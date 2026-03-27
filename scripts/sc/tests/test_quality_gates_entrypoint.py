#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


quality_gates = _load_module("quality_gates_module", "scripts/python/quality_gates.py")


def _ok_dotnet_summary() -> dict:
    return {
        "status": "ok",
        "threshold_ok": True,
        "coverage": {
            "line_pct": 95.0,
            "branch_pct": 90.0,
            "lines_min": 90.0,
            "branches_min": 85.0,
        },
        "summary_path": "mock",
    }


class QualityGatesEntrypointTests(unittest.TestCase):
    def test_run_smoke_headless_should_enable_exit_on_ready_temporarily(self) -> None:
        observed = {}
        original_exit_on_ready = os.environ.get("GD_SMOKE_EXIT_ON_READY")
        original_exit_delay = os.environ.get("GD_SMOKE_EXIT_DELAY_SEC")
        os.environ.pop("GD_SMOKE_EXIT_ON_READY", None)
        os.environ.pop("GD_SMOKE_EXIT_DELAY_SEC", None)

        def fake_run(cmd):
            observed["cmd"] = list(cmd)
            observed["exit_on_ready"] = os.environ.get("GD_SMOKE_EXIT_ON_READY")
            observed["exit_delay"] = os.environ.get("GD_SMOKE_EXIT_DELAY_SEC")
            return 0

        try:
            with mock.patch.object(quality_gates, "_run", side_effect=fake_run):
                rc = quality_gates.run_smoke_headless("C:/Godot/Godot.exe")
        finally:
            if original_exit_on_ready is None:
                os.environ.pop("GD_SMOKE_EXIT_ON_READY", None)
            else:
                os.environ["GD_SMOKE_EXIT_ON_READY"] = original_exit_on_ready
            if original_exit_delay is None:
                os.environ.pop("GD_SMOKE_EXIT_DELAY_SEC", None)
            else:
                os.environ["GD_SMOKE_EXIT_DELAY_SEC"] = original_exit_delay

        self.assertEqual(0, rc)
        self.assertEqual("1", observed.get("exit_on_ready"))
        self.assertEqual("0.25", observed.get("exit_delay"))
        self.assertNotIn("GD_SMOKE_EXIT_ON_READY", os.environ)
        self.assertNotIn("GD_SMOKE_EXIT_DELAY_SEC", os.environ)

    def test_all_should_delegate_to_gate_bundle_hard_by_default(self) -> None:
        with mock.patch.object(quality_gates, "run_gate_bundle_hard", return_value=0) as bundle_mock, \
                mock.patch.object(quality_gates, "_normalize_dotnet_summary", return_value=_ok_dotnet_summary()), \
                mock.patch.object(quality_gates, "run_gdunit_hard") as gdunit_mock, \
                mock.patch.object(quality_gates, "run_smoke_headless") as smoke_mock:
            rc = quality_gates.main(["all"])

        self.assertEqual(0, rc)
        bundle_mock.assert_called_once_with(
            delivery_profile="",
            task_files=quality_gates.DEFAULT_GATE_BUNDLE_TASK_FILES,
            out_dir="",
            run_id="",
        )
        gdunit_mock.assert_not_called()
        smoke_mock.assert_not_called()

    def test_all_should_forward_gate_bundle_runtime_options(self) -> None:
        with mock.patch.object(quality_gates, "run_gate_bundle_hard", return_value=0) as bundle_mock, \
                mock.patch.object(quality_gates, "_normalize_dotnet_summary", return_value=_ok_dotnet_summary()):
            rc = quality_gates.main(
                [
                    "all",
                    "--delivery-profile",
                    "standard",
                    "--run-id",
                    "local-demo",
                    "--out-dir",
                    "logs/ci/demo/gate-bundle",
                    "--task-file",
                    "custom/tasks_back.json",
                    "--task-file",
                    "custom/tasks_gameplay.json",
                ]
            )

        self.assertEqual(0, rc)
        bundle_mock.assert_called_once_with(
            delivery_profile="standard",
            task_files=["custom/tasks_back.json", "custom/tasks_gameplay.json"],
            out_dir="logs/ci/demo/gate-bundle",
            run_id="local-demo",
        )

    def test_all_should_append_gdunit_and_smoke_when_enabled(self) -> None:
        with mock.patch.object(quality_gates, "run_gate_bundle_hard", return_value=0) as bundle_mock, \
                mock.patch.object(quality_gates, "_normalize_dotnet_summary", return_value=_ok_dotnet_summary()), \
                mock.patch.object(quality_gates, "run_gdunit_hard", return_value=0) as gdunit_mock, \
                mock.patch.object(quality_gates, "run_smoke_headless", return_value=0) as smoke_mock:
            rc = quality_gates.main(
                [
                    "all",
                    "--gdunit-hard",
                    "--smoke",
                    "--godot-bin",
                    "C:/Godot/Godot.exe",
                ]
            )

        self.assertEqual(0, rc)
        bundle_mock.assert_called_once()
        gdunit_mock.assert_called_once_with("C:/Godot/Godot.exe")
        smoke_mock.assert_called_once_with("C:/Godot/Godot.exe")

    def test_all_should_accept_legacy_gdunit_ui_and_coverage_soft_flags(self) -> None:
        with mock.patch.object(quality_gates, "run_gate_bundle_hard", return_value=0) as bundle_mock, \
                mock.patch.object(quality_gates, "_normalize_dotnet_summary", return_value=_ok_dotnet_summary()), \
                mock.patch.object(quality_gates, "run_gdunit_hard", return_value=0) as gdunit_mock, \
                mock.patch.object(quality_gates, "run_smoke_headless") as smoke_mock:
            rc = quality_gates.main(
                [
                    "all",
                    "--gdunit-ui",
                    "--coverage-soft",
                    "--godot-bin",
                    "C:/Godot/Godot.exe",
                ]
            )

        self.assertEqual(0, rc)
        bundle_mock.assert_called_once()
        gdunit_mock.assert_called_once_with("C:/Godot/Godot.exe")
        smoke_mock.assert_not_called()

    def test_all_should_require_godot_bin_when_gdunit_or_smoke_is_requested(self) -> None:
        with mock.patch.object(quality_gates, "run_gate_bundle_hard", return_value=0) as bundle_mock, \
                mock.patch.object(quality_gates, "run_gdunit_hard") as gdunit_mock, \
                mock.patch.object(quality_gates, "run_smoke_headless") as smoke_mock:
            rc = quality_gates.main(["all", "--gdunit-hard"])

        self.assertEqual(2, rc)
        bundle_mock.assert_not_called()
        gdunit_mock.assert_not_called()
        smoke_mock.assert_not_called()

    def test_all_should_record_resolved_solution_in_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_dir = tmp_path / "out"
            dotnet_summary = tmp_path / "dotnet-summary.json"
            dotnet_summary.write_text(
                '{"status":"ok","threshold_ok":true,"coverage":{"line_pct":95.0,"branch_pct":90.0,"lines_min":90.0,"branches_min":85.0}}',
                encoding="utf-8",
            )

            env = {
                quality_gates.QUALITY_GATES_TEST_MODE_ENV: "1",
                quality_gates.QUALITY_GATES_TEST_OUT_DIR_ENV: str(out_dir),
                quality_gates.QUALITY_GATES_TEST_DOTNET_SUMMARY_JSON_ENV: str(dotnet_summary),
            }
            with mock.patch.dict(os.environ, env, clear=False), \
                    mock.patch.object(quality_gates, "run_gate_bundle_hard", return_value=0):
                rc = quality_gates.main(["all"])

            self.assertEqual(0, rc)
            summary = (out_dir / quality_gates.QUALITY_GATES_SUMMARY_FILE).read_text(encoding="utf-8")
            self.assertIn('"solution_requested": "auto"', summary)
            self.assertIn('"solution": "GodotGame.sln"', summary)


if __name__ == "__main__":
    unittest.main()
