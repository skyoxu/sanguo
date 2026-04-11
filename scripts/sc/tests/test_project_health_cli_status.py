#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import json
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


project_health_scan_module = _load_module("project_health_scan_status_test_module", "scripts/python/project_health_scan.py")
serve_project_health_module = _load_module("serve_project_health_status_test_module", "scripts/python/serve_project_health.py")
cli_status_module = _load_module("project_health_cli_status_test_module", "scripts/python/_project_health_cli_status.py")


class ProjectHealthCliStatusTests(unittest.TestCase):
    def test_cli_status_examples_should_match_renderers(self) -> None:
        scan_ok = (
            REPO_ROOT / "docs" / "workflows" / "examples" / "sc-project-health-scan.stdout.example.txt"
        ).read_text(encoding="utf-8")
        scan_ci_fail = (
            REPO_ROOT / "docs" / "workflows" / "examples" / "sc-project-health-scan-ci-fail.stdout.example.txt"
        ).read_text(encoding="utf-8")
        server_ok = (
            REPO_ROOT / "docs" / "workflows" / "examples" / "sc-project-health-server.stdout.example.txt"
        ).read_text(encoding="utf-8")
        server_ci_fail = (
            REPO_ROOT / "docs" / "workflows" / "examples" / "sc-project-health-server-ci-fail.stdout.example.txt"
        ).read_text(encoding="utf-8")

        self.assertEqual(
            scan_ok,
            cli_status_module.render_project_health_scan_status_line(
                status="warn",
                url="http://127.0.0.1:8765/latest.html",
            )
            + "\n",
        )
        self.assertEqual(scan_ci_fail, cli_status_module.render_project_health_scan_ci_fail_line() + "\n")
        self.assertEqual(
            server_ok,
            cli_status_module.render_project_health_server_status_line(
                reused=False,
                url="http://127.0.0.1:8765/latest.html",
                server_json="logs/ci/project-health/server.json",
            )
            + "\n",
        )
        self.assertEqual(server_ci_fail, cli_status_module.render_project_health_server_ci_fail_line() + "\n")

    def test_project_health_scan_main_should_print_stable_status_line(self) -> None:
        stdout = io.StringIO()
        with mock.patch.object(
            project_health_scan_module,
            "project_health_scan",
            return_value={"kind": "project-health-scan", "status": "warn", "exit_code": 0, "results": []},
        ), mock.patch.object(
            project_health_scan_module,
            "ensure_project_health_server",
            return_value={"url": "http://127.0.0.1:8765/latest.html"},
        ), mock.patch("sys.stdout", stdout):
            rc = project_health_scan_module.main(["--repo-root", "demo-root", "--serve"])

        self.assertEqual(0, rc)
        self.assertEqual(
            "PROJECT_HEALTH_SCAN status=warn dashboard=logs/ci/project-health/latest.html url=http://127.0.0.1:8765/latest.html\n",
            stdout.getvalue(),
        )

    def test_project_health_scan_main_should_print_ci_fail_status_line(self) -> None:
        stdout = io.StringIO()
        with mock.patch.dict(project_health_scan_module.os.environ, {"CI": "1"}, clear=False), mock.patch("sys.stdout", stdout):
            rc = project_health_scan_module.main(["--serve"])

        self.assertEqual(2, rc)
        self.assertEqual("PROJECT_HEALTH_SCAN status=fail reason=serve_not_allowed_in_ci\n", stdout.getvalue())

    def test_serve_project_health_main_should_print_stable_status_line(self) -> None:
        stdout = io.StringIO()
        with mock.patch.object(
            serve_project_health_module,
            "ensure_project_health_server",
            return_value={
                "reused": False,
                "url": "http://127.0.0.1:8765/latest.html",
                "server_json": "logs/ci/project-health/server.json",
            },
        ), mock.patch("sys.stdout", stdout):
            rc = serve_project_health_module.main(["--repo-root", "demo-root"])

        self.assertEqual(0, rc)
        self.assertEqual(
            "PROJECT_HEALTH_SERVER status=ok reused=false url=http://127.0.0.1:8765/latest.html server_json=logs/ci/project-health/server.json\n",
            stdout.getvalue(),
        )

    def test_serve_project_health_main_should_print_ci_fail_status_line(self) -> None:
        stdout = io.StringIO()
        with mock.patch.dict(serve_project_health_module.os.environ, {"CI": "1"}, clear=False), mock.patch("sys.stdout", stdout):
            rc = serve_project_health_module.main([])

        self.assertEqual(2, rc)
        self.assertEqual("PROJECT_HEALTH_SERVER status=fail reason=serve_not_allowed_in_ci\n", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
