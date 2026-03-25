#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import socket
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


server_module = _load_module("project_health_server_test_module", "scripts/python/_project_health_server.py")
scan_cli_module = _load_module("project_health_scan_cli_test_module", "scripts/python/project_health_scan.py")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ProjectHealthServerTests(unittest.TestCase):
    def test_choose_available_port_should_skip_busy_port(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((server_module.HOST, 0))
            sock.listen(1)
            busy_port = sock.getsockname()[1]
            selected = server_module.choose_available_port(preferred_port=0, start=busy_port, end=busy_port + 3)
        self.assertNotEqual(busy_port, selected)

    def test_ensure_project_health_server_should_reuse_existing_live_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(root / "logs" / "ci" / "project-health" / "latest.html", "<html></html>\n")
            sidecar = root / "logs" / "ci" / "project-health" / "server.json"
            sidecar.write_text(
                json.dumps(
                    {
                        "repo_root": str(root.resolve()).replace("\\", "/"),
                        "port": 8765,
                        "pid": 4321,
                        "url": "http://127.0.0.1:8765/latest.html",
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(server_module, "is_process_alive", return_value=True), mock.patch.object(
                server_module,
                "port_accepts_connections",
                return_value=True,
            ), mock.patch.object(server_module, "spawn_detached_http_server") as spawn_mock:
                payload = server_module.ensure_project_health_server(root=root)

            self.assertTrue(payload["reused"])
            self.assertEqual(8765, payload["port"])
            spawn_mock.assert_not_called()

    def test_ensure_project_health_server_should_spawn_and_write_server_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(root / "logs" / "ci" / "project-health" / "latest.html", "<html></html>\n")

            with mock.patch.object(server_module, "spawn_detached_http_server", return_value=5555) as spawn_mock, mock.patch.object(
                server_module,
                "wait_until_port_open",
                return_value=True,
            ):
                payload = server_module.ensure_project_health_server(root=root, preferred_port=8777)

            sidecar = json.loads((root / "logs" / "ci" / "project-health" / "server.json").read_text(encoding="utf-8"))
            self.assertFalse(payload["reused"])
            self.assertEqual(8777, payload["port"])
            self.assertEqual(5555, payload["pid"])
            self.assertEqual("http://127.0.0.1:8777/latest.html", payload["url"])
            self.assertEqual(8777, sidecar["port"])
            spawn_mock.assert_called_once()

    def test_project_health_scan_cli_should_optionally_serve(self) -> None:
        with mock.patch.object(
            scan_cli_module,
            "project_health_scan",
            return_value={"status": "warn", "exit_code": 0},
        ), mock.patch.object(
            scan_cli_module,
            "ensure_project_health_server",
            return_value={"url": "http://127.0.0.1:8765/latest.html", "reused": False},
        ) as ensure_mock:
            rc = scan_cli_module.main(["--repo-root", "demo-root", "--serve", "--port", "8765"])

        self.assertEqual(0, rc)
        ensure_mock.assert_called_once()
        self.assertEqual("demo-root", ensure_mock.call_args.kwargs["root"])
        self.assertEqual(8765, ensure_mock.call_args.kwargs["preferred_port"])

    def test_project_health_scan_cli_should_reject_serve_in_ci(self) -> None:
        with mock.patch.dict(scan_cli_module.os.environ, {"CI": "1"}):
            rc = scan_cli_module.main(["--serve"])
        self.assertEqual(2, rc)


if __name__ == "__main__":
    unittest.main()
