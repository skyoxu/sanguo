#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "sc" / "llm_check_subtasks_coverage.py"


class SubtasksCoverageCliGuardTests(unittest.TestCase):
    def test_strict_view_selection_requires_task_id(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--strict-view-selection"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        self.assertEqual(2, proc.returncode)
        self.assertIn("strict_view_selection_requires_task_id", proc.stdout or "")

    def test_requires_task_id_in_ci(self) -> None:
        env = dict(os.environ)
        env["CI"] = "1"
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        self.assertEqual(2, proc.returncode)
        self.assertIn("task_id_required_in_ci", proc.stdout or "")

    def test_self_check_exits_without_llm(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--self-check", "--max-schema-errors", "3"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        self.assertEqual(0, proc.returncode)
        self.assertIn("SC_LLM_SUBTASKS_COVERAGE_SELF_CHECK status=ok", proc.stdout or "")


if __name__ == "__main__":
    unittest.main()
