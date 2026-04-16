#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
import sys
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


util_module = _load_module("sc_util_module", "scripts/sc/_util.py")


class _FakeProcess:
    def __init__(self, returncode: int = 0, stdout: str = "ok\n") -> None:
        self.returncode = returncode
        self._stdout = stdout

    def communicate(self, timeout: int | None = None):  # noqa: ARG002
        return self._stdout, None

    def kill(self) -> None:
        return None


class RunCmdTests(unittest.TestCase):
    def test_run_cmd_should_replace_py_launcher_with_current_interpreter(self) -> None:
        captured: dict[str, object] = {}

        def fake_popen(args, **kwargs):
            captured["args"] = list(args)
            captured["kwargs"] = kwargs
            return _FakeProcess()

        with mock.patch.object(subprocess, "Popen", side_effect=fake_popen):
            rc, out = util_module.run_cmd(["py", "-3", "scripts/python/demo.py", "--task-id", "122"])

        self.assertEqual(0, rc)
        self.assertEqual("ok\n", out)
        self.assertEqual(
            [sys.executable, "scripts/python/demo.py", "--task-id", "122"],
            captured["args"],
        )


if __name__ == "__main__":
    unittest.main()
