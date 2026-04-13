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
from _pipeline_session import PipelineSession  # noqa: E402
from _pipeline_events import append_run_event, build_run_event  # noqa: E402
from _pipeline_helpers import has_materialized_pipeline_steps, write_latest_index  # noqa: E402
from _pipeline_support import load_existing_summary  # noqa: E402
from _summary_schema import SummarySchemaError, validate_pipeline_summary  # noqa: E402


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
    def test_build_run_event_should_derive_taxonomy_fields(self) -> None:
        payload = build_run_event(
            event="step_finished",
            task_id="1",
            run_id="run-1",
            delivery_profile="fast-ship",
            security_profile="host-safe",
            step_name="sc-test",
            status="ok",
            details={"rc": 0},
        )

        self.assertEqual("run-1:turn-1", payload["turn_id"])
        self.assertEqual(1, payload["turn_seq"])
        self.assertEqual("step", payload["item_kind"])
        self.assertEqual("sc-test", payload["item_id"])
        self.assertEqual("step", payload["event_family"])

    def test_build_run_event_should_derive_approval_item_taxonomy(self) -> None:
        payload = build_run_event(
            event="approval_request_written",
            task_id="15",
            run_id="run-15",
            delivery_profile="fast-ship",
            security_profile="host-safe",
            status="pending",
            details={"action": "fork", "request_id": "run-15:fork"},
        )

        self.assertEqual("approval", payload["item_kind"])
        self.assertEqual("run-15:fork", payload["item_id"])
        self.assertEqual("approval", payload["event_family"])
        self.assertEqual("run-15:turn-1", payload["turn_id"])

    def test_pipeline_session_should_copy_active_task_recommendations_into_summary(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            out_dir.mkdir(parents=True, exist_ok=True)
            emitted_events: list[dict[str, object]] = []
            active_task_json = tmp_root / "task-1.active.json"
            active_task_md = tmp_root / "task-1.active.md"
            active_task_json.write_text(
                json.dumps(
                    {
                        "latest_summary_signals": {
                            "reason": "rerun_blocked:repeat_review_needs_fix",
                            "run_type": "full",
                            "reuse_mode": "deterministic-only-reuse",
                            "artifact_integrity_kind": "",
                            "diagnostics_keys": ["rerun_guard"],
                        },
                        "chapter6_hints": {
                            "next_action": "needs-fix-fast",
                            "can_skip_6_7": True,
                            "can_go_to_6_8": True,
                            "blocked_by": "rerun_guard",
                            "rerun_forbidden": True,
                            "rerun_override_flag": "--allow-full-rerun",
                        },
                        "recommended_action": "needs-fix-fast",
                        "recommended_action_why": "repeat family",
                        "candidate_commands": {
                            "needs_fix_fast": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 1 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                            "rerun": "py -3 scripts/sc/run_review_pipeline.py --task-id 1",
                        },
                        "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 1 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                        "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 1"],
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            active_task_md.write_text("# active\n", encoding="utf-8")

            session = PipelineSession(
                args=type("Args", (), {"dry_run": False, "fork": False})(),
                out_dir=out_dir,
                task_id="1",
                run_id=run_id,
                turn_id=f"{run_id}:turn-1",
                turn_seq=1,
                requested_run_id=run_id,
                delivery_profile="fast-ship",
                security_profile="host-safe",
                llm_review_context={},
                summary={
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
                    "started_at_utc": "2026-04-10T00:00:00+00:00",
                    "finished_at_utc": "2026-04-10T00:00:05+00:00",
                    "elapsed_sec": 5,
                    "run_type": "full",
                    "reason": "step_failed:sc-test",
                    "reuse_mode": "none",
                },
                marathon_state={"steps": {}, "diagnostics": {}, "agent_review": {}},
                agent_review_mode="off",
                schema_error_log=out_dir / "summary-schema-validation-error.log",
                apply_runtime_policy=lambda state: state,
                apply_agent_review_signal=lambda state, _review: state,
                validate_pipeline_summary=validate_pipeline_summary,
                summary_schema_error=SummarySchemaError,
                write_harness_capabilities=lambda **_: None,
                write_json=lambda path, payload: path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"),
                write_text=lambda path, content: path.write_text(content, encoding="utf-8"),
                save_marathon_state=lambda _out_dir, _state: None,
                build_repair_guide=lambda *_args, **_kwargs: {
                    "schema_version": "1.0.0",
                    "status": "needs-fix",
                    "task_id": "1",
                    "summary_status": "fail",
                    "failed_step": "sc-test",
                    "approval": {},
                    "generated_from": {},
                    "recommendations": [],
                },
                sync_soft_approval_sidecars=lambda **_: {"events": []},
                build_execution_context=lambda **kwargs: {
                    "schema_version": "1.0.0",
                    "recommended_action": str((kwargs.get("summary") or {}).get("recommended_action") or ""),
                    "recommended_command": str((kwargs.get("summary") or {}).get("recommended_command") or ""),
                    "forbidden_commands": list((kwargs.get("summary") or {}).get("forbidden_commands") or []),
                    "chapter6_hints": dict((kwargs.get("summary") or {}).get("chapter6_hints") or {}),
                },
                render_repair_guide_markdown=lambda _payload: "# repair\n",
                append_run_event=lambda **kwargs: emitted_events.append(dict(kwargs)),
                write_latest_index=lambda **_: None,
                write_active_task_sidecar=lambda **_: (active_task_json, active_task_md),
                record_step_result=lambda state, _step: state,
                upsert_step=lambda _summary, _step: None,
                append_step_event=lambda **_: None,
                run_step=lambda **_: {},
                can_retry_failed_step=lambda *_: False,
                step_is_already_complete=lambda *_: False,
                wall_time_exceeded=lambda *_: False,
                mark_wall_time_exceeded=lambda state: state,
                cap_step_timeout=lambda timeout, _state: timeout,
                run_agent_review_post_hook=lambda **_: (0, {}),
                refresh_summary_meta=lambda _summary: None,
            )

            persisted = session.persist()

            self.assertTrue(persisted)
            summary_payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            execution_context_payload = json.loads((out_dir / "execution-context.json").read_text(encoding="utf-8"))
            self.assertEqual("needs-fix-fast", summary_payload["recommended_action"])
            self.assertEqual(
                "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 1 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                summary_payload["recommended_command"],
            )
            self.assertEqual("step-failed", summary_payload["failure_kind"])
            self.assertEqual(
                ["py -3 scripts/sc/run_review_pipeline.py --task-id 1"],
                summary_payload["forbidden_commands"],
            )
            self.assertEqual("needs-fix-fast", summary_payload["chapter6_hints"]["next_action"])
            self.assertEqual("needs-fix-fast", execution_context_payload["recommended_action"])
            self.assertEqual("step-failed", execution_context_payload["failure_kind"])
            self.assertEqual(
                "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 1 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                execution_context_payload["recommended_command"],
            )
            self.assertEqual(
                ["py -3 scripts/sc/run_review_pipeline.py --task-id 1"],
                execution_context_payload["forbidden_commands"],
            )
            self.assertEqual("needs-fix-fast", execution_context_payload["chapter6_hints"]["next_action"])
            event_names = [str(item.get("event") or "") for item in emitted_events]
            self.assertIn("sidecar_harness_capabilities_synced", event_names)
            self.assertIn("sidecar_execution_context_synced", event_names)
            self.assertIn("sidecar_repair_guide_synced", event_names)
            self.assertIn("sidecar_latest_index_synced", event_names)
            self.assertIn("sidecar_active_task_synced", event_names)

    def test_pipeline_session_finish_should_emit_reviewer_event(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / f"sc-review-pipeline-task-1-{run_id}"
            out_dir.mkdir(parents=True, exist_ok=True)
            emitted_events: list[dict[str, object]] = []

            session = PipelineSession(
                args=type("Args", (), {"dry_run": False, "fork": False, "skip_agent_review": False})(),
                out_dir=out_dir,
                task_id="1",
                run_id=run_id,
                turn_id=f"{run_id}:turn-1",
                turn_seq=1,
                requested_run_id=run_id,
                delivery_profile="fast-ship",
                security_profile="host-safe",
                llm_review_context={},
                summary={
                    "cmd": "sc-review-pipeline",
                    "task_id": "1",
                    "requested_run_id": run_id,
                    "run_id": run_id,
                    "allow_overwrite": False,
                    "force_new_run_id": False,
                    "status": "ok",
                    "steps": [],
                    "started_at_utc": "2026-04-10T00:00:00+00:00",
                    "finished_at_utc": "",
                    "elapsed_sec": 0,
                    "run_type": "full",
                    "reason": "pipeline_clean",
                    "reuse_mode": "none",
                },
                marathon_state={"steps": {}, "diagnostics": {}, "agent_review": {}},
                agent_review_mode="warn",
                schema_error_log=out_dir / "summary-schema-validation-error.log",
                apply_runtime_policy=lambda state: state,
                apply_agent_review_signal=lambda state, _review: state,
                validate_pipeline_summary=validate_pipeline_summary,
                summary_schema_error=SummarySchemaError,
                write_harness_capabilities=lambda **_: None,
                write_json=lambda path, payload: path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"),
                write_text=lambda path, content: path.write_text(content, encoding="utf-8"),
                save_marathon_state=lambda _out_dir, _state: None,
                build_repair_guide=lambda *_args, **_kwargs: {
                    "schema_version": "1.0.0",
                    "status": "not-needed",
                    "task_id": "1",
                    "summary_status": "ok",
                    "failed_step": "",
                    "approval": {},
                    "generated_from": {},
                    "recommendations": [],
                },
                sync_soft_approval_sidecars=lambda **_: {"events": []},
                build_execution_context=lambda **kwargs: {
                    "schema_version": "1.0.0",
                    "recommended_action": str((kwargs.get("summary") or {}).get("recommended_action") or ""),
                    "recommended_command": str((kwargs.get("summary") or {}).get("recommended_command") or ""),
                    "forbidden_commands": list((kwargs.get("summary") or {}).get("forbidden_commands") or []),
                    "chapter6_hints": dict((kwargs.get("summary") or {}).get("chapter6_hints") or {}),
                },
                render_repair_guide_markdown=lambda _payload: "# repair\n",
                append_run_event=lambda **kwargs: emitted_events.append(dict(kwargs)),
                write_latest_index=lambda **_: None,
                write_active_task_sidecar=lambda **_: (),
                record_step_result=lambda state, _step: state,
                upsert_step=lambda _summary, _step: None,
                append_step_event=lambda **_: None,
                run_step=lambda **_: {},
                can_retry_failed_step=lambda *_: False,
                step_is_already_complete=lambda *_: False,
                wall_time_exceeded=lambda *_: False,
                mark_wall_time_exceeded=lambda state: state,
                cap_step_timeout=lambda timeout, _state: timeout,
                run_agent_review_post_hook=lambda **_: (
                    0,
                    {
                        "steps": {},
                        "diagnostics": {},
                        "agent_review": {
                            "review_verdict": "needs-fix",
                            "recommended_action": "fork",
                        },
                    },
                ),
                refresh_summary_meta=lambda _summary: None,
            )

            rc = session.finish()

            self.assertEqual(0, rc)
            reviewer_event = next(item for item in emitted_events if item.get("event") == "reviewer_completed")
            self.assertEqual("reviewer", reviewer_event["item_kind"])
            self.assertEqual("artifact-reviewer", reviewer_event["item_id"])
            self.assertEqual("ok", reviewer_event["status"])
            self.assertEqual("fork", reviewer_event["details"]["recommended_action"])

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
            self.assertIn("run_completed", {item["event"] for item in events})
            self.assertIn("step_skipped", {item["event"] for item in events})
            self.assertIn("step_planned", {item["event"] for item in events})
            self.assertEqual("run", events[0]["item_kind"])
            self.assertEqual(f"{run_id}:turn-1", events[0]["turn_id"])
            self.assertEqual(1, events[0]["turn_seq"])
            planned = next(item for item in events if item["event"] == "step_planned")
            self.assertEqual("step", planned["item_kind"])
            self.assertTrue(str(planned["item_id"]).strip())
            self.assertEqual("step", planned["event_family"])

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
            self.assertEqual("artifact-incomplete", latest["failure_kind"])

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
            self.assertEqual("ok", latest["failure_kind"])

    def test_write_latest_index_should_emit_review_needs_fix_failure_kind(self) -> None:
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
                                "status": "ok",
                                "log": str(out_dir / "sc-test.log"),
                            }
                        ],
                        "started_at_utc": "2026-04-08T00:00:00+00:00",
                        "finished_at_utc": "2026-04-08T00:00:05+00:00",
                        "elapsed_sec": 5,
                        "run_type": "deterministic-only",
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
                        "date": "2026-04-08",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "status": "ok",
                        "run_type": "deterministic-only",
                        "reason": "pipeline_clean",
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
            (out_dir / "repair-guide.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "status": "needs-fix",
                        "task_id": "1",
                        "summary_status": "ok",
                        "failed_step": "",
                        "approval": {},
                        "recommendations": [{"id": "fix", "title": "Fix", "why": "Needs follow-up"}],
                        "generated_from": {},
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
            self.assertEqual("ok", latest["status"])
            self.assertEqual("review-needs-fix", latest["failure_kind"])

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
            task_id="1",
            run_id="run-1",
            action="fork",
            request_id="req-1",
            decision="approved",
            reviewer="human",
            reason="fork is acceptable for recovery",
        )

        validate_approval_request_payload(request)
        validate_approval_response_payload(response)

        self.assertEqual("pending", request["status"])
        self.assertEqual("pause", request["recommended_action"])
        self.assertEqual(["inspect", "pause"], request["allowed_actions"])
        self.assertEqual(["fork", "resume", "rerun"], request["blocked_actions"])
        self.assertEqual("approved", response["decision"])
        self.assertEqual("fork", response["action"])
        self.assertEqual("1", response["task_id"])
        self.assertEqual("run-1", response["run_id"])
        self.assertEqual("fork", response["recommended_action"])
        self.assertEqual(["fork", "inspect"], response["allowed_actions"])
        self.assertEqual(["resume", "rerun"], response["blocked_actions"])

    def test_build_approval_request_should_reject_unknown_action(self) -> None:
        from _approval_contract import build_approval_request

        with self.assertRaises(Exception):
            build_approval_request(
                task_id="1",
                run_id="run-1",
                action="resume",
                reason="unsupported action should fail validation",
                requested_files=[],
                requested_commands=[],
                request_id="req-1",
            )


if __name__ == "__main__":
    unittest.main()
