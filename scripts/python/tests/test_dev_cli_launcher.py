#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


def _load_module():
    path = REPO_ROOT / "scripts" / "python" / "dev_cli.py"
    spec = importlib.util.spec_from_file_location("dev_cli_module", path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["dev_cli_module"] = module
    spec.loader.exec_module(module)
    return module


dev_cli = _load_module()


class DevCliLauncherTests(unittest.TestCase):
    def test_run_should_replace_py_launcher_with_current_interpreter(self) -> None:
        captured: dict[str, object] = {}

        def fake_run(args, **kwargs):
            captured["args"] = list(args)
            captured["kwargs"] = kwargs
            return subprocess.CompletedProcess(args, 0)

        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            rc = dev_cli.run(["py", "-3", "scripts/python/resume_task.py", "--task-id", "122"])

        self.assertEqual(0, rc)
        self.assertEqual(
            [sys.executable, "scripts/python/resume_task.py", "--task-id", "122"],
            captured["args"],
        )
        self.assertEqual({"text": True}, captured["kwargs"])


if __name__ == "__main__":
    unittest.main()
