#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import sys
import unittest
from argparse import Namespace
from pathlib import Path


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

    def test_test_runtime_should_scale_coverage_defaults_by_profile(self) -> None:
        playable = sc_test.resolve_test_runtime(delivery_profile="playable-ea", security_profile=None, no_coverage_gate=False)
        fast_ship = sc_test.resolve_test_runtime(delivery_profile="fast-ship", security_profile=None, no_coverage_gate=False)
        standard = sc_test.resolve_test_runtime(delivery_profile="standard", security_profile=None, no_coverage_gate=False)

        self.assertFalse(playable["coverage_gate"])
        self.assertEqual(0, playable["coverage_lines_min"])
        self.assertEqual(0, playable["coverage_branches_min"])
        self.assertFalse(playable["allow_full_unit_fallback"])

        self.assertTrue(fast_ship["coverage_gate"])
        self.assertEqual(70, fast_ship["coverage_lines_min"])
        self.assertEqual(60, fast_ship["coverage_branches_min"])
        self.assertEqual("host-safe", fast_ship["security_profile"])
        self.assertFalse(fast_ship["allow_full_unit_fallback"])

        self.assertTrue(standard["coverage_gate"])
        self.assertEqual(90, standard["coverage_lines_min"])
        self.assertEqual(85, standard["coverage_branches_min"])
        self.assertEqual("strict", standard["security_profile"])
        self.assertFalse(standard["allow_full_unit_fallback"])

    def test_test_runtime_should_respect_explicit_no_coverage_gate(self) -> None:
        runtime = sc_test.resolve_test_runtime(delivery_profile="standard", security_profile=None, no_coverage_gate=True)
        self.assertFalse(runtime["coverage_gate"])
        self.assertEqual(90, runtime["coverage_lines_min"])
        self.assertEqual(85, runtime["coverage_branches_min"])

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
