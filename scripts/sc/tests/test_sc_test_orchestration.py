#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sc_test = _load_module("sc_test_orchestration_module", "scripts/sc/test.py")


class ScTestOrchestrationTests(unittest.TestCase):
    def test_self_check_should_validate_planned_summary_without_running_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "sc-test"
            argv = ["test.py", "--self-check", "--type", "unit", "--run-id", "9" * 32]
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(sc_test, "ci_dir", return_value=out_dir), \
                mock.patch.object(sc_test, "run_unit") as run_unit_mock, \
                mock.patch.object(sc_test, "run_csharp_test_conventions") as conventions_mock, \
                mock.patch.object(sc_test, "run_coverage_report") as coverage_mock:
                rc = sc_test.main()

            self.assertEqual(0, rc)
            run_unit_mock.assert_not_called()
            conventions_mock.assert_not_called()
            coverage_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("self-check", summary["mode"])
            self.assertEqual("ok", summary["status"])
            self.assertEqual(["unit", "csharp-test-conventions", "coverage-report"], [item["name"] for item in summary["planned_steps"]])

    def test_main_should_run_unit_then_coverage_and_persist_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "sc-test"
            run_id = "1" * 32
            argv = ["test.py", "--type", "unit", "--run-id", run_id]
            unit_step = {
                "name": "unit",
                "cmd": ["py", "-3", "scripts/python/run_dotnet.py"],
                "rc": 0,
                "log": str(out_dir / "unit.log"),
                "artifacts_dir": str(out_dir / "unit-artifacts"),
                "status": "ok",
            }
            coverage_step = {
                "name": "coverage-report",
                "cmd": ["reportgenerator"],
                "rc": 0,
                "log": str(out_dir / "coverage-report.log"),
                "report_dir": str(out_dir / "coverage-report"),
                "status": "ok",
            }
            conventions_step = {
                "name": "csharp-test-conventions",
                "cmd": ["py", "-3", "scripts/python/check_csharp_test_conventions.py"],
                "rc": 0,
                "log": str(out_dir / "csharp-test-conventions.log"),
                "status": "ok",
            }
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(sc_test, "ci_dir", return_value=out_dir), \
                mock.patch.object(sc_test, "run_unit", return_value=unit_step) as run_unit_mock, \
                mock.patch.object(sc_test, "run_csharp_test_conventions", return_value=conventions_step) as conventions_mock, \
                mock.patch.object(sc_test, "run_coverage_report", return_value=coverage_step) as coverage_mock:
                rc = sc_test.main()

            self.assertEqual(0, rc)
            run_unit_mock.assert_called_once()
            conventions_mock.assert_called_once()
            coverage_mock.assert_called_once()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", summary["status"])
            self.assertEqual(run_id, summary["run_id"])
            self.assertEqual(["unit", "csharp-test-conventions", "coverage-report"], [item["name"] for item in summary["steps"]])

    def test_main_should_skip_coverage_when_unit_step_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "sc-test"
            argv = ["test.py", "--type", "unit", "--run-id", "2" * 32]
            unit_step = {
                "name": "unit",
                "cmd": ["py", "-3", "scripts/python/run_dotnet.py"],
                "rc": 1,
                "log": str(out_dir / "unit.log"),
                "artifacts_dir": str(out_dir / "unit-artifacts"),
                "status": "fail",
            }
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(sc_test, "ci_dir", return_value=out_dir), \
                mock.patch.object(sc_test, "run_unit", return_value=unit_step), \
                mock.patch.object(sc_test, "run_csharp_test_conventions") as conventions_mock, \
                mock.patch.object(sc_test, "run_coverage_report") as coverage_mock:
                rc = sc_test.main()

            self.assertEqual(1, rc)
            conventions_mock.assert_not_called()
            coverage_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual(["unit"], [item["name"] for item in summary["steps"]])

    def test_main_should_fail_when_csharp_test_conventions_gate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "sc-test"
            argv = ["test.py", "--type", "unit", "--run-id", "5" * 32, "--task-id", "11"]
            unit_step = {
                "name": "unit",
                "cmd": ["py", "-3", "scripts/python/run_dotnet.py"],
                "rc": 0,
                "log": str(out_dir / "unit.log"),
                "artifacts_dir": str(out_dir / "unit-artifacts"),
                "status": "ok",
            }
            conventions_step = {
                "name": "csharp-test-conventions",
                "cmd": ["py", "-3", "scripts/python/check_csharp_test_conventions.py", "--task-id", "11"],
                "rc": 1,
                "log": str(out_dir / "csharp-test-conventions.log"),
                "status": "fail",
            }
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(sc_test, "ci_dir", return_value=out_dir), \
                mock.patch.object(sc_test, "run_unit", return_value=unit_step), \
                mock.patch.object(sc_test, "run_csharp_test_conventions", return_value=conventions_step) as conventions_mock, \
                mock.patch.object(sc_test, "run_coverage_report") as coverage_mock:
                rc = sc_test.main()

            self.assertEqual(1, rc)
            conventions_mock.assert_called_once()
            coverage_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual(["unit", "csharp-test-conventions"], [item["name"] for item in summary["steps"]])

    def test_main_should_require_godot_bin_for_e2e_before_running_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "sc-test"
            argv = ["test.py", "--type", "e2e", "--run-id", "3" * 32]
            env = dict(os.environ)
            env.pop("GODOT_BIN", None)
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(sc_test, "ci_dir", return_value=out_dir), \
                mock.patch.dict(sc_test.os.environ, env, clear=True), \
                mock.patch.object(sc_test, "run_gdunit_hard") as gdunit_mock, \
                mock.patch.object(sc_test, "run_smoke") as smoke_mock:
                rc = sc_test.main()

            self.assertEqual(2, rc)
            gdunit_mock.assert_not_called()
            smoke_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual([], summary["steps"])

    def test_main_should_run_gdunit_then_smoke_and_fail_on_smoke_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "sc-test"
            argv = ["test.py", "--type", "e2e", "--run-id", "4" * 32, "--godot-bin", "C:/Godot/Godot.exe"]
            gdunit_step = {
                "name": "gdunit-hard",
                "cmd": ["py", "-3", "scripts/python/run_gdunit.py"],
                "rc": 0,
                "log": str(out_dir / "gdunit-hard.log"),
                "report_dir": str(out_dir / "gdunit-hard"),
                "status": "ok",
            }
            smoke_step = {
                "name": "smoke",
                "cmd": ["py", "-3", "scripts/python/smoke_headless.py"],
                "rc": 2,
                "log": str(out_dir / "smoke.log"),
                "status": "fail",
            }
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(sc_test, "ci_dir", return_value=out_dir), \
                mock.patch.object(sc_test, "run_gdunit_hard", return_value=gdunit_step) as gdunit_mock, \
                mock.patch.object(sc_test, "run_smoke", return_value=smoke_step) as smoke_mock:
                rc = sc_test.main()

            self.assertEqual(1, rc)
            gdunit_mock.assert_called_once()
            smoke_mock.assert_called_once()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual(["gdunit-hard", "smoke"], [item["name"] for item in summary["steps"]])

    def test_main_should_skip_gdunit_for_task_scoped_all_when_no_gd_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "sc-test"
            argv = ["test.py", "--type", "all", "--run-id", "6" * 32, "--task-id", "21", "--godot-bin", "C:/Godot/Godot.exe"]
            unit_step = {
                "name": "unit",
                "cmd": ["py", "-3", "scripts/python/run_dotnet.py"],
                "rc": 0,
                "log": str(out_dir / "unit.log"),
                "artifacts_dir": str(out_dir / "unit-artifacts"),
                "status": "ok",
            }
            conventions_step = {
                "name": "csharp-test-conventions",
                "cmd": ["py", "-3", "scripts/python/check_csharp_test_conventions.py", "--task-id", "21"],
                "rc": 0,
                "log": str(out_dir / "csharp-test-conventions.log"),
                "status": "ok",
            }
            coverage_step = {
                "name": "coverage-report",
                "cmd": ["reportgenerator"],
                "rc": 0,
                "log": str(out_dir / "coverage-report.log"),
                "report_dir": str(out_dir / "coverage-report"),
                "status": "ok",
            }
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(sc_test, "ci_dir", return_value=out_dir), \
                mock.patch.object(sc_test, "run_unit", return_value=unit_step), \
                mock.patch.object(sc_test, "run_csharp_test_conventions", return_value=conventions_step), \
                mock.patch.object(sc_test, "run_coverage_report", return_value=coverage_step), \
                mock.patch.object(sc_test, "_task_scoped_gdunit_refs", return_value=[]), \
                mock.patch.object(sc_test, "run_gdunit_hard") as gdunit_mock, \
                mock.patch.object(sc_test, "run_smoke") as smoke_mock:
                rc = sc_test.main()

            self.assertEqual(0, rc)
            gdunit_mock.assert_not_called()
            smoke_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", summary["status"])
            self.assertEqual(
                ["unit", "csharp-test-conventions", "coverage-report", "gdunit-hard", "smoke"],
                [item["name"] for item in summary["steps"]],
            )
            self.assertEqual("skipped", summary["steps"][3]["status"])
            self.assertEqual("task_scoped_no_gd_refs_unit_only", summary["steps"][3]["reason"])
            self.assertEqual("skipped", summary["steps"][4]["status"])

    def test_main_should_keep_fail_fast_for_explicit_e2e_when_no_gd_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "sc-test"
            argv = ["test.py", "--type", "e2e", "--run-id", "7" * 32, "--task-id", "21", "--godot-bin", "C:/Godot/Godot.exe"]
            gdunit_step = {
                "name": "gdunit-hard",
                "cmd": ["internal:task_scoped_gdunit_refs"],
                "rc": 2,
                "log": str(out_dir / "gdunit-hard.log"),
                "report_dir": str(out_dir / "gdunit-hard"),
                "status": "fail",
                "reason": "missing_task_scoped_gdunit_refs",
            }
            smoke_step = {
                "name": "smoke",
                "cmd": ["py", "-3", "scripts/python/smoke_headless.py"],
                "rc": 0,
                "log": str(out_dir / "smoke.log"),
                "status": "ok",
            }
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(sc_test, "ci_dir", return_value=out_dir), \
                mock.patch.object(sc_test, "_task_scoped_gdunit_refs", return_value=[]), \
                mock.patch.object(sc_test, "run_gdunit_hard", return_value=gdunit_step) as gdunit_mock, \
                mock.patch.object(sc_test, "run_smoke", return_value=smoke_step) as smoke_mock:
                rc = sc_test.main()

            self.assertEqual(1, rc)
            gdunit_mock.assert_called_once()
            smoke_mock.assert_called_once()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])

    def test_main_should_skip_engine_lane_when_unit_failed_in_all_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "sc-test"
            argv = ["test.py", "--type", "all", "--run-id", "8" * 32, "--task-id", "21", "--godot-bin", "C:/Godot/Godot.exe"]
            unit_step = {
                "name": "unit",
                "cmd": ["py", "-3", "scripts/python/run_dotnet.py"],
                "rc": 1,
                "log": str(out_dir / "unit.log"),
                "artifacts_dir": str(out_dir / "unit-artifacts"),
                "status": "fail",
            }
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(sc_test, "ci_dir", return_value=out_dir), \
                mock.patch.object(sc_test, "run_unit", return_value=unit_step), \
                mock.patch.object(sc_test, "_task_scoped_gdunit_refs", return_value=["Tests.Godot/tests/Integration/test_task_21_flow.gd"]), \
                mock.patch.object(sc_test, "run_gdunit_hard") as gdunit_mock, \
                mock.patch.object(sc_test, "run_smoke") as smoke_mock:
                rc = sc_test.main()

            self.assertEqual(1, rc)
            gdunit_mock.assert_not_called()
            smoke_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual(["unit", "gdunit-hard", "smoke"], [item["name"] for item in summary["steps"]])
            self.assertEqual("skipped", summary["steps"][1]["status"])
            self.assertEqual("unit_failed_prevents_engine_lane", summary["steps"][1]["reason"])
            self.assertEqual("skipped", summary["steps"][2]["status"])
            self.assertEqual("unit_failed_prevents_engine_lane", summary["steps"][2]["reason"])


if __name__ == "__main__":
    unittest.main()
