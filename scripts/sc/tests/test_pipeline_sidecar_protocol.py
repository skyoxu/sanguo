#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

import run_review_pipeline as run_review_pipeline_module  # noqa: E402


def _stable_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in (
        "DELIVERY_PROFILE",
        "SECURITY_PROFILE",
        "SC_PIPELINE_RUN_ID",
        "SC_TEST_RUN_ID",
        "SC_ACCEPTANCE_RUN_ID",
    ):
        env.pop(key, None)
    return env


class PipelineSidecarProtocolTests(unittest.TestCase):
    def test_dry_run_should_write_run_events_and_capabilities(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--dry-run",
                "--skip-test",
                "--skip-agent-review",
            ]
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path):
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            self.assertTrue((out_dir / "run-events.jsonl").exists())
            self.assertTrue((out_dir / "harness-capabilities.json").exists())

            events = [
                json.loads(line)
                for line in (out_dir / "run-events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertGreaterEqual(len(events), 4)
            self.assertEqual("run_started", events[0]["event"])
            self.assertEqual("run_completed", events[-1]["event"])
            self.assertIn("step_skipped", {item["event"] for item in events})
            self.assertIn("step_planned", {item["event"] for item in events})

            capabilities = json.loads((out_dir / "harness-capabilities.json").read_text(encoding="utf-8"))
            self.assertEqual("1.0.0", capabilities["protocol_version"])
            self.assertEqual("fast-ship", capabilities["delivery_profile"])
            self.assertEqual("host-safe", capabilities["security_profile"])
            self.assertIn("run-events.jsonl", capabilities["supported_sidecars"])
            self.assertIn("approval-request.json", capabilities["supported_sidecars"])
            self.assertIn("resume", capabilities["supported_recovery_actions"])
            self.assertTrue(capabilities["approval_contract_supported"])
            self.assertFalse((out_dir / "approval-request.json").exists())
            self.assertFalse((out_dir / "approval-response.json").exists())

    def test_abort_should_append_run_aborted_event(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "ok",
                        "steps": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "run_id": run_id,
                        "status": "running",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--abort",
            ]
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path):
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            events = [
                json.loads(line)
                for line in (out_dir / "run-events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual("run_aborted", events[-1]["event"])
            self.assertEqual("aborted", events[-1]["status"])


class ApprovalContractTests(unittest.TestCase):
    def test_write_and_validate_approval_contract_files(self) -> None:
        from _approval_contract import (
            build_approval_request,
            build_approval_response,
            validate_approval_request_payload,
            validate_approval_response_payload,
        )

        request = build_approval_request(
            task_id="1",
            run_id="run-1",
            action="fork",
            reason="cross-step integrity issue requires isolated continuation",
            requested_files=["scripts/sc/run_review_pipeline.py"],
            requested_commands=["py -3 scripts/sc/run_review_pipeline.py --task-id 1 --fork"],
            request_id="req-1",
        )
        response = build_approval_response(
            request_id="req-1",
            decision="approved",
            reviewer="human",
            reason="fork is acceptable for recovery",
        )

        validate_approval_request_payload(request)
        validate_approval_response_payload(response)

        self.assertEqual("pending", request["status"])
        self.assertEqual("approved", response["decision"])


if __name__ == "__main__":
    unittest.main()
