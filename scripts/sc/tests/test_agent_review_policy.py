#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _agent_review_policy import apply_agent_review_policy, summarize_agent_review  # noqa: E402


def _base_state() -> dict:
    return {
        "status": "fail",
        "resume_count": 1,
        "context_refresh_needed": False,
        "context_refresh_reasons": [],
        "steps": {
            "sc-test": {"status": "ok", "attempt_count": 1},
            "sc-acceptance-check": {"status": "ok", "attempt_count": 1},
            "sc-llm-review": {"status": "ok", "attempt_count": 1},
        },
    }


class AgentReviewPolicyTests(unittest.TestCase):
    def test_summarize_agent_review_should_prefer_resume_for_single_step_needs_fix(self) -> None:
        payload = {
            "review_verdict": "needs-fix",
            "findings": [
                {
                    "finding_id": "llm-code-reviewer-needs-fix",
                    "severity": "medium",
                    "category": "llm-review",
                    "owner_step": "sc-llm-review",
                    "evidence_path": "logs/ci/x/llm.json",
                    "message": "Needs Fix",
                    "suggested_fix": "Fix it",
                    "commands": [],
                }
            ],
        }

        signal = summarize_agent_review(payload)

        self.assertEqual("resume", signal["recommended_action"])
        self.assertEqual(["sc-llm-review"], signal["owner_steps"])
        self.assertEqual([], signal["recommended_refresh_reasons"])

    def test_summarize_agent_review_should_keep_single_medium_structural_finding_on_resume(self) -> None:
        payload = {
            "review_verdict": "needs-fix",
            "findings": [
                {
                    "finding_id": "acceptance-refs",
                    "severity": "medium",
                    "category": "acceptance-refs",
                    "owner_step": "sc-acceptance-check",
                    "evidence_path": "logs/ci/x/acceptance.json",
                    "message": "Acceptance refs drift",
                    "suggested_fix": "Align refs",
                    "commands": [],
                }
            ],
        }

        signal = summarize_agent_review(payload)

        self.assertEqual("resume", signal["recommended_action"])
        self.assertEqual([], signal["recommended_refresh_reasons"])

    def test_summarize_agent_review_should_refresh_for_single_high_structural_finding(self) -> None:
        payload = {
            "review_verdict": "needs-fix",
            "findings": [
                {
                    "finding_id": "acceptance-refs",
                    "severity": "high",
                    "category": "acceptance-refs",
                    "owner_step": "sc-acceptance-check",
                    "evidence_path": "logs/ci/x/acceptance.json",
                    "message": "Acceptance refs drift",
                    "suggested_fix": "Align refs",
                    "commands": [],
                }
            ],
        }

        signal = summarize_agent_review(payload)

        self.assertEqual("refresh", signal["recommended_action"])
        self.assertIn("agent_review_high_severity_refresh_category(acceptance-refs)", signal["recommended_refresh_reasons"])

    def test_summarize_agent_review_should_keep_cross_step_noise_on_resume(self) -> None:
        payload = {
            "review_verdict": "needs-fix",
            "findings": [
                {
                    "finding_id": "review-noise",
                    "severity": "medium",
                    "category": "review-noise",
                    "owner_step": "sc-llm-review",
                    "evidence_path": "logs/ci/x/llm.json",
                    "message": "Review noise",
                    "suggested_fix": "Trim noise",
                    "commands": [],
                },
                {
                    "finding_id": "naming",
                    "severity": "medium",
                    "category": "naming",
                    "owner_step": "sc-acceptance-check",
                    "evidence_path": "logs/ci/x/acceptance.json",
                    "message": "Naming mismatch",
                    "suggested_fix": "Rename consistently",
                    "commands": [],
                },
            ],
        }

        signal = summarize_agent_review(payload)

        self.assertEqual("resume", signal["recommended_action"])
        self.assertEqual([], signal["recommended_refresh_reasons"])

    def test_summarize_agent_review_should_fork_for_high_severity_artifact_integrity(self) -> None:
        payload = {
            "review_verdict": "needs-fix",
            "findings": [
                {
                    "finding_id": "artifact-integrity",
                    "severity": "high",
                    "category": "artifact-integrity",
                    "owner_step": "producer-pipeline",
                    "evidence_path": "logs/ci/x/summary.json",
                    "message": "Artifacts are inconsistent",
                    "suggested_fix": "Rebuild artifacts from a clean run",
                    "commands": [],
                }
            ],
        }

        signal = summarize_agent_review(payload)

        self.assertEqual("fork", signal["recommended_action"])
        self.assertIn("agent_review_high_severity_fork_category(artifact-integrity)", signal["recommended_refresh_reasons"])

    def test_summarize_agent_review_should_fork_for_summary_integrity_even_without_high_severity(self) -> None:
        payload = {
            "review_verdict": "block",
            "findings": [
                {
                    "finding_id": "summary-integrity",
                    "severity": "medium",
                    "category": "summary-integrity",
                    "owner_step": "producer-pipeline",
                    "evidence_path": "logs/ci/x/summary.json",
                    "message": "Summary contract drift",
                    "suggested_fix": "Rebuild the run from clean artifacts",
                    "commands": [],
                }
            ],
        }

        signal = summarize_agent_review(payload)

        self.assertEqual("fork", signal["recommended_action"])
        self.assertIn("agent_review_integrity_reset(summary-integrity)", signal["recommended_refresh_reasons"])

    def test_summarize_agent_review_should_request_refresh_for_cross_axis_needs_fix(self) -> None:
        payload = {
            "review_verdict": "needs-fix",
            "findings": [
                {
                    "finding_id": "acceptance-refs",
                    "severity": "medium",
                    "category": "acceptance-refs",
                    "owner_step": "sc-acceptance-check",
                    "evidence_path": "logs/ci/x/acceptance.json",
                    "message": "Acceptance refs drift",
                    "suggested_fix": "Align refs",
                    "commands": [],
                },
                {
                    "finding_id": "sc-test-failure",
                    "severity": "medium",
                    "category": "pipeline-step-failed",
                    "owner_step": "sc-test",
                    "evidence_path": "logs/ci/x/sc-test.log",
                    "message": "sc-test failed",
                    "suggested_fix": "Fix test failure",
                    "commands": [],
                },
            ],
        }

        signal = summarize_agent_review(payload)

        self.assertEqual("refresh", signal["recommended_action"])
        self.assertIn("agent_review_cross_step_needs_fix", signal["recommended_refresh_reasons"])
        self.assertIn("agent_review_semantic_axis_mix", signal["recommended_refresh_reasons"])

    def test_apply_agent_review_policy_should_prefer_fork_for_cross_step_block(self) -> None:
        state = _base_state()
        payload = {
            "review_verdict": "block",
            "findings": [
                {
                    "finding_id": "sc-test-failed",
                    "severity": "high",
                    "category": "pipeline-step-failed",
                    "owner_step": "sc-test",
                    "evidence_path": "logs/ci/x/sc-test.log",
                    "message": "sc-test failed",
                    "suggested_fix": "Fix project path",
                    "commands": [],
                },
                {
                    "finding_id": "llm-needs-fix",
                    "severity": "medium",
                    "category": "llm-review",
                    "owner_step": "sc-llm-review",
                    "evidence_path": "logs/ci/x/llm.json",
                    "message": "Needs Fix",
                    "suggested_fix": "Resolve review findings",
                    "commands": [],
                },
            ],
        }

        updated = apply_agent_review_policy(state, payload)

        self.assertTrue(updated["context_refresh_needed"])
        self.assertEqual("fork", updated["agent_review"]["recommended_action"])
        self.assertIn("agent_review_cross_step_block", updated["context_refresh_reasons"])


if __name__ == "__main__":
    unittest.main()
