#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _repair_guidance import build_execution_context, build_repair_guide, render_repair_guide_markdown  # noqa: E402


class RepairGuidanceTests(unittest.TestCase):
    def test_build_execution_context_should_expose_marathon_recovery_pointers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            payload = build_execution_context(
                task_id="1",
                requested_run_id="abc",
                run_id="def",
                out_dir=out_dir,
                delivery_profile="fast-ship",
                security_profile="host-safe",
                summary={"status": "fail", "steps": [{"name": "sc-test", "status": "fail"}]},
                marathon_state={
                    "diff_stats": {
                        "baseline": {"total_lines": 10, "categories": ["scripts"], "axes": ["implementation"]},
                        "current": {"total_lines": 70, "categories": ["docs", "scripts"], "axes": ["governance", "implementation"]},
                        "growth": {"total_lines": 60, "new_categories": ["docs"], "new_axes": ["governance"]},
                    }
                },
            )
            self.assertEqual(str(out_dir / "marathon-state.json"), payload["paths"]["marathon_state_json"])
            self.assertEqual("py -3 scripts/sc/run_review_pipeline.py --task-id 1 --resume", payload["recovery"]["resume_command"])
            self.assertEqual("py -3 scripts/sc/run_review_pipeline.py --task-id 1 --abort", payload["recovery"]["abort_command"])
            self.assertEqual(10, payload["marathon"]["diff_baseline_total_lines"])
            self.assertEqual(70, payload["marathon"]["diff_current_total_lines"])
            self.assertEqual(60, payload["marathon"]["diff_growth_total_lines"])
            self.assertEqual(["docs", "scripts"], payload["marathon"]["diff_current_categories"])
            self.assertEqual(["governance", "implementation"], payload["marathon"]["diff_current_axes"])
            self.assertEqual(["docs"], payload["marathon"]["diff_growth_new_categories"])
            self.assertEqual(["governance"], payload["marathon"]["diff_growth_new_axes"])

    def test_build_repair_guide_should_mark_not_needed_when_no_failed_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            summary = {
                "status": "ok",
                "steps": [
                    {"name": "sc-test", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/test.py"]},
                ],
            }
            payload = build_repair_guide(summary, task_id="1", out_dir=out_dir)
            self.assertEqual("not-needed", payload["status"])
            self.assertEqual([], payload["recommendations"])

    def test_build_repair_guide_should_suggest_project_path_fix_for_msb1009(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            log_path = out_dir / "sc-test.log"
            log_path.write_text("MSBUILD : error MSB1009: Project file does not exist.\n", encoding="utf-8")
            summary = {
                "status": "fail",
                "steps": [
                    {
                        "name": "sc-test",
                        "status": "fail",
                        "rc": 1,
                        "cmd": ["py", "-3", "scripts/sc/test.py", "--task-id", "1"],
                        "log": str(log_path),
                    },
                ],
            }
            payload = build_repair_guide(summary, task_id="1", out_dir=out_dir)
            self.assertEqual("needs-fix", payload["status"])
            ids = {item["id"] for item in payload["recommendations"]}
            self.assertIn("pipeline-resume", ids)
            self.assertIn("sc-test-project-path", ids)

    def test_build_repair_guide_should_suggest_acceptance_test_refs_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            log_path = out_dir / "sc-acceptance-check.log"
            log_path.write_text("validate_task_test_refs failed under require-task-test-refs\n", encoding="utf-8")
            summary = {
                "status": "fail",
                "steps": [
                    {
                        "name": "sc-acceptance-check",
                        "status": "fail",
                        "rc": 1,
                        "cmd": ["py", "-3", "scripts/sc/acceptance_check.py", "--task-id", "1"],
                        "log": str(log_path),
                    },
                ],
            }
            payload = build_repair_guide(summary, task_id="1", out_dir=out_dir)
            ids = {item["id"] for item in payload["recommendations"]}
            self.assertIn("acceptance-test-refs", ids)

    def test_build_repair_guide_should_suggest_context_refresh_when_marathon_state_requests_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            log_path = out_dir / "sc-test.log"
            log_path.write_text("generic failure\n", encoding="utf-8")
            (out_dir / "marathon-state.json").write_text(
                """{
  "schema_version": "1.0.0",
  "task_id": "1",
  "run_id": "abc",
  "status": "fail",
  "context_refresh_needed": true,
  "context_refresh_reasons": ["step_failures:sc-test>=2"],
  "steps": {
    "sc-test": {"attempt_count": 2, "status": "fail"}
  }
}
""",
                encoding="utf-8",
            )
            summary = {
                "status": "fail",
                "steps": [
                    {
                        "name": "sc-test",
                        "status": "fail",
                        "rc": 1,
                        "cmd": ["py", "-3", "scripts/sc/test.py", "--task-id", "1"],
                        "log": str(log_path),
                    },
                ],
            }
            payload = build_repair_guide(summary, task_id="1", out_dir=out_dir)
            ids = {item["id"] for item in payload["recommendations"]}
            self.assertIn("pipeline-context-refresh", ids)

    def test_build_repair_guide_should_surface_agent_review_resume_when_pipeline_summary_is_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            summary = {
                "status": "ok",
                "steps": [
                    {"name": "sc-test", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/test.py"]},
                    {"name": "sc-acceptance-check", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/acceptance_check.py"]},
                    {"name": "sc-llm-review", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/llm_review.py"]},
                ],
            }
            payload = build_repair_guide(
                summary,
                task_id="1",
                out_dir=out_dir,
                marathon_state={
                    "status": "ok",
                    "agent_review": {
                        "review_verdict": "needs-fix",
                        "recommended_action": "resume",
                        "recommended_refresh_reasons": [],
                        "owner_steps": ["sc-llm-review"],
                        "categories": ["llm-review"],
                    },
                },
            )
            self.assertEqual("needs-fix", payload["status"])
            ids = {item["id"] for item in payload["recommendations"]}
            self.assertIn("agent-review-resume", ids)

    def test_build_repair_guide_should_surface_approved_fork_instead_of_generic_pipeline_fork(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            summary = {
                "status": "ok",
                "steps": [
                    {"name": "sc-test", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/test.py"]},
                    {"name": "sc-acceptance-check", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/acceptance_check.py"]},
                    {"name": "sc-llm-review", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/llm_review.py"]},
                ],
            }
            payload = build_repair_guide(
                summary,
                task_id="1",
                out_dir=out_dir,
                marathon_state={
                    "status": "ok",
                    "agent_review": {
                        "review_verdict": "block",
                        "recommended_action": "fork",
                        "recommended_refresh_reasons": ["agent_review_integrity_reset(summary-integrity)"],
                        "owner_steps": ["producer-pipeline"],
                        "categories": ["summary-integrity"],
                    },
                },
                approval_state={
                    "soft_gate": True,
                    "required_action": "fork",
                    "status": "approved",
                    "decision": "approved",
                    "reason": "Fork approved by operator",
                    "request_id": "run-1:fork",
                    "request_path": str(out_dir / "approval-request.json"),
                    "response_path": str(out_dir / "approval-response.json"),
                },
            )
            ids = [item["id"] for item in payload["recommendations"]]
            self.assertIn("approval-fork-approved", ids)
            self.assertNotIn("pipeline-fork", ids)
            self.assertEqual("approved", payload["approval"]["status"])
            markdown = render_repair_guide_markdown(payload)
            self.assertIn("approval-fork-approved", markdown)
            self.assertIn("status: approved", markdown)

    def test_build_repair_guide_should_surface_denied_fork_and_remove_fork_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            summary = {
                "status": "ok",
                "steps": [
                    {"name": "sc-test", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/test.py"]},
                    {"name": "sc-acceptance-check", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/acceptance_check.py"]},
                    {"name": "sc-llm-review", "status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/llm_review.py"]},
                ],
            }
            payload = build_repair_guide(
                summary,
                task_id="1",
                out_dir=out_dir,
                marathon_state={
                    "status": "ok",
                    "agent_review": {
                        "review_verdict": "block",
                        "recommended_action": "fork",
                        "recommended_refresh_reasons": ["agent_review_integrity_reset(summary-integrity)"],
                        "owner_steps": ["producer-pipeline"],
                        "categories": ["summary-integrity"],
                    },
                },
                approval_state={
                    "soft_gate": True,
                    "required_action": "fork",
                    "status": "denied",
                    "decision": "denied",
                    "reason": "Do not fork this run",
                    "request_id": "run-1:fork",
                    "request_path": str(out_dir / "approval-request.json"),
                    "response_path": str(out_dir / "approval-response.json"),
                },
            )
            ids = [item["id"] for item in payload["recommendations"]]
            self.assertIn("approval-fork-denied", ids)
            self.assertNotIn("pipeline-fork", ids)
            denied = next(item for item in payload["recommendations"] if item["id"] == "approval-fork-denied")
            joined = " ".join(denied["commands"])
            self.assertNotIn("--fork", joined)
            self.assertIn("--resume", joined)


if __name__ == "__main__":
    unittest.main()
