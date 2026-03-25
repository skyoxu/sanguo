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


dev_cli = _load_module("dev_cli_project_health_module", "scripts/python/dev_cli.py")


class DevCliProjectHealthCommandsTests(unittest.TestCase):
    def test_detect_project_stage_should_delegate_to_script(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(["detect-project-stage", "--repo-root", "demo-root"])

        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/detect_project_stage.py"], cmd[:3])
        self.assertIn("--repo-root", cmd)
        self.assertIn("demo-root", cmd)

    def test_doctor_project_should_delegate_to_script(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(["doctor-project", "--repo-root", "demo-root"])

        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/doctor_project.py"], cmd[:3])
        self.assertIn("--repo-root", cmd)
        self.assertIn("demo-root", cmd)

    def test_check_directory_boundaries_should_delegate_to_script(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(["check-directory-boundaries", "--repo-root", "demo-root"])

        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/check_directory_boundaries.py"], cmd[:3])
        self.assertIn("--repo-root", cmd)
        self.assertIn("demo-root", cmd)

    def test_project_health_scan_should_delegate_to_script(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(["project-health-scan", "--repo-root", "demo-root"])

        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/project_health_scan.py"], cmd[:3])
        self.assertIn("--repo-root", cmd)
        self.assertIn("demo-root", cmd)

    def test_project_health_scan_should_forward_serve_flags(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(["project-health-scan", "--repo-root", "demo-root", "--serve", "--port", "8772"])

        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertIn("--serve", cmd)
        self.assertIn("--port", cmd)
        self.assertIn("8772", cmd)

    def test_serve_project_health_should_delegate_to_script(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(["serve-project-health", "--repo-root", "demo-root", "--port", "8771"])

        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/serve_project_health.py"], cmd[:3])
        self.assertIn("--repo-root", cmd)
        self.assertIn("demo-root", cmd)
        self.assertIn("--port", cmd)
        self.assertIn("8771", cmd)


if __name__ == "__main__":
    unittest.main()
