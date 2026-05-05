#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

import llm_check_subtasks_coverage as subtasks_script  # noqa: E402


class SubtasksCoverageSelectionPolicyTests(unittest.TestCase):
    def test_should_fail_with_strict_reason_when_selected_task_has_no_views(self) -> None:
        with tempfile.TemporaryDirectory(dir=str(REPO_ROOT)) as td:
            out_dir = Path(td) / "subtasks-coverage"
            triplet = SimpleNamespace(
                task_id="17",
                master={"title": "Task17", "subtasks": [{"id": "17.1", "title": "Subtask A"}]},
                back=None,
                gameplay=None,
            )
            with (
                patch.object(subtasks_script, "resolve_triplet", return_value=triplet),
                patch.object(subtasks_script, "ci_dir", return_value=out_dir),
                patch.object(subtasks_script, "run_subtasks_coverage_garbled_precheck", return_value=(True, {})),
                patch.object(
                    sys,
                    "argv",
                    ["llm_check_subtasks_coverage.py", "--task-id", "17", "--strict-view-selection", "--garbled-gate", "off"],
                ),
            ):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = subtasks_script.main()

            self.assertEqual(1, rc)
            self.assertIn("strict_view_selection_missing_acceptance_views", buf.getvalue())

    def test_summary_should_include_selection_policy_and_garbled_gate(self) -> None:
        with tempfile.TemporaryDirectory(dir=str(REPO_ROOT)) as td:
            out_dir = Path(td) / "subtasks-coverage"
            triplet = SimpleNamespace(
                task_id="17",
                master={"title": "Task17", "subtasks": []},
                back={"acceptance": ["ACC:T17.1 noop"]},
                gameplay=None,
            )
            with (
                patch.object(subtasks_script, "resolve_triplet", return_value=triplet),
                patch.object(subtasks_script, "ci_dir", return_value=out_dir),
                patch.object(subtasks_script, "run_subtasks_coverage_garbled_precheck", return_value=(True, {})),
                patch.object(
                    sys,
                    "argv",
                    ["llm_check_subtasks_coverage.py", "--task-id", "17", "--garbled-gate", "off"],
                ),
            ):
                rc = subtasks_script.main()

            self.assertEqual(0, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertIn("selection_policy", summary)
            self.assertIn("garbled_gate", summary)


if __name__ == "__main__":
    unittest.main()
