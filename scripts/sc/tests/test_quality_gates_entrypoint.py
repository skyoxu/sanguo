#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
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
    def test_all_should_delegate_to_gate_bundle_hard_by_default(self) -> None:
        with mock.patch.object(quality_gates, "run_gate_bundle_hard", return_value=0) as bundle_mock, \
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
        with mock.patch.object(quality_gates, "run_gate_bundle_hard", return_value=0) as bundle_mock:
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

    def test_all_should_require_godot_bin_when_gdunit_or_smoke_is_requested(self) -> None:
        with mock.patch.object(quality_gates, "run_gate_bundle_hard", return_value=0) as bundle_mock, \
                mock.patch.object(quality_gates, "run_gdunit_hard") as gdunit_mock, \
                mock.patch.object(quality_gates, "run_smoke_headless") as smoke_mock:
            rc = quality_gates.main(["all", "--gdunit-hard"])

        self.assertEqual(2, rc)
        bundle_mock.assert_not_called()
        gdunit_mock.assert_not_called()
        smoke_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
