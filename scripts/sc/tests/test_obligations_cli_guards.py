#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from _taskmaster_fixture import staged_taskmaster_triplet


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "sc" / "llm_extract_task_obligations.py"


class ObligationsCliGuardTests(unittest.TestCase):
    def _extract_out_path(self, output: str) -> Path:
        match = re.search(r"\bout=([^\r\n]+)", output or "")
        if not match:
            raise AssertionError(f"missing out=... in output:\n{output}")
        return Path(match.group(1).strip())

    def _pick_task_id(self) -> str:
        tasks_path = REPO_ROOT / ".taskmaster" / "tasks" / "tasks.json"
        obj = json.loads(tasks_path.read_text(encoding="utf-8"))
        tasks = ((obj.get("master") or {}).get("tasks") or [])
        for task in tasks:
            if isinstance(task, dict) and str(task.get("id") or "").strip():
                return str(task.get("id"))
        raise AssertionError("No task id found in tasks.json")

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

    def test_dry_run_fingerprint_exits_without_llm(self) -> None:
        with staged_taskmaster_triplet():
            task_id = self._pick_task_id()
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--task-id", task_id, "--garbled-gate", "off", "--explain-reuse-miss", "--dry-run-fingerprint"],
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
        self.assertEqual(0, proc.returncode)
        self.assertIn("SC_LLM_OBLIGATIONS_FINGERPRINT status=ok", proc.stdout or "")
        self.assertIn("input_hash=", proc.stdout or "")
        self.assertIn("reuse_lookup_key=", proc.stdout or "")

    def test_dry_run_fingerprint_should_follow_standard_delivery_profile_security_default(self) -> None:
        with staged_taskmaster_triplet():
            task_id = self._pick_task_id()
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--task-id", task_id, "--delivery-profile", "standard", "--garbled-gate", "off", "--dry-run-fingerprint"],
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
        self.assertEqual(0, proc.returncode, proc.stdout)
        fingerprint_path = self._extract_out_path(proc.stdout or "")
        payload = json.loads(fingerprint_path.read_text(encoding="utf-8"))
        self.assertEqual("strict", payload.get("security_profile"))


if __name__ == "__main__":
    unittest.main()
