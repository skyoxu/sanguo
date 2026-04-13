#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "sc" / "llm_fill_acceptance_refs.py"


class FillAcceptanceRefsCliGuardTests(unittest.TestCase):
    def test_self_check_should_exit_zero(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--self-check"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        self.assertEqual(0, proc.returncode)
        self.assertIn("SC_LLM_ACCEPTANCE_REFS_SELF_CHECK status=ok", proc.stdout or "")

    def test_self_check_should_accept_explicit_openai_backend(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--self-check", "--llm-backend", "openai-api"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        self.assertEqual(0, proc.returncode)
        self.assertIn("SC_LLM_ACCEPTANCE_REFS_SELF_CHECK status=ok", proc.stdout or "")

    def test_missing_target_args_should_exit_two(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--consensus-runs", "1"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        self.assertEqual(2, proc.returncode)
        self.assertIn("specify --task-id <n> or --all", proc.stdout or "")


if __name__ == "__main__":
    unittest.main()
