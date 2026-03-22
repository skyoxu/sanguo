#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from agent_to_agent_review import build_agent_review  # noqa: E402


class AgentToAgentReviewTests(unittest.TestCase):
    def test_build_agent_review_should_block_when_required_artifacts_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            payload, errors = build_agent_review(out_dir=out_dir, reviewer="artifact-reviewer")
            self.assertTrue(errors)
            self.assertEqual("block", payload["review_verdict"])
            self.assertEqual("fork", payload["explain"]["recommended_action"])
            self.assertIn("artifact-integrity", payload["explain"]["summary"])

    def test_build_agent_review_should_block_on_sc_test_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            summary = {
                "task_id": "1",
                "run_id": "abc123",
                "status": "fail",
                "steps": [
                    {
                        "name": "sc-test",
                        "status": "fail",
                        "rc": 1,
                        "cmd": ["py", "-3", "scripts/sc/test.py", "--task-id", "1"],
                        "log": str(out_dir / "sc-test.log"),
                    }
                ],
            }
            execution_context = {
                "task_id": "1",
                "run_id": "abc123",
                "status": "fail",
                "failed_step": "sc-test",
            }
            repair_guide = {
                "status": "needs-fix",
                "recommendations": [
                    {
                        "id": "sc-test-rerun",
                        "title": "Rerun isolated sc-test first",
                        "commands": ["py -3 scripts/sc/test.py --task-id 1"],
                    }
                ],
            }
            (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "execution-context.json").write_text(json.dumps(execution_context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "repair-guide.json").write_text(json.dumps(repair_guide, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "sc-test.log").write_text("unit failure\n", encoding="utf-8")

            payload, errors = build_agent_review(out_dir=out_dir, reviewer="artifact-reviewer")
            self.assertEqual([], errors)
            self.assertEqual("block", payload["review_verdict"])
            self.assertEqual("resume", payload["explain"]["recommended_action"])
            self.assertIn("isolated", payload["explain"]["summary"])

    def test_build_agent_review_should_mark_needs_fix_from_llm_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            llm_dir = out_dir / "llm"
            llm_dir.mkdir(parents=True, exist_ok=True)
            llm_summary = {
                "status": "warn",
                "results": [
                    {
                        "agent": "code-reviewer",
                        "status": "ok",
                        "output_path": "logs/ci/2026-03-19/sc-llm-review/review-code-reviewer.md",
                        "details": {"verdict": "Needs Fix"},
                    }
                ],
            }
            summary = {
                "task_id": "1",
                "run_id": "abc123",
                "status": "ok",
                "steps": [
                    {"name": "sc-test", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/test.py"], "log": str(out_dir / "sc-test.log")},
                    {"name": "sc-acceptance-check", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/acceptance_check.py"], "log": str(out_dir / "acc.log")},
                    {"name": "sc-llm-review", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/llm_review.py"], "log": str(out_dir / "llm.log"), "summary_file": str(llm_dir / "summary.json")},
                ],
            }
            execution_context = {"task_id": "1", "run_id": "abc123", "status": "ok", "failed_step": ""}
            repair_guide = {"status": "not-needed", "recommendations": []}
            (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "execution-context.json").write_text(json.dumps(execution_context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "repair-guide.json").write_text(json.dumps(repair_guide, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (llm_dir / "summary.json").write_text(json.dumps(llm_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "sc-test.log").write_text("ok\n", encoding="utf-8")
            (out_dir / "acc.log").write_text("ok\n", encoding="utf-8")
            (out_dir / "llm.log").write_text("warn\n", encoding="utf-8")

            payload, errors = build_agent_review(out_dir=out_dir, reviewer="artifact-reviewer")
            self.assertEqual([], errors)
            self.assertEqual("needs-fix", payload["review_verdict"])
            ids = {item["finding_id"] for item in payload["findings"]}
            self.assertIn("llm-code-reviewer-needs-fix", ids)
            self.assertEqual("resume", payload["explain"]["recommended_action"])
            self.assertIn("sc-llm-review", payload["explain"]["summary"])

    def test_build_agent_review_should_ignore_missing_llm_summary_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            summary = {
                "task_id": "1",
                "run_id": "abc123",
                "status": "ok",
                "steps": [
                    {"name": "sc-test", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/test.py"], "log": str(out_dir / "sc-test.log")},
                    {"name": "sc-acceptance-check", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/acceptance_check.py"], "log": str(out_dir / "acc.log")},
                    {"name": "sc-llm-review", "status": "planned", "rc": 0, "cmd": ["py", "-3", "scripts/sc/llm_review.py"]},
                ],
            }
            execution_context = {"task_id": "1", "run_id": "abc123", "status": "ok", "failed_step": ""}
            repair_guide = {"status": "not-needed", "recommendations": []}
            (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "execution-context.json").write_text(json.dumps(execution_context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "repair-guide.json").write_text(json.dumps(repair_guide, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "sc-test.log").write_text("ok\n", encoding="utf-8")
            (out_dir / "acc.log").write_text("ok\n", encoding="utf-8")

            payload, errors = build_agent_review(out_dir=out_dir, reviewer="artifact-reviewer")
            self.assertEqual([], errors)
            self.assertEqual("pass", payload["review_verdict"])
            ids = {item["finding_id"] for item in payload["findings"]}
            self.assertNotIn("llm-summary-invalid", ids)

    def test_build_agent_review_should_surface_denied_fork_approval_in_payload_and_explain(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            summary = {
                "task_id": "1",
                "run_id": "abc123",
                "status": "ok",
                "steps": [
                    {"name": "sc-test", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/test.py"], "log": str(out_dir / "sc-test.log")},
                    {"name": "sc-acceptance-check", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/acceptance_check.py"], "log": str(out_dir / "acc.log")},
                    {"name": "sc-llm-review", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/llm_review.py"], "log": str(out_dir / "llm.log")},
                ],
            }
            execution_context = {"task_id": "1", "run_id": "abc123", "status": "ok", "failed_step": ""}
            repair_guide = {
                "status": "needs-fix",
                "approval": {
                    "soft_gate": True,
                    "required_action": "fork",
                    "status": "denied",
                    "decision": "denied",
                    "reason": "Do not fork this run",
                    "request_path": str(out_dir / "approval-request.json"),
                    "response_path": str(out_dir / "approval-response.json"),
                },
                "recommendations": [
                    {
                        "id": "approval-fork-denied",
                        "title": "Fork recovery was denied",
                        "commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 1 --resume"],
                    }
                ],
            }
            (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "execution-context.json").write_text(json.dumps(execution_context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "repair-guide.json").write_text(json.dumps(repair_guide, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "sc-test.log").write_text("ok\n", encoding="utf-8")
            (out_dir / "acc.log").write_text("ok\n", encoding="utf-8")
            (out_dir / "llm.log").write_text("ok\n", encoding="utf-8")

            payload, errors = build_agent_review(out_dir=out_dir, reviewer="artifact-reviewer")

            self.assertEqual([], errors)
            self.assertEqual("denied", payload["approval"]["status"])
            self.assertEqual("fork", payload["approval"]["required_action"])
            self.assertFalse(payload["explain"]["approval_blocks_recommended_action"])
            self.assertEqual("denied", payload["explain"]["approval_status"])
            self.assertIn("Approval status is denied", payload["explain"]["summary"])

    def test_build_agent_review_should_block_when_sidecars_fail_schema_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            summary = {
                "task_id": "1",
                "run_id": "abc123",
                "status": "ok",
                "steps": [],
            }
            execution_context = {
                "task_id": "1",
                "run_id": "abc123",
                "status": "ok",
                "failed_step": "",
                "approval": "invalid",
            }
            repair_guide = {"status": "not-needed", "recommendations": []}
            (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "execution-context.json").write_text(json.dumps(execution_context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out_dir / "repair-guide.json").write_text(json.dumps(repair_guide, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            payload, errors = build_agent_review(out_dir=out_dir, reviewer="artifact-reviewer")

            self.assertTrue(errors)
            self.assertEqual("block", payload["review_verdict"])
            self.assertIn("schema validation failed", "\n".join(errors))
            self.assertEqual("fork", payload["explain"]["recommended_action"])


if __name__ == "__main__":
    unittest.main()
