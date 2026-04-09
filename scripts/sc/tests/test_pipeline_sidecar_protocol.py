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
from _pipeline_events import append_run_event  # noqa: E402
from _pipeline_helpers import has_materialized_pipeline_steps, write_latest_index  # noqa: E402
from _pipeline_support import load_existing_summary  # noqa: E402


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
                "--delivery-profile",
                "fast-ship",
                "--security-profile",
                "host-safe",
                "--reselect-profile",
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
                        "elapsed_sec": 0,
                        "reason": "pipeline_clean",
                        "reuse_mode": "none",
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

    def test_write_latest_index_should_backfill_reason_and_reuse_mode_from_legacy_summary(self) -> None:
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
                        "status": "fail",
                        "steps": [
                            {
                                "name": "sc-test",
                                "cmd": ["py", "-3", "scripts/sc/test.py"],
                                "rc": 1,
                                "status": "fail",
                                "log": str(out_dir / "sc-test.log"),
                            }
                        ],
                        "elapsed_sec": 3,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "cmd": "sc-review-pipeline",
                        "date": "2026-04-07",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "status": "fail",
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "failed_step": "sc-test",
                        "paths": {},
                        "git": {},
                        "recovery": {},
                        "marathon": {},
                        "agent_review": {},
                        "llm_review": {},
                        "approval": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            write_latest_index(
                task_id="1",
                run_id=run_id,
                out_dir=out_dir,
                status="fail",
                latest_index_path_fn=lambda _task_id: latest_path,
            )

            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            self.assertEqual("step_failed:sc-test", latest["reason"])
            self.assertEqual("none", latest["reuse_mode"])

    def test_write_latest_index_should_not_publish_ok_before_run_completed(self) -> None:
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
                        "elapsed_sec": 1,
                        "reason": "pipeline_clean",
                        "reuse_mode": "none",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "cmd": "sc-review-pipeline",
                        "date": "2026-04-07",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "status": "ok",
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "failed_step": "",
                        "paths": {},
                        "git": {},
                        "recovery": {},
                        "marathon": {},
                        "agent_review": {},
                        "llm_review": {},
                        "approval": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            write_latest_index(
                task_id="1",
                run_id=run_id,
                out_dir=out_dir,
                status="ok",
                latest_index_path_fn=lambda _task_id: latest_path,
            )

            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            self.assertEqual("running", latest["status"])
            self.assertEqual("in_progress", latest["reason"])

            append_run_event(
                out_dir=out_dir,
                event="run_completed",
                task_id="1",
                run_id=run_id,
                delivery_profile="fast-ship",
                security_profile="host-safe",
                status="ok",
                details={"agent_review_rc": 0},
            )
            write_latest_index(
                task_id="1",
                run_id=run_id,
                out_dir=out_dir,
                status="ok",
                latest_index_path_fn=lambda _task_id: latest_path,
            )

            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            self.assertEqual("ok", latest["status"])
            self.assertEqual("pipeline_clean", latest["reason"])

    def test_write_latest_index_should_mark_planned_only_terminal_run_as_incomplete(self) -> None:
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
                        "steps": [
                            {
                                "name": "sc-test",
                                "cmd": ["py", "-3", "scripts/sc/test.py"],
                                "rc": 0,
                                "status": "planned",
                            },
                            {
                                "name": "sc-acceptance-check",
                                "cmd": ["py", "-3", "scripts/sc/acceptance_check.py"],
                                "rc": 0,
                                "status": "planned",
                            },
                        ],
                        "started_at_utc": "2026-04-08T00:00:00+00:00",
                        "finished_at_utc": "2026-04-08T00:00:05+00:00",
                        "elapsed_sec": 5,
                        "run_type": "planned-only",
                        "reason": "planned_only_incomplete",
                        "reuse_mode": "none",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "cmd": "sc-review-pipeline",
                        "date": "2026-04-08",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "status": "ok",
                        "run_type": "planned-only",
                        "reason": "planned_only_incomplete",
                        "reuse_mode": "none",
                        "started_at_utc": "2026-04-08T00:00:00+00:00",
                        "finished_at_utc": "2026-04-08T00:00:05+00:00",
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "failed_step": "",
                        "paths": {},
                        "git": {},
                        "recovery": {},
                        "marathon": {},
                        "agent_review": {},
                        "llm_review": {},
                        "approval": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            append_run_event(
                out_dir=out_dir,
                event="run_completed",
                task_id="1",
                run_id=run_id,
                delivery_profile="fast-ship",
                security_profile="host-safe",
                status="ok",
                details={"agent_review_rc": 0},
            )

            write_latest_index(
                task_id="1",
                run_id=run_id,
                out_dir=out_dir,
                status="ok",
                latest_index_path_fn=lambda _task_id: latest_path,
            )

            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            self.assertEqual("fail", latest["status"])
            self.assertEqual("planned_only_incomplete", latest["reason"])
            self.assertEqual("planned-only", latest["run_type"])

    def test_write_latest_index_should_preserve_existing_real_latest_when_new_run_is_planned_only(self) -> None:
        existing_run_id = "existing-real-run"
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            existing_out_dir = tmp_root / f"sc-review-pipeline-task-1-{existing_run_id}"
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            existing_out_dir.mkdir(parents=True, exist_ok=True)
            out_dir.mkdir(parents=True, exist_ok=True)

            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "run_id": existing_run_id,
                        "status": "ok",
                        "reason": "pipeline_clean",
                        "run_type": "full",
                        "latest_out_dir": str(existing_out_dir),
                        "summary_path": str(existing_out_dir / "summary.json"),
                        "execution_context_path": str(existing_out_dir / "execution-context.json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

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
                        "steps": [
                            {"name": "sc-test", "status": "planned"},
                            {"name": "sc-acceptance-check", "status": "planned"},
                            {"name": "sc-llm-review", "status": "planned"},
                        ],
                        "started_at_utc": "2026-04-08T00:00:00+00:00",
                        "finished_at_utc": "2026-04-08T00:00:05+00:00",
                        "elapsed_sec": 5,
                        "run_type": "planned-only",
                        "reason": "planned_only_incomplete",
                        "reuse_mode": "none",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "cmd": "sc-review-pipeline",
                        "date": "2026-04-08",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "status": "ok",
                        "run_type": "planned-only",
                        "reason": "planned_only_incomplete",
                        "reuse_mode": "none",
                        "started_at_utc": "2026-04-08T00:00:00+00:00",
                        "finished_at_utc": "2026-04-08T00:00:05+00:00",
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "failed_step": "",
                        "paths": {},
                        "git": {},
                        "recovery": {},
                        "marathon": {},
                        "agent_review": {},
                        "llm_review": {},
                        "approval": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            append_run_event(
                out_dir=out_dir,
                event="run_completed",
                task_id="1",
                run_id=run_id,
                delivery_profile="fast-ship",
                security_profile="host-safe",
                status="ok",
                details={"agent_review_rc": 0},
            )

            write_latest_index(
                task_id="1",
                run_id=run_id,
                out_dir=out_dir,
                status="ok",
                latest_index_path_fn=lambda _task_id: latest_path,
            )

            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            self.assertEqual(existing_run_id, latest["run_id"])
            self.assertEqual(str(existing_out_dir), latest["latest_out_dir"])
            self.assertEqual("full", latest["run_type"])

    def test_write_latest_index_should_replace_existing_real_latest_when_new_run_is_preflight_only_failure(self) -> None:
        existing_run_id = "existing-real-run"
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            existing_out_dir = tmp_root / f"sc-review-pipeline-task-1-{existing_run_id}"
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            existing_out_dir.mkdir(parents=True, exist_ok=True)
            out_dir.mkdir(parents=True, exist_ok=True)

            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "run_id": existing_run_id,
                        "status": "ok",
                        "reason": "pipeline_clean",
                        "run_type": "full",
                        "latest_out_dir": str(existing_out_dir),
                        "summary_path": str(existing_out_dir / "summary.json"),
                        "execution_context_path": str(existing_out_dir / "execution-context.json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "fail",
                        "steps": [
                            {
                                "name": "sc-build-tdd-refactor-preflight",
                                "status": "fail",
                                "rc": 1,
                            }
                        ],
                        "started_at_utc": "2026-04-08T00:00:00+00:00",
                        "finished_at_utc": "2026-04-08T00:00:05+00:00",
                        "elapsed_sec": 5,
                        "run_type": "preflight-only",
                        "reason": "step_failed:sc-build-tdd-refactor-preflight",
                        "reuse_mode": "none",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "cmd": "sc-review-pipeline",
                        "date": "2026-04-08",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "status": "fail",
                        "run_type": "preflight-only",
                        "reason": "step_failed:sc-build-tdd-refactor-preflight",
                        "reuse_mode": "none",
                        "started_at_utc": "2026-04-08T00:00:00+00:00",
                        "finished_at_utc": "2026-04-08T00:00:05+00:00",
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "failed_step": "sc-build-tdd-refactor-preflight",
                        "paths": {},
                        "git": {},
                        "recovery": {},
                        "marathon": {},
                        "agent_review": {},
                        "llm_review": {},
                        "approval": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            append_run_event(
                out_dir=out_dir,
                event="run_completed",
                task_id="1",
                run_id=run_id,
                delivery_profile="fast-ship",
                security_profile="host-safe",
                status="fail",
            )

            write_latest_index(
                task_id="1",
                run_id=run_id,
                out_dir=out_dir,
                status="fail",
                latest_index_path_fn=lambda _task_id: latest_path,
            )

            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            self.assertEqual(run_id, latest["run_id"])
            self.assertEqual(str(out_dir), latest["latest_out_dir"])
            self.assertEqual("preflight-only", latest["run_type"])
            self.assertEqual("step_failed:sc-build-tdd-refactor-preflight", latest["reason"])

    def test_has_materialized_pipeline_steps_should_reject_planned_only_summary(self) -> None:
        summary = {
            "cmd": "sc-review-pipeline",
            "steps": [
                {"name": "sc-test", "status": "planned"},
                {"name": "sc-acceptance-check", "status": "planned"},
            ],
        }
        self.assertFalse(has_materialized_pipeline_steps(summary))

    def test_load_existing_summary_should_infer_legacy_planned_only_reason(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "status": "ok",
                        "steps": [
                            {"name": "sc-test", "status": "planned"},
                            {"name": "sc-acceptance-check", "status": "planned"},
                            {"name": "sc-llm-review", "status": "planned"},
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            append_run_event(
                out_dir=out_dir,
                event="run_completed",
                task_id="1",
                run_id=run_id,
                delivery_profile="fast-ship",
                security_profile="host-safe",
                status="ok",
            )

            payload = load_existing_summary(out_dir)

            self.assertIsNotNone(payload)
            self.assertEqual("planned-only", payload["run_type"])
            self.assertEqual("planned_only_incomplete", payload["reason"])
            self.assertEqual("none", payload["reuse_mode"])


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
