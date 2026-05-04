#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
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


guard = _load_module("preflight_acceptance_extract_guard_module", "scripts/python/preflight_acceptance_extract_guard.py")


class PreflightAcceptanceExtractGuardTests(unittest.TestCase):
    def test_evaluate_task_should_flag_missing_refs_and_missing_task_specific_tests(self) -> None:
        master = {
            "id": "200",
            "title": "Module: sample hard gate",
            "details": "Task requires hard gate behavior.",
            "testStrategy": "Task-specific deterministic tests.",
        }
        back = {"acceptance": ["Task verifies hard gate behavior."]}
        gameplay = {"acceptance": ["Task verifies hard gate behavior and must not advance on failure. Refs: Tests/Fake.cs"]}

        payload = guard.evaluate_task(task_id="200", master=master, back=back, gameplay=gameplay)

        self.assertEqual("fail", payload["status"])
        self.assertIn("missing_refs", payload["issue_ids"])
        self.assertIn("task_specific_deterministic_tests_missing", payload["issue_ids"])

    def test_evaluate_task_should_pass_when_split_and_hard_gate_language_is_explicit(self) -> None:
        master = {
            "id": "201",
            "title": "Module: integration pack",
            "details": "Integration closure check from split-task evidence; implementation is moved to tasks 301, 302.",
            "testStrategy": "Task-specific deterministic tests.",
        }
        acceptance = [
            "Task-specific deterministic tests are required evidence for closure. Refs: Game.Core.Tests/Tasks/Task201Tests.cs",
            "Split-task evidence from tasks 301 and 302 is required, and the task must not advance if that evidence is missing. Refs: Game.Core.Tests/Tasks/Task201Tests.cs",
        ]

        payload = guard.evaluate_task(task_id="201", master=master, back={"acceptance": acceptance}, gameplay={"acceptance": acceptance})

        self.assertEqual("ok", payload["status"])
        self.assertEqual([], payload["issue_ids"])


if __name__ == "__main__":
    unittest.main()
