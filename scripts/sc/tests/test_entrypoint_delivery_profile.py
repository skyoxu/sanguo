#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
PYTHON_DIR = REPO_ROOT / "scripts" / "python"

for candidate in (SC_DIR, PYTHON_DIR):
    text = str(candidate)
    if text not in sys.path:
        sys.path.insert(0, text)


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sc_build = _load_module("sc_build_module", "scripts/sc/build.py")
sc_test = _load_module("sc_test_module", "scripts/sc/test.py")
gate_bundle = _load_module("gate_bundle_module", "scripts/python/run_gate_bundle.py")
sc_semantic_gate_all = _load_module("sc_semantic_gate_all_module", "scripts/sc/llm_semantic_gate_all.py")
sc_subtasks_coverage = _load_module("sc_subtasks_coverage_module", "scripts/sc/llm_check_subtasks_coverage.py")


class EntrypointDeliveryProfileTests(unittest.TestCase):
    def test_build_runtime_should_relax_warn_as_error_for_playable_ea(self) -> None:
        runtime = sc_build.resolve_build_runtime(delivery_profile="playable-ea", security_profile=None)
        self.assertEqual("playable-ea", runtime["delivery_profile"])
        self.assertEqual("host-safe", runtime["security_profile"])
        self.assertFalse(runtime["warn_as_error"])

        cmd = sc_build.build_dotnet_build_cmd(target="Game.sln", config="Debug", verbose=False, warn_as_error=runtime["warn_as_error"])
        self.assertNotIn("-warnaserror", cmd)

    def test_build_runtime_should_keep_warn_as_error_for_standard(self) -> None:
        runtime = sc_build.resolve_build_runtime(delivery_profile="standard", security_profile=None)
        self.assertEqual("standard", runtime["delivery_profile"])
        self.assertEqual("strict", runtime["security_profile"])
        self.assertTrue(runtime["warn_as_error"])

        cmd = sc_build.build_dotnet_build_cmd(target="Game.sln", config="Release", verbose=True, warn_as_error=runtime["warn_as_error"])
        self.assertIn("-warnaserror", cmd)

    def test_build_main_should_prefer_godotgame_solution_when_target_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "logs" / "ci" / "sc-build"
            (root / "Game.sln").write_text("stub", encoding="utf-8")
            (root / "GodotGame.sln").write_text("stub", encoding="utf-8")
            argv = ["build.py"]

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(sc_build, "repo_root", return_value=root), \
                mock.patch.object(sc_build, "ci_dir", return_value=out_dir), \
                mock.patch.object(sc_build, "run_cmd", return_value=(0, "ok")) as run_cmd_mock:
                rc = sc_build.main()

            self.assertEqual(0, rc)
            run_cmd_mock.assert_called_once()
            build_cmd = run_cmd_mock.call_args[0][0]
            self.assertEqual(["dotnet", "build"], build_cmd[:2])
            self.assertEqual(str(root / "GodotGame.sln"), build_cmd[2])

    def test_test_runtime_should_scale_coverage_defaults_by_profile(self) -> None:
        playable = sc_test.resolve_test_runtime(delivery_profile="playable-ea", security_profile=None, no_coverage_gate=False)
        fast_ship = sc_test.resolve_test_runtime(delivery_profile="fast-ship", security_profile=None, no_coverage_gate=False)
        standard = sc_test.resolve_test_runtime(delivery_profile="standard", security_profile=None, no_coverage_gate=False)

        self.assertFalse(playable["coverage_gate"])
        self.assertEqual(0, playable["coverage_lines_min"])
        self.assertEqual(0, playable["coverage_branches_min"])

        self.assertTrue(fast_ship["coverage_gate"])
        self.assertEqual(70, fast_ship["coverage_lines_min"])
        self.assertEqual(60, fast_ship["coverage_branches_min"])
        self.assertEqual("host-safe", fast_ship["security_profile"])

        self.assertTrue(standard["coverage_gate"])
        self.assertEqual(90, standard["coverage_lines_min"])
        self.assertEqual(85, standard["coverage_branches_min"])
        self.assertEqual("strict", standard["security_profile"])

    def test_test_runtime_should_respect_explicit_no_coverage_gate(self) -> None:
        runtime = sc_test.resolve_test_runtime(delivery_profile="standard", security_profile=None, no_coverage_gate=True)
        self.assertFalse(runtime["coverage_gate"])
        self.assertEqual(90, runtime["coverage_lines_min"])
        self.assertEqual(85, runtime["coverage_branches_min"])

    def test_test_parser_should_default_solution_to_auto(self) -> None:
        args = sc_test.build_parser().parse_args([])
        self.assertEqual("auto", args.solution)

    def test_test_main_should_set_skip_coverage_env_when_no_coverage_gate_is_enabled(self) -> None:
        observed: dict[str, str | None] = {}
        parser = mock.Mock()
        parser.parse_args.return_value = Namespace(
            type="unit",
            task_id=None,
            solution="Game.sln",
            configuration="Debug",
            delivery_profile="standard",
            security_profile=None,
            godot_bin=None,
            run_id="run123",
            smoke_scene="res://Game.Godot/Scenes/Main.tscn",
            timeout_sec=600,
            skip_smoke=False,
            no_coverage_gate=True,
            no_coverage_report=True,
        )

        original_skip = os.environ.get("SC_ACCEPTANCE_NO_COVERAGE_GATE")
        original_lines = os.environ.get("COVERAGE_LINES_MIN")
        original_branches = os.environ.get("COVERAGE_BRANCHES_MIN")
        os.environ.pop("SC_ACCEPTANCE_NO_COVERAGE_GATE", None)
        os.environ.pop("COVERAGE_LINES_MIN", None)
        os.environ.pop("COVERAGE_BRANCHES_MIN", None)

        def fake_run_unit(out_dir, solution, configuration, *, run_id, task_id=None):
            observed["skip"] = os.environ.get("SC_ACCEPTANCE_NO_COVERAGE_GATE")
            observed["lines"] = os.environ.get("COVERAGE_LINES_MIN")
            observed["branches"] = os.environ.get("COVERAGE_BRANCHES_MIN")
            return {
                "name": "unit",
                "rc": 0,
                "status": "ok",
                "artifacts_dir": str(REPO_ROOT / "logs" / "unit" / "2026-03-25"),
            }

        try:
            with (
                mock.patch.object(sc_test, "build_parser", return_value=parser),
                mock.patch.object(sc_test, "run_unit", side_effect=fake_run_unit),
                mock.patch.object(sc_test, "run_csharp_test_conventions", return_value={"name": "csharp-test-conventions", "rc": 0, "status": "ok"}),
                mock.patch.object(sc_test, "validate_sc_test_summary", return_value=None),
            ):
                rc = sc_test.main()
        finally:
            if original_skip is None:
                os.environ.pop("SC_ACCEPTANCE_NO_COVERAGE_GATE", None)
            else:
                os.environ["SC_ACCEPTANCE_NO_COVERAGE_GATE"] = original_skip
            if original_lines is None:
                os.environ.pop("COVERAGE_LINES_MIN", None)
            else:
                os.environ["COVERAGE_LINES_MIN"] = original_lines
            if original_branches is None:
                os.environ.pop("COVERAGE_BRANCHES_MIN", None)
            else:
                os.environ["COVERAGE_BRANCHES_MIN"] = original_branches

        self.assertEqual(0, rc)
        self.assertEqual("1", observed.get("skip"))
        self.assertIsNone(observed.get("lines"))
        self.assertIsNone(observed.get("branches"))
        self.assertNotIn("SC_ACCEPTANCE_NO_COVERAGE_GATE", os.environ)

    def test_gate_bundle_runtime_should_scale_warning_budget_and_stability_gate(self) -> None:
        playable = gate_bundle.resolve_gate_bundle_runtime(delivery_profile="playable-ea")
        standard = gate_bundle.resolve_gate_bundle_runtime(delivery_profile="standard")

        self.assertEqual("playable-ea", playable["delivery_profile"])
        self.assertEqual(300, playable["task_links_max_warnings"])
        self.assertFalse(playable["stability_template_hard"])

        self.assertEqual("standard", standard["delivery_profile"])
        self.assertEqual(100, standard["task_links_max_warnings"])
        self.assertTrue(standard["stability_template_hard"])

    def test_semantic_gate_runtime_should_relax_batch_llm_thresholds_for_playable_ea(self) -> None:
        playable = sc_semantic_gate_all.apply_delivery_profile_defaults(
            Namespace(
                delivery_profile="playable-ea",
                timeout_sec=None,
                consensus_runs=None,
                model_reasoning_effort=None,
                max_prompt_chars=None,
                max_needs_fix=None,
                max_unknown=None,
                garbled_gate=None,
            )
        )
        standard = sc_semantic_gate_all.apply_delivery_profile_defaults(
            Namespace(
                delivery_profile="standard",
                timeout_sec=None,
                consensus_runs=None,
                model_reasoning_effort=None,
                max_prompt_chars=None,
                max_needs_fix=None,
                max_unknown=None,
                garbled_gate=None,
            )
        )

        self.assertEqual("playable-ea", playable.delivery_profile)
        self.assertEqual(300, playable.timeout_sec)
        self.assertEqual(1, playable.consensus_runs)
        self.assertEqual(999, playable.max_needs_fix)
        self.assertEqual(999, playable.max_unknown)
        self.assertEqual("off", playable.garbled_gate)

        self.assertEqual("standard", standard.delivery_profile)
        self.assertEqual(900, standard.timeout_sec)
        self.assertEqual(1, standard.consensus_runs)
        self.assertEqual(0, standard.max_needs_fix)
        self.assertEqual(0, standard.max_unknown)
        self.assertEqual("on", standard.garbled_gate)

    def test_subtasks_coverage_runtime_should_follow_delivery_profile_defaults(self) -> None:
        playable = sc_subtasks_coverage.apply_delivery_profile_defaults(
            Namespace(
                delivery_profile="playable-ea",
                timeout_sec=None,
                max_prompt_chars=None,
                consensus_runs=None,
                garbled_gate=None,
            )
        )
        standard = sc_subtasks_coverage.apply_delivery_profile_defaults(
            Namespace(
                delivery_profile="standard",
                timeout_sec=None,
                max_prompt_chars=None,
                consensus_runs=None,
                garbled_gate=None,
            )
        )

        self.assertEqual("playable-ea", playable.delivery_profile)
        self.assertEqual(300, playable.timeout_sec)
        self.assertEqual(40000, playable.max_prompt_chars)
        self.assertEqual(1, playable.consensus_runs)
        self.assertEqual("off", playable.garbled_gate)

        self.assertEqual("standard", standard.delivery_profile)
        self.assertEqual(900, standard.timeout_sec)
        self.assertEqual(60000, standard.max_prompt_chars)
        self.assertEqual(1, standard.consensus_runs)
        self.assertEqual("on", standard.garbled_gate)


if __name__ == "__main__":
    unittest.main()
