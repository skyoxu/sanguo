#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "sc" / "llm_semantic_gate_all.py"


class SemanticGateAllCliGuardTests(unittest.TestCase):
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
        self.assertIn("SC_SEMANTIC_GATE_ALL_SELF_CHECK status=ok", proc.stdout or "")

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
        self.assertIn("SC_SEMANTIC_GATE_ALL_SELF_CHECK status=ok", proc.stdout or "")

    def test_invalid_batch_size_should_exit_two(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--batch-size", "0", "--garbled-gate", "off"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        self.assertEqual(2, proc.returncode)
        self.assertIn("--batch-size must be > 0", proc.stdout or "")

    def test_even_consensus_runs_should_exit_two(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--consensus-runs", "2", "--garbled-gate", "off"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        self.assertEqual(2, proc.returncode)
        self.assertIn("--consensus-runs must be an odd positive integer", proc.stdout or "")


if __name__ == "__main__":
    unittest.main()
