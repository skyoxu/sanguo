#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
import json


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _pipeline_approval as pipeline_approval  # noqa: E402
import _repair_approval as repair_approval  # noqa: E402


class PipelineApprovalTests(unittest.TestCase):
    def test_protocol_examples_should_resolve_to_approved_fork_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-10-run1"
            out_dir.mkdir(parents=True, exist_ok=True)

            request_example = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-approval-request.example.json"
            response_example = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-approval-response.example.json"

            (out_dir / "approval-request.json").write_text(
                json.dumps(json.loads(request_example.read_text(encoding="utf-8")), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (out_dir / "approval-response.json").write_text(
                json.dumps(json.loads(response_example.read_text(encoding="utf-8")), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            approval = repair_approval.resolve_approval_state(out_dir=out_dir)

            self.assertTrue(approval["soft_gate"])
            self.assertEqual("fork", approval["required_action"])
            self.assertEqual("approved", approval["status"])
            self.assertEqual("approved", approval["decision"])
            self.assertEqual("fork", approval["recommended_action"])
            self.assertEqual(["fork", "inspect"], approval["allowed_actions"])
            self.assertEqual(["resume", "rerun"], approval["blocked_actions"])
            self.assertEqual("apr-20260321-001", approval["request_id"])

    def test_resolve_approval_state_should_reject_inconsistent_request_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run1"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "approval-request.json").write_text(
                (
                    "{\n"
                    '  "schema_version": "1.0.0",\n'
                    '  "request_id": "run1:fork",\n'
                    '  "task_id": "15",\n'
                    '  "run_id": "run1",\n'
                    '  "action": "fork",\n'
                    '  "reason": "Fork was requested.",\n'
                    '  "requested_files": [],\n'
                    '  "requested_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork"],\n'
                    '  "status": "pending",\n'
                    '  "recommended_action": "inspect",\n'
                    '  "allowed_actions": ["inspect"],\n'
                    '  "blocked_actions": ["fork", "resume", "rerun"]\n'
                    "}\n"
                ),
                encoding="utf-8",
            )

            approval = repair_approval.resolve_approval_state(out_dir=out_dir)

            self.assertEqual("invalid", approval["status"])
            self.assertEqual("inspect", approval["recommended_action"])
            self.assertIn("request contract does not match", approval["reason"])

    def test_resolve_approval_state_should_reject_inconsistent_response_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run1"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "approval-request.json").write_text(
                (
                    "{\n"
                    '  "schema_version": "1.0.0",\n'
                    '  "request_id": "run1:fork",\n'
                    '  "task_id": "15",\n'
                    '  "run_id": "run1",\n'
                    '  "action": "fork",\n'
                    '  "reason": "Fork was requested.",\n'
                    '  "requested_files": [],\n'
                    '  "requested_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork"],\n'
                    '  "status": "pending"\n'
                    "}\n"
                ),
                encoding="utf-8",
            )
            (out_dir / "approval-response.json").write_text(
                (
                    "{\n"
                    '  "schema_version": "1.0.0",\n'
                    '  "task_id": "15",\n'
                    '  "run_id": "run1",\n'
                    '  "action": "fork",\n'
                    '  "request_id": "run1:fork",\n'
                    '  "decision": "approved",\n'
                    '  "reviewer": "human",\n'
                    '  "reason": "Approved but with the wrong contract.",\n'
                    '  "recommended_action": "resume",\n'
                    '  "allowed_actions": ["resume", "inspect"],\n'
                    '  "blocked_actions": ["fork"]\n'
                    "}\n"
                ),
                encoding="utf-8",
            )

            approval = repair_approval.resolve_approval_state(out_dir=out_dir)

            self.assertEqual("invalid", approval["status"])
            self.assertEqual("inspect", approval["recommended_action"])
            self.assertIn("does not match", approval["reason"])

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

    def test_resolve_approval_state_should_mark_mismatched_when_response_request_id_differs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run1"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "approval-request.json").write_text(
                (
                    "{\n"
                    '  "schema_version": "1.0.0",\n'
                    '  "request_id": "run1:fork",\n'
                    '  "task_id": "15",\n'
                    '  "run_id": "run1",\n'
                    '  "action": "fork",\n'
                    '  "reason": "Fork was requested.",\n'
                    '  "requested_files": [],\n'
                    '  "requested_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork"],\n'
                    '  "status": "pending"\n'
                    "}\n"
                ),
                encoding="utf-8",
            )
            (out_dir / "approval-response.json").write_text(
                (
                    "{\n"
                    '  "schema_version": "1.0.0",\n'
                    '  "request_id": "other-run:fork",\n'
                    '  "decision": "approved",\n'
                    '  "reviewer": "human",\n'
                    '  "reason": "Approved the wrong request."\n'
                    "}\n"
                ),
                encoding="utf-8",
            )

            approval = repair_approval.resolve_approval_state(out_dir=out_dir)

            self.assertEqual("fork", approval["required_action"])
            self.assertEqual("mismatched", approval["status"])
            self.assertEqual("approved", approval["decision"])
            self.assertEqual("inspect", approval["recommended_action"])
            self.assertEqual(["inspect"], approval["allowed_actions"])
            self.assertIn("does not match", approval["reason"])

    def test_apply_approval_to_recommendations_should_strip_fork_when_response_is_mismatched(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run1"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "approval-request.json").write_text(
                (
                    "{\n"
                    '  "schema_version": "1.0.0",\n'
                    '  "request_id": "run1:fork",\n'
                    '  "task_id": "15",\n'
                    '  "run_id": "run1",\n'
                    '  "action": "fork",\n'
                    '  "reason": "Fork was requested.",\n'
                    '  "requested_files": [],\n'
                    '  "requested_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork"],\n'
                    '  "status": "pending"\n'
                    "}\n"
                ),
                encoding="utf-8",
            )
            (out_dir / "approval-response.json").write_text(
                (
                    "{\n"
                    '  "schema_version": "1.0.0",\n'
                    '  "request_id": "other-run:fork",\n'
                    '  "decision": "approved",\n'
                    '  "reviewer": "human",\n'
                    '  "reason": "Approved the wrong request."\n'
                    "}\n"
                ),
                encoding="utf-8",
            )

            recommendations, approval = repair_approval.apply_approval_to_recommendations(
                task_id="15",
                out_dir=out_dir,
                recommendations=[
                    {
                        "id": "pipeline-fork",
                        "title": "Fork the pipeline",
                        "why": "Use an isolated run.",
                        "actions": [],
                        "commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork"],
                        "files": [],
                    }
                ],
            )

            self.assertEqual("mismatched", approval["status"])
            self.assertEqual("approval-fork-invalid", recommendations[0]["id"])
            self.assertEqual([], recommendations[0]["commands"])

    def test_resolve_approval_state_should_mark_invalid_when_response_action_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run1"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "approval-request.json").write_text(
                (
                    "{\n"
                    '  "schema_version": "1.0.0",\n'
                    '  "request_id": "run1:fork",\n'
                    '  "task_id": "15",\n'
                    '  "run_id": "run1",\n'
                    '  "action": "fork",\n'
                    '  "reason": "Fork was requested.",\n'
                    '  "requested_files": [],\n'
                    '  "requested_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork"],\n'
                    '  "status": "pending"\n'
                    "}\n"
                ),
                encoding="utf-8",
            )
            (out_dir / "approval-response.json").write_text(
                (
                    "{\n"
                    '  "schema_version": "1.0.0",\n'
                    '  "task_id": "15",\n'
                    '  "run_id": "run1",\n'
                    '  "action": "resume",\n'
                    '  "request_id": "run1:fork",\n'
                    '  "decision": "approved",\n'
                    '  "reviewer": "human",\n'
                    '  "reason": "Wrong action in response."\n'
                    "}\n"
                ),
                encoding="utf-8",
            )

            approval = repair_approval.resolve_approval_state(out_dir=out_dir)

            self.assertEqual("invalid", approval["status"])
            self.assertEqual("inspect", approval["recommended_action"])
            self.assertIn("action", approval["reason"].lower())

    def test_resolve_approval_state_should_publish_protocol_actions_for_pending_request(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run1"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "approval-request.json").write_text(
                (
                    "{\n"
                    '  "schema_version": "1.0.0",\n'
                    '  "request_id": "run1:fork",\n'
                    '  "task_id": "15",\n'
                    '  "run_id": "run1",\n'
                    '  "action": "fork",\n'
                    '  "reason": "Fork was requested.",\n'
                    '  "requested_files": [],\n'
                    '  "requested_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork"],\n'
                    '  "status": "pending"\n'
                    "}\n"
                ),
                encoding="utf-8",
            )

            approval = repair_approval.resolve_approval_state(out_dir=out_dir)

            self.assertEqual("pending", approval["status"])
            self.assertEqual("pause", approval["recommended_action"])
            self.assertEqual(["inspect", "pause"], approval["allowed_actions"])
            self.assertEqual(["fork", "resume", "rerun"], approval["blocked_actions"])


if __name__ == "__main__":
    unittest.main()
