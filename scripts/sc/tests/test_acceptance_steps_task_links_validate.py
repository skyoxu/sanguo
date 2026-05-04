#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

import _acceptance_steps as acceptance_steps  # noqa: E402


class AcceptanceStepsTaskLinksValidateTests(unittest.TestCase):
    def test_should_call_task_links_validate_with_mode_all_by_default(self) -> None:
        captured: dict[str, object] = {}

        def _fake_run_and_capture(out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> acceptance_steps.StepResult:
            captured["name"] = name
            captured["cmd"] = cmd
            captured["timeout"] = timeout_sec
            return acceptance_steps.StepResult(name=name, status="ok", rc=0, cmd=cmd, log=str(out_dir / f"{name}.log"))

        with tempfile.TemporaryDirectory(dir=str(REPO_ROOT)) as td:
            out_dir = Path(td)
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(acceptance_steps, "run_and_capture", side_effect=_fake_run_and_capture):
                    res = acceptance_steps.step_task_links_validate(out_dir)

        self.assertEqual("ok", res.status)
        self.assertEqual("task-links-validate", captured.get("name"))
        cmd = captured.get("cmd")
        self.assertIsInstance(cmd, list)
        self.assertIn("--mode", cmd)
        self.assertIn("all", cmd)
        self.assertNotIn("--max-warnings", cmd)
        self.assertEqual(300, captured.get("timeout"))

    def test_should_forward_warning_budget_from_env(self) -> None:
        captured: dict[str, object] = {}

        def _fake_run_and_capture(out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> acceptance_steps.StepResult:
            captured["cmd"] = cmd
            return acceptance_steps.StepResult(name=name, status="ok", rc=0, cmd=cmd, log=str(out_dir / f"{name}.log"))

        with tempfile.TemporaryDirectory(dir=str(REPO_ROOT)) as td:
            out_dir = Path(td)
            with patch.dict(os.environ, {"TASK_LINKS_MAX_WARNINGS": "73"}, clear=True):
                with patch.object(acceptance_steps, "run_and_capture", side_effect=_fake_run_and_capture):
                    _ = acceptance_steps.step_task_links_validate(out_dir)

        cmd = captured.get("cmd")
        self.assertIsInstance(cmd, list)
        self.assertIn("--max-warnings", cmd)
        idx = cmd.index("--max-warnings")
        self.assertEqual("73", cmd[idx + 1])


if __name__ == "__main__":
    unittest.main()
