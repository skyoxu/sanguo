#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from unittest import mock
from pathlib import Path


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


dev_cli = _load_module("dev_cli_module", "scripts/python/dev_cli.py")


class DevCliRecoveryCommandsTests(unittest.TestCase):
    def test_new_execution_plan_should_forward_arguments(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "new-execution-plan",
                    "--title",
                    "demo-plan",
                    "--task-id",
                    "7",
                    "--run-id",
                    "abc123",
                    "--latest-json",
                    "logs/ci/2026-03-21/sc-review-pipeline-task-7/latest.json",
                    "--adr",
                    "docs/adr/ADR-0019-godot-security-baseline.md",
                ]
            )
        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/new_execution_plan.py"], cmd[:3])
        self.assertIn("--task-id", cmd)
        self.assertIn("7", cmd)
        self.assertIn("--run-id", cmd)
        self.assertIn("abc123", cmd)
        self.assertIn("--latest-json", cmd)

    def test_new_decision_log_should_forward_arguments(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "new-decision-log",
                    "--title",
                    "decision-demo",
                    "--task-id",
                    "5",
                    "--execution-plan",
                    "execution-plans/2026-03-21-demo.md",
                    "--supersedes",
                    "none",
                ]
            )
        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/new_decision_log.py"], cmd[:3])
        self.assertIn("--task-id", cmd)
        self.assertIn("5", cmd)
        self.assertIn("--execution-plan", cmd)
        self.assertIn("execution-plans/2026-03-21-demo.md", cmd)


if __name__ == "__main__":
    unittest.main()
