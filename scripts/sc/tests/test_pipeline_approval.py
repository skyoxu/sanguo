#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _pipeline_approval as pipeline_approval  # noqa: E402


class PipelineApprovalTests(unittest.TestCase):
    def test_sync_soft_approval_sidecars_should_preserve_pending_request_without_rewriting(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-1-run1"
            out_dir.mkdir(parents=True, exist_ok=True)

            summary = {"status": "fail", "steps": [{"name": "sc-test", "status": "fail"}]}
            repair_guide = {
                "recommendations": [
                    {
                        "id": "approval-fork-pending",
                        "title": "Fork recovery is pending approval",
                        "commands": [],
                        "files": [],
                    }
                ],
                "approval": {
                    "soft_gate": True,
                    "required_action": "fork",
                    "status": "pending",
                    "decision": "",
                    "reason": "A fork request exists, but no approval response is available yet.",
                    "request_id": "run1:fork",
                    "request_path": str(out_dir / "approval-request.json"),
                    "response_path": "",
                },
            }

            first = pipeline_approval.sync_soft_approval_sidecars(
                out_dir=out_dir,
                task_id="1",
                run_id="run1",
                summary=summary,
                repair_guide=repair_guide,
                marathon_state={},
                explicit_fork=False,
            )
            second = pipeline_approval.sync_soft_approval_sidecars(
                out_dir=out_dir,
                task_id="1",
                run_id="run1",
                summary=summary,
                repair_guide=repair_guide,
                marathon_state={},
                explicit_fork=False,
            )

            self.assertEqual("pending", first["status"])
            self.assertEqual("pending", second["status"])
            self.assertEqual("fork", second["required_action"])
            self.assertTrue((out_dir / "approval-request.json").exists())
            self.assertEqual(1, len(first["events"]))
            self.assertEqual("approval_request_written", first["events"][0]["event"])
            self.assertEqual([], second["events"])


if __name__ == "__main__":
    unittest.main()
