#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _sc_test_steps as sc_steps  # noqa: E402


class ScTestStepsUnitFallbackTests(unittest.TestCase):
    def test_run_unit_should_fail_fast_when_task_scoped_coverage_is_zero_and_fallback_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            first_out = "RUN_DOTNET status=coverage_failed line=0.0% branch=0.0 out=logs/unit/2026-03-30\n"

            with (
                mock.patch.object(sc_steps, "repo_root", return_value=REPO_ROOT),
                mock.patch.object(sc_steps, "today_str", return_value="2026-03-30"),
                mock.patch.object(sc_steps, "task_scoped_cs_refs", return_value=["Game.Core.Tests/Tasks/Task0056AcceptanceTests.cs"]),
                mock.patch.object(sc_steps, "build_dotnet_filter_from_cs_refs", return_value="FullyQualifiedName~Task0056AcceptanceTests"),
                mock.patch.object(sc_steps, "run_cmd", return_value=(2, first_out)) as run_cmd_mock,
            ):
                step = sc_steps.run_unit(out_dir, "Game.sln", "Debug", run_id="r1", task_id="56")

            self.assertEqual(2, int(step["rc"]))
            self.assertEqual("fail", step["status"])
            self.assertIn("--filter", step["cmd"])
            run_cmd_mock.assert_called_once()
            log_text = (out_dir / "unit.log").read_text(encoding="utf-8")
            self.assertIn("full-suite fallback is disabled", log_text)

    def test_run_unit_should_retry_without_filter_when_explicitly_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            first_out = "RUN_DOTNET status=coverage_failed line=0.0% branch=0.0 out=logs/unit/2026-03-30\n"
            second_out = "RUN_DOTNET status=ok line=92.0% branch=86.0 out=logs/unit/2026-03-30\n"

            with (
                mock.patch.object(sc_steps, "repo_root", return_value=REPO_ROOT),
                mock.patch.object(sc_steps, "today_str", return_value="2026-03-30"),
                mock.patch.object(sc_steps, "task_scoped_cs_refs", return_value=["Game.Core.Tests/Tasks/Task0056AcceptanceTests.cs"]),
                mock.patch.object(sc_steps, "build_dotnet_filter_from_cs_refs", return_value="FullyQualifiedName~Task0056AcceptanceTests"),
                mock.patch.object(sc_steps, "run_cmd", side_effect=[(2, first_out), (0, second_out)]),
            ):
                step = sc_steps.run_unit(
                    out_dir,
                    "Game.sln",
                    "Debug",
                    run_id="r2",
                    task_id="56",
                    allow_full_unit_fallback=True,
                )

            self.assertEqual(0, int(step["rc"]))
            self.assertEqual("ok", step["status"])
            self.assertEqual(
                ["py", "-3", "scripts/python/run_dotnet.py", "--solution", "Game.sln", "--configuration", "Debug"],
                step["cmd"],
            )
            log_text = (out_dir / "unit.log").read_text(encoding="utf-8")
            self.assertIn("retrying unit without task filter", log_text)
            self.assertIn("fallback_rc: 0", log_text)

    def test_run_unit_should_keep_original_failure_when_fallback_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            first_out = "RUN_DOTNET status=coverage_failed line=0.0% branch=0.0 out=logs/unit/2026-03-30\n"
            second_out = "RUN_DOTNET status=tests_failed line=10.0% branch=5.0 out=logs/unit/2026-03-30\n"

            with (
                mock.patch.object(sc_steps, "repo_root", return_value=REPO_ROOT),
                mock.patch.object(sc_steps, "today_str", return_value="2026-03-30"),
                mock.patch.object(sc_steps, "task_scoped_cs_refs", return_value=["Game.Core.Tests/Tasks/Task0056AcceptanceTests.cs"]),
                mock.patch.object(sc_steps, "build_dotnet_filter_from_cs_refs", return_value="FullyQualifiedName~Task0056AcceptanceTests"),
                mock.patch.object(sc_steps, "run_cmd", side_effect=[(2, first_out), (1, second_out)]),
            ):
                step = sc_steps.run_unit(
                    out_dir,
                    "Game.sln",
                    "Debug",
                    run_id="r2b",
                    task_id="56",
                    allow_full_unit_fallback=True,
                )

            self.assertEqual(2, int(step["rc"]))
            self.assertEqual("fail", step["status"])
            self.assertIn("--filter", step["cmd"])

    def test_run_gdunit_hard_should_fail_when_task_has_no_gd_refs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            with (
                mock.patch.object(sc_steps, "repo_root", return_value=REPO_ROOT),
                mock.patch.object(sc_steps, "today_str", return_value="2026-04-01"),
                mock.patch.object(sc_steps, "task_scoped_gdunit_refs", return_value=[]),
                mock.patch.object(sc_steps, "run_cmd") as run_cmd_mock,
            ):
                step = sc_steps.run_gdunit_hard(
                    out_dir,
                    "godot.exe",
                    120,
                    run_id="r3",
                    task_id="56",
                    require_task_scoped_refs=True,
                )

            self.assertEqual(1, int(step["rc"]))
            self.assertEqual("fail", step["status"])
            self.assertEqual("missing_task_scoped_gd_refs", step["error"])
            run_cmd_mock.assert_not_called()
            log_text = (out_dir / "gdunit-hard.log").read_text(encoding="utf-8")
            self.assertIn("no task-scoped .gd refs resolved", log_text)

    def test_run_gdunit_hard_should_fallback_to_default_dirs_when_task_has_no_gd_refs_but_gate_is_not_required(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci"
            tests_project = root / "Tests.Godot"
            (tests_project / "tests" / "Scenes").mkdir(parents=True, exist_ok=True)
            captured: list[list[str]] = []

            def fake_run_cmd(cmd, *, cwd=None, timeout_sec=0):  # noqa: ANN001
                captured.append(list(cmd))
                return 0, "ok\n"

            with (
                mock.patch.object(sc_steps, "repo_root", return_value=root),
                mock.patch.object(sc_steps, "today_str", return_value="2026-04-01"),
                mock.patch.object(sc_steps, "task_scoped_gdunit_refs", return_value=[]),
                mock.patch.object(sc_steps, "run_cmd", side_effect=fake_run_cmd),
            ):
                step = sc_steps.run_gdunit_hard(
                    out_dir,
                    "godot.exe",
                    120,
                    run_id="r3b",
                    task_id="56",
                    require_task_scoped_refs=False,
                )

            self.assertEqual(0, int(step["rc"]))
            self.assertEqual("ok", step["status"])
            self.assertIn("tests/Scenes", captured[0])

    def test_run_gdunit_hard_should_only_use_task_scoped_gd_refs_when_task_id_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci"
            tests_project = root / "Tests.Godot"
            (tests_project / "tests" / "Tasks").mkdir(parents=True, exist_ok=True)
            (tests_project / "tests" / "Scenes").mkdir(parents=True, exist_ok=True)
            refs = ["tests/Tasks/test_task_56_a.gd", "tests/Tasks/test_task_56_b.gd"]
            for rel in refs:
                path = tests_project / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("extends Node\n", encoding="utf-8")
            captured: list[list[str]] = []

            def fake_run_cmd(cmd, *, cwd=None, timeout_sec=0):  # noqa: ANN001
                captured.append(list(cmd))
                return 0, "ok\n"

            with (
                mock.patch.object(sc_steps, "repo_root", return_value=root),
                mock.patch.object(sc_steps, "today_str", return_value="2026-04-01"),
                mock.patch.object(sc_steps, "task_scoped_gdunit_refs", return_value=refs),
                mock.patch.object(sc_steps, "run_cmd", side_effect=fake_run_cmd),
            ):
                step = sc_steps.run_gdunit_hard(out_dir, "godot.exe", 120, run_id="r4", task_id="56")

            self.assertEqual(0, int(step["rc"]))
            cmd = captured[0]
            self.assertEqual(refs, [cmd[idx + 1] for idx, token in enumerate(cmd[:-1]) if token == "--add"])
            self.assertNotIn("tests/Scenes", cmd)


if __name__ == "__main__":
    unittest.main()
