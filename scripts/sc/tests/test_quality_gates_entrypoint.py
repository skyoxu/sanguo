#!/usr/bin/env python3
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


class QualityGatesEntrypointTests(unittest.TestCase):
    def _call_main_in_test_mode(self, argv: list[str]) -> int:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            out_dir = td_path / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            dotnet_summary = td_path / "dotnet-summary.json"
            dotnet_summary.write_text(
                json.dumps(
                    {
                        "status": "ok",
                        "threshold_ok": True,
                        "coverage": {"lines": 0.0, "branches": 0.0},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            env = {
                "QUALITY_GATES_TEST_MODE": "1",
                "QUALITY_GATES_TEST_ARCH_HOTSPOTS_RC": "0",
                "QUALITY_GATES_TEST_OUT_DIR": str(out_dir),
                "QUALITY_GATES_TEST_DOTNET_SUMMARY_JSON": str(dotnet_summary),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                return quality_gates.main(argv)

    def test_all_should_resolve_test_solution_when_auto(self) -> None:
        with mock.patch.object(quality_gates, "resolve_test_solution_arg", return_value="Game.sln") as resolve_mock, \
                mock.patch.object(quality_gates, "run_gate_bundle_hard", return_value=0):
            rc = self._call_main_in_test_mode(["all", "--solution", "auto"])

        self.assertEqual(0, rc)
        resolve_mock.assert_called_once_with("auto")

    def test_all_should_delegate_to_gate_bundle_hard_by_default(self) -> None:
        with mock.patch.object(quality_gates, "build_gate_bundle_hard_cmd", return_value=["py", "-3", "scripts/python/run_gate_bundle.py"]) as build_cmd_mock, \
                mock.patch.object(quality_gates, "_run_and_stream", return_value=0) as run_mock, \
                mock.patch.object(quality_gates, "run_gdunit_hard") as gdunit_mock, \
                mock.patch.object(quality_gates, "run_smoke_headless") as smoke_mock:
            rc = self._call_main_in_test_mode(["all"])

        self.assertEqual(0, rc)
        build_cmd_mock.assert_called_once_with(
            delivery_profile="",
            task_files=quality_gates.DEFAULT_GATE_BUNDLE_TASK_FILES,
            out_dir=mock.ANY,
            run_id="",
        )
        run_mock.assert_called_once_with(["py", "-3", "scripts/python/run_gate_bundle.py"])
        gdunit_mock.assert_not_called()
        smoke_mock.assert_not_called()

    def test_all_should_forward_gate_bundle_runtime_options(self) -> None:
        with mock.patch.object(quality_gates, "build_gate_bundle_hard_cmd", return_value=["py", "-3", "scripts/python/run_gate_bundle.py"]) as build_cmd_mock, \
                mock.patch.object(quality_gates, "_run_and_stream", return_value=0) as run_mock:
            rc = self._call_main_in_test_mode(
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
        build_cmd_mock.assert_called_once_with(
            delivery_profile="standard",
            task_files=["custom/tasks_back.json", "custom/tasks_gameplay.json"],
            out_dir=mock.ANY,
            run_id="local-demo",
        )
        run_mock.assert_called_once_with(["py", "-3", "scripts/python/run_gate_bundle.py"])

    def test_all_should_append_gdunit_and_smoke_when_enabled(self) -> None:
        with mock.patch.object(quality_gates, "build_gate_bundle_hard_cmd", return_value=["py", "-3", "scripts/python/run_gate_bundle.py"]) as build_cmd_mock, \
                mock.patch.object(quality_gates, "_run_and_stream", return_value=0) as run_mock, \
                mock.patch.object(quality_gates, "run_gdunit_hard", return_value=0) as gdunit_mock, \
                mock.patch.object(quality_gates, "run_smoke_headless_with_exit_on_ready", return_value=0) as smoke_with_env_mock:
            rc = self._call_main_in_test_mode(
                [
                    "all",
                    "--gdunit-hard",
                    "--smoke",
                    "--godot-bin",
                    "C:/Godot/Godot.exe",
                ]
            )

        self.assertEqual(0, rc)
        build_cmd_mock.assert_called_once()
        run_mock.assert_called_once_with(["py", "-3", "scripts/python/run_gate_bundle.py"])
        gdunit_mock.assert_called_once_with("C:/Godot/Godot.exe")
        smoke_with_env_mock.assert_called_once_with("C:/Godot/Godot.exe")

    def test_all_should_require_godot_bin_when_gdunit_or_smoke_is_requested(self) -> None:
        with mock.patch.object(quality_gates, "run_gate_bundle_hard", return_value=0) as bundle_mock, \
                mock.patch.object(quality_gates, "run_gdunit_hard") as gdunit_mock, \
                mock.patch.object(quality_gates, "run_smoke_headless") as smoke_mock:
            rc = self._call_main_in_test_mode(["all", "--gdunit-hard"])

        self.assertEqual(2, rc)
        bundle_mock.assert_not_called()
        gdunit_mock.assert_not_called()
        smoke_mock.assert_not_called()

    def test_run_smoke_headless_with_exit_on_ready_should_set_and_restore_env(self) -> None:
        observed: dict[str, str | None] = {}
        original_exit_on_ready = os.environ.get("GD_SMOKE_EXIT_ON_READY")
        original_exit_delay = os.environ.get("GD_SMOKE_EXIT_DELAY_SEC")
        os.environ.pop("GD_SMOKE_EXIT_ON_READY", None)
        os.environ.pop("GD_SMOKE_EXIT_DELAY_SEC", None)
        try:
            def _fake_run(_: str) -> int:
                observed["exit_on_ready"] = os.environ.get("GD_SMOKE_EXIT_ON_READY")
                observed["exit_delay"] = os.environ.get("GD_SMOKE_EXIT_DELAY_SEC")
                return 0

            with mock.patch.object(quality_gates, "run_smoke_headless", side_effect=_fake_run):
                rc = quality_gates.run_smoke_headless_with_exit_on_ready("C:/Godot/Godot.exe")
            self.assertEqual(0, rc)
            self.assertEqual("1", observed.get("exit_on_ready"))
            self.assertEqual("0.25", observed.get("exit_delay"))
            self.assertNotIn("GD_SMOKE_EXIT_ON_READY", os.environ)
            self.assertNotIn("GD_SMOKE_EXIT_DELAY_SEC", os.environ)
        finally:
            if original_exit_on_ready is None:
                os.environ.pop("GD_SMOKE_EXIT_ON_READY", None)
            else:
                os.environ["GD_SMOKE_EXIT_ON_READY"] = original_exit_on_ready
            if original_exit_delay is None:
                os.environ.pop("GD_SMOKE_EXIT_DELAY_SEC", None)
            else:
                os.environ["GD_SMOKE_EXIT_DELAY_SEC"] = original_exit_delay

    def test_all_should_treat_perf_audit_arch_failures_as_advisory_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            out_dir = td_path / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            dotnet_summary = td_path / "dotnet-summary.json"
            dotnet_summary.write_text(
                json.dumps(
                    {
                        "status": "ok",
                        "threshold_ok": True,
                        "coverage": {"lines": 0.0, "branches": 0.0},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            def _fake_run(cmd: list[str]) -> int:
                s = " ".join(cmd)
                if "validate_perf.py" in s:
                    return 1
                if "validate_audit_logs.py" in s:
                    return 1
                if "check_architecture_hotspots.py" in s:
                    return 1
                return 0

            env = {
                "QUALITY_GATES_TEST_DOTNET_SUMMARY_JSON": str(dotnet_summary),
            }
            with mock.patch.dict(os.environ, env, clear=False), \
                    mock.patch.object(quality_gates, "_run_and_stream", side_effect=_fake_run):
                rc = quality_gates.main(["all", "--out-dir", str(out_dir)])

            self.assertEqual(0, rc)
            summary = json.loads((Path("logs/ci") / quality_gates._today() / "quality-gates-summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", summary.get("status"))
            self.assertEqual([], summary.get("reasons"))
            self.assertIn("perf_gate_failed", summary.get("advisory_reasons", []))
            self.assertIn("audit_gate_failed", summary.get("advisory_reasons", []))
            self.assertIn("architecture_hotspots_failed", summary.get("advisory_reasons", []))

    def test_all_should_block_on_perf_audit_arch_when_require_flags_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            out_dir = td_path / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            dotnet_summary = td_path / "dotnet-summary.json"
            dotnet_summary.write_text(
                json.dumps(
                    {
                        "status": "ok",
                        "threshold_ok": True,
                        "coverage": {"lines": 0.0, "branches": 0.0},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            def _fake_run(cmd: list[str]) -> int:
                s = " ".join(cmd)
                if "validate_perf.py" in s:
                    return 1
                if "validate_audit_logs.py" in s:
                    return 1
                if "check_architecture_hotspots.py" in s:
                    return 1
                return 0

            env = {
                "QUALITY_GATES_TEST_DOTNET_SUMMARY_JSON": str(dotnet_summary),
            }
            with mock.patch.dict(os.environ, env, clear=False), \
                    mock.patch.object(quality_gates, "_run_and_stream", side_effect=_fake_run):
                rc = quality_gates.main(
                    [
                        "all",
                        "--out-dir",
                        str(out_dir),
                        "--require-perf",
                        "--require-audit",
                        "--require-arch-hotspots",
                    ]
                )

            self.assertEqual(1, rc)
            summary = json.loads((Path("logs/ci") / quality_gates._today() / "quality-gates-summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary.get("status"))
            self.assertIn("perf_gate_failed", summary.get("reasons", []))
            self.assertIn("audit_gate_failed", summary.get("reasons", []))
            self.assertIn("architecture_hotspots_failed", summary.get("reasons", []))


if __name__ == "__main__":
    unittest.main()
