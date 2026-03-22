#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _agent_review_contract import make_review_payload, render_review_markdown, validate_review_payload  # noqa: E402


class AgentReviewContractTests(unittest.TestCase):
    def test_validate_review_payload_should_accept_valid_payload(self) -> None:
        payload = make_review_payload(
            task_id="1",
            run_id="abc123",
            pipeline_out_dir="logs/ci/2026-03-19/sc-review-pipeline-task-1-abc123",
            pipeline_status="ok",
            failed_step="",
            review_verdict="pass",
            reviewer="artifact-reviewer",
            findings=[],
        )
        self.assertEqual([], validate_review_payload(payload))

    def test_validate_review_payload_should_reject_bad_verdict(self) -> None:
        payload = make_review_payload(
            task_id="1",
            run_id="abc123",
            pipeline_out_dir="logs/ci/2026-03-19/sc-review-pipeline-task-1-abc123",
            pipeline_status="ok",
            failed_step="",
            review_verdict="bad",
            reviewer="artifact-reviewer",
            findings=[],
        )
        errors = validate_review_payload(payload)
        self.assertTrue(any("$.review_verdict" in item for item in errors))

    def test_render_review_markdown_should_include_findings(self) -> None:
        payload = make_review_payload(
            task_id="1",
            run_id="abc123",
            pipeline_out_dir="logs/ci/2026-03-19/sc-review-pipeline-task-1-abc123",
            pipeline_status="fail",
            failed_step="sc-test",
            review_verdict="block",
            reviewer="artifact-reviewer",
            findings=[
                {
                    "finding_id": "sc-test-failed",
                    "severity": "high",
                    "category": "pipeline-step-failed",
                    "owner_step": "sc-test",
                    "evidence_path": "logs/ci/2026-03-19/sc-test.log",
                    "message": "sc-test failed",
                    "suggested_fix": "Fix the failing unit test first.",
                    "commands": ["py -3 scripts/sc/test.py --task-id 1"],
                }
            ],
        )
        rendered = render_review_markdown(payload)
        self.assertIn("review_verdict: block", rendered)
        self.assertIn("sc-test-failed", rendered)

    def test_render_review_markdown_should_include_approval_section(self) -> None:
        payload = make_review_payload(
            task_id="1",
            run_id="abc123",
            pipeline_out_dir="logs/ci/2026-03-19/sc-review-pipeline-task-1-abc123",
            pipeline_status="ok",
            failed_step="",
            review_verdict="needs-fix",
            reviewer="artifact-reviewer",
            findings=[],
            approval={
                "required_action": "fork",
                "status": "pending",
                "decision": "",
                "reason": "Await operator approval",
                "request_path": "logs/ci/x/approval-request.json",
                "response_path": "",
            },
        )
        rendered = render_review_markdown(payload)
        self.assertIn("## Approval", rendered)
        self.assertIn("status: pending", rendered)


if __name__ == "__main__":
    unittest.main()
