#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
SC_DIR = REPO_ROOT / "scripts" / "sc"

for candidate in (PYTHON_DIR, SC_DIR):
    text = str(candidate)
    if text not in sys.path:
        sys.path.insert(0, text)


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gate_bundle = _load_module("gate_bundle_template_module", "scripts/python/run_gate_bundle.py")


class GateBundleTemplateTests(unittest.TestCase):
    def test_hard_mode_should_include_semantic_review_tier_gate(self) -> None:
        commands = gate_bundle._hard_gate_commands_with_options(
            [".taskmaster/tasks/tasks_back.json", ".taskmaster/tasks/tasks_gameplay.json"],
            False,
            -1,
        )
        by_name = {str(item["name"]): item for item in commands}

        self.assertIn("validate_semantic_review_tier", by_name)
        self.assertEqual(
            ["py", "-3", "scripts/python/validate_semantic_review_tier.py"],
            by_name["validate_semantic_review_tier"]["cmd"],
        )

    def test_missing_task_files_should_skip_semantic_review_tier_gate(self) -> None:
        skip_reason = gate_bundle._skip_reason_for_gate(
            "validate_semantic_review_tier",
            repo_root=REPO_ROOT,
            task_files=["logs/test-temp/missing_back.json", "logs/test-temp/missing_gameplay.json"],
        )
        self.assertEqual("missing_task_files", skip_reason)

    def test_hard_mode_should_include_signal_compliance_workflow_gate(self) -> None:
        commands = gate_bundle._hard_gate_commands_with_options(
            [".taskmaster/tasks/tasks_back.json", ".taskmaster/tasks/tasks_gameplay.json"],
            False,
            -1,
        )
        by_name = {str(item["name"]): item for item in commands}

        self.assertIn("signal_compliance_workflow_hard_gate", by_name)
        self.assertEqual(
            [
                "py",
                "-3",
                "scripts/python/check_signal_compliance_workflow_hard_gate.py",
                "--task-files",
                ".taskmaster/tasks/tasks_back.json",
                ".taskmaster/tasks/tasks_gameplay.json",
            ],
            by_name["signal_compliance_workflow_hard_gate"]["cmd"],
        )


if __name__ == "__main__":
    unittest.main()
