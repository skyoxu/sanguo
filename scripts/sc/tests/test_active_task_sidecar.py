#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _active_task_sidecar as active_task_sidecar  # noqa: E402
from _sidecar_schema import validate_active_task_payload  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ActiveTaskSidecarTests(unittest.TestCase):
    def _build_bundle(
        self,
        *,
        root: Path,
        task_id: str = "14",
        run_id: str = "",
        summary_payload: dict,
        execution_context_payload: dict,
        repair_guide_payload: dict | None = None,
        extra_files: dict[str, dict] | None = None,
        include_run_completed: bool = True,
    ) -> tuple[Path, Path]:
        run_id = str(run_id or summary_payload.get("run_id") or execution_context_payload.get("run_id") or "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        out_dir = root / "logs" / "ci" / "2026-04-07" / f"sc-review-pipeline-task-{task_id}-{run_id}"
        latest_path = root / "logs" / "ci" / "2026-04-07" / f"sc-review-pipeline-task-{task_id}" / "latest.json"
        _write_json(out_dir / "summary.json", summary_payload)
        _write_json(out_dir / "execution-context.json", execution_context_payload)
        _write_json(
            out_dir / "repair-guide.json",
            repair_guide_payload
            or {
                "schema_version": "1.0.0",
                "status": "needs-fix" if summary_payload.get("status") == "fail" else "not-needed",
                "task_id": task_id,
                "summary_status": str(summary_payload.get("status") or ""),
                "failed_step": "",
                "approval": {},
                "generated_from": {},
                "recommendations": [],
            },
        )
        (out_dir / "repair-guide.md").write_text("# repair\n", encoding="utf-8")
        _write_json(
            latest_path,
            {
                "task_id": task_id,
                "run_id": run_id,
                "status": str(summary_payload.get("status") or ""),
                "date": "2026-04-07",
                "latest_out_dir": str(out_dir),
                "summary_path": str(out_dir / "summary.json"),
                "execution_context_path": str(out_dir / "execution-context.json"),
                "repair_guide_json_path": str(out_dir / "repair-guide.json"),
                "repair_guide_md_path": str(out_dir / "repair-guide.md"),
                "marathon_state_path": str(out_dir / "marathon-state.json"),
                "run_events_path": str(out_dir / "run-events.jsonl"),
                "harness_capabilities_path": str(out_dir / "harness-capabilities.json"),
            },
        )
        run_events_path = out_dir / "run-events.jsonl"
        run_events_path.parent.mkdir(parents=True, exist_ok=True)
        events = [
            {
                "schema_version": "1.0.0",
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": "run_started",
                "event_family": "run",
                "task_id": task_id,
                "run_id": run_id,
                "turn_id": f"{run_id}:turn-1",
                "turn_seq": 1,
                "delivery_profile": str(execution_context_payload.get("delivery_profile") or "fast-ship"),
                "security_profile": str(execution_context_payload.get("security_profile") or "host-safe"),
                "item_kind": "run",
                "item_id": run_id,
                "step_name": None,
                "status": "ok",
                "details": {},
            }
        ]
        if include_run_completed:
            events.append(
                {
                    "schema_version": "1.0.0",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "event": "run_completed",
                    "event_family": "run",
                    "task_id": task_id,
                    "run_id": run_id,
                    "turn_id": f"{run_id}:turn-1",
                    "turn_seq": 1,
                    "delivery_profile": str(execution_context_payload.get("delivery_profile") or "fast-ship"),
                    "security_profile": str(execution_context_payload.get("security_profile") or "host-safe"),
                    "item_kind": "run",
                    "item_id": run_id,
                    "step_name": None,
                    "status": str(summary_payload.get("status") or ""),
                    "details": {},
                }
            )
        run_events_path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in events) + "\n", encoding="utf-8")
        for relative_path, payload in (extra_files or {}).items():
            _write_json(out_dir / relative_path, payload)
        return out_dir, latest_path

    def test_build_active_task_payload_should_validate_against_schema(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "abababababababababababababababab"
            out_dir, latest_path = self._build_bundle(
                root=root,
                task_id="15",
                run_id=run_id,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": run_id,
                    "status": "fail",
                    "reason": "rerun_blocked:repeat_review_needs_fix",
                    "reuse_mode": "deterministic-only-reuse",
                    "recommended_action": "needs-fix-fast",
                    "recommended_action_why": "Repeat reviewer family is already deterministic.",
                    "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --max-rounds 1",
                    "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
                    "steps": [
                        {"name": "sc-test", "status": "ok", "rc": 0},
                        {"name": "sc-acceptance-check", "status": "ok", "rc": 0},
                        {"name": "sc-llm-review", "status": "fail", "rc": 1}
                    ],
                    "clean_state": {"state": "deterministic_ok_llm_not_clean", "llm_review": "needs-fix"},
                    "latest_summary_signals": {"reason": "rerun_blocked:repeat_review_needs_fix"},
                    "chapter6_hints": {
                        "next_action": "needs-fix-fast",
                        "blocked_by": "rerun_guard",
                        "rerun_forbidden": True,
                        "can_skip_6_7": True,
                        "can_go_to_6_8": True,
                        "rerun_override_flag": "--allow-rerun"
                    },
                    "diagnostics": {}
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-07",
                    "task_id": "15",
                    "requested_run_id": run_id,
                    "run_id": run_id,
                    "status": "fail",
                    "delivery_profile": "fast-ship",
                    "security_profile": "host-safe",
                    "approval": {
                        "soft_gate": True,
                        "required_action": "fork",
                        "status": "pending",
                        "decision": "",
                        "reason": "Waiting for operator approval.",
                        "request_id": f"{run_id}:fork",
                        "request_path": str(root / "approval-request.json"),
                        "response_path": "",
                        "recommended_action": "pause",
                        "allowed_actions": ["inspect", "pause"],
                        "blocked_actions": ["fork", "resume", "rerun"]
                    },
                    "agent_review": {"recommended_action": "fork"}
                },
            )
            run_events_path = out_dir / "run-events.jsonl"
            run_events_path.write_text(
                "\n".join(
                    json.dumps(item, ensure_ascii=False)
                    for item in [
                        {
                            "schema_version": "1.0.0",
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "event": "run_started",
                            "event_family": "run",
                            "task_id": "15",
                            "run_id": run_id,
                            "turn_id": f"{run_id}:turn-1",
                            "turn_seq": 1,
                            "delivery_profile": "fast-ship",
                            "security_profile": "host-safe",
                            "item_kind": "run",
                            "item_id": run_id,
                            "step_name": None,
                            "status": "ok",
                            "details": {}
                        },
                        {
                            "schema_version": "1.0.0",
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "event": "run_resumed",
                            "event_family": "run",
                            "task_id": "15",
                            "run_id": run_id,
                            "turn_id": f"{run_id}:turn-2",
                            "turn_seq": 2,
                            "delivery_profile": "fast-ship",
                            "security_profile": "host-safe",
                            "item_kind": "run",
                            "item_id": run_id,
                            "step_name": None,
                            "status": "ok",
                            "details": {}
                        },
                        {
                            "schema_version": "1.0.0",
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "event": "reviewer_completed",
                            "event_family": "reviewer",
                            "task_id": "15",
                            "run_id": run_id,
                            "turn_id": f"{run_id}:turn-2",
                            "turn_seq": 2,
                            "delivery_profile": "fast-ship",
                            "security_profile": "host-safe",
                            "item_kind": "reviewer",
                            "item_id": "code-reviewer",
                            "step_name": None,
                            "status": "needs-fix",
                            "details": {"reviewer": "code-reviewer", "review_verdict": "needs-fix"}
                        },
                        {
                            "schema_version": "1.0.0",
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "event": "approval_request_written",
                            "event_family": "approval",
                            "task_id": "15",
                            "run_id": run_id,
                            "turn_id": f"{run_id}:turn-2",
                            "turn_seq": 2,
                            "delivery_profile": "fast-ship",
                            "security_profile": "host-safe",
                            "item_kind": "approval",
                            "item_id": f"{run_id}:fork",
                            "step_name": None,
                            "status": "pending",
                            "details": {"action": "fork", "request_id": f"{run_id}:fork", "transition": "created"}
                        },
                        {
                            "schema_version": "1.0.0",
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "event": "sidecar_active_task_synced",
                            "event_family": "sidecar",
                            "task_id": "15",
                            "run_id": run_id,
                            "turn_id": f"{run_id}:turn-2",
                            "turn_seq": 2,
                            "delivery_profile": "fast-ship",
                            "security_profile": "host-safe",
                            "item_kind": "sidecar",
                            "item_id": "task-active",
                            "step_name": None,
                            "status": "ok",
                            "details": {"sidecar": "task-active"}
                        }
                    ]
                ) + "\n",
                encoding="utf-8",
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="15",
                run_id=run_id,
                status="fail",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )

            validate_active_task_payload(payload)
            self.assertEqual("active-task-sidecar", payload["cmd"])
            self.assertEqual("pause", payload["approval"]["recommended_action"])
            self.assertEqual(f"{run_id}:turn-1", payload["run_event_summary"]["previous_turn_id"])
            self.assertEqual("py -3 scripts/python/dev_cli.py resume-task --task-id 15", payload["candidate_commands"]["resume_summary"])

    def test_build_active_task_payload_should_prefer_needs_fix_fast_when_rerun_guard_blocks_llm_only_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, latest_path = self._build_bundle(
                root=root,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "status": "fail",
                    "reason": "rerun_blocked:deterministic_green_llm_not_clean",
                    "reuse_mode": "deterministic-only-reuse",
                    "steps": [
                        {"name": "sc-test", "status": "ok", "summary_file": str((root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-14-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" / "child-artifacts" / "sc-test" / "summary.json"))},
                        {"name": "sc-acceptance-check", "status": "ok"},
                        {"name": "sc-llm-review", "status": "fail", "summary_file": str((root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-14-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" / "child-artifacts" / "sc-llm-review" / "summary.json"))},
                    ],
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-07",
                    "task_id": "14",
                    "requested_run_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "run_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "status": "fail",
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
                    "diagnostics": {
                        "rerun_guard": {
                            "kind": "deterministic_green_llm_not_clean",
                            "blocked": True,
                            "recommended_path": "llm-only",
                        }
                    },
                },
                extra_files={
                    "child-artifacts/sc-test/summary.json": {
                        "cmd": "sc-test",
                        "status": "ok",
                        "steps": [{"name": "unit", "status": "ok", "rc": 0}],
                    },
                    "child-artifacts/sc-llm-review/summary.json": {
                        "status": "fail",
                        "results": [
                            {"agent": "code-reviewer", "status": "fail", "rc": 124, "details": {"verdict": ""}},
                        ],
                    },
                },
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                status="fail",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )

            self.assertEqual("needs-fix-fast", payload["recommended_action"])
            self.assertEqual("rerun_guard", payload["chapter6_hints"]["blocked_by"])
            self.assertTrue(payload["chapter6_hints"]["can_skip_6_7"])
            self.assertTrue(payload["chapter6_hints"]["can_go_to_6_8"])
            self.assertTrue(payload["chapter6_hints"]["rerun_forbidden"])
            self.assertEqual("--allow-full-rerun", payload["chapter6_hints"]["rerun_override_flag"])
            self.assertEqual(payload["candidate_commands"]["needs_fix_fast"], payload["recommended_command"])
            self.assertIn(payload["candidate_commands"]["rerun"], payload["forbidden_commands"])
            self.assertIn(payload["candidate_commands"]["resume"], payload["forbidden_commands"])
            self.assertIn("rerun guard", payload["recommended_action_why"].lower())


    def test_build_active_task_payload_should_emit_resume_summary_command_for_continue_action(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
            out_dir, latest_path = self._build_bundle(
                root=root,
                run_id=run_id,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": run_id,
                    "status": "ok",
                    "reason": "pipeline_clean",
                    "reuse_mode": "full-clean-reuse",
                    "steps": [
                        {"name": "sc-test", "status": "ok", "rc": 0},
                        {"name": "sc-acceptance-check", "status": "ok", "rc": 0},
                        {"name": "sc-llm-review", "status": "ok", "rc": 0},
                    ],
                },
                execution_context_payload={
                    "run_id": run_id,
                    "delivery_profile": "fast-ship",
                    "security_profile": "host-safe",
                },
                repair_guide_payload={
                    "schema_version": "1.0.0",
                    "status": "not-needed",
                    "task_id": "14",
                    "summary_status": "ok",
                    "failed_step": "",
                    "approval": {},
                    "generated_from": {},
                    "recommendations": [],
                },
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id=run_id,
                status="ok",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )

            self.assertEqual("continue", payload["recommended_action"])
            self.assertEqual(payload["candidate_commands"]["resume_summary"], payload["recommended_command"])

    def test_build_active_task_payload_should_respect_approval_pause_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "ffffffffffffffffffffffffffffffff"
            out_dir, latest_path = self._build_bundle(
                root=root,
                run_id=run_id,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": run_id,
                    "status": "fail",
                    "reason": "review_pending",
                    "reuse_mode": "none",
                    "steps": [
                        {"name": "sc-test", "status": "ok", "rc": 0},
                        {"name": "sc-acceptance-check", "status": "ok", "rc": 0},
                        {"name": "sc-llm-review", "status": "fail", "rc": 1},
                    ],
                },
                execution_context_payload={
                    "run_id": run_id,
                    "delivery_profile": "fast-ship",
                    "security_profile": "host-safe",
                    "approval": {
                        "required_action": "fork",
                        "status": "pending",
                        "recommended_action": "pause",
                        "allowed_actions": ["inspect", "pause"],
                        "blocked_actions": ["fork", "resume", "rerun"],
                    },
                },
                repair_guide_payload={
                    "schema_version": "1.0.0",
                    "status": "needs-fix",
                    "task_id": "14",
                    "summary_status": "fail",
                    "failed_step": "",
                    "approval": {
                        "required_action": "fork",
                        "status": "pending",
                        "recommended_action": "pause",
                        "allowed_actions": ["inspect", "pause"],
                        "blocked_actions": ["fork", "resume", "rerun"],
                    },
                    "generated_from": {},
                    "recommendations": [],
                },
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id=run_id,
                status="fail",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )
            markdown = active_task_sidecar.render_active_task_markdown(payload)

            self.assertEqual("pause", payload["approval"]["recommended_action"])
            self.assertEqual(["inspect", "pause"], payload["approval"]["allowed_actions"])
            self.assertEqual("", payload["recommended_command"])
            self.assertIn(payload["candidate_commands"]["resume"], payload["forbidden_commands"])
            self.assertIn(payload["candidate_commands"]["fork"], payload["forbidden_commands"])
            self.assertIn(payload["candidate_commands"]["rerun"], payload["forbidden_commands"])
            self.assertIn("- Approval required action: fork", markdown)
            self.assertIn("- Approval status: pending", markdown)
            self.assertIn("- Approval recommended action: pause", markdown)
            self.assertIn("- Approval allowed actions: inspect, pause", markdown)
            self.assertIn("- Approval blocked actions: fork, resume, rerun", markdown)

    def test_render_active_task_markdown_should_surface_run_event_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "11112222333344445555666677778888"
            out_dir, latest_path = self._build_bundle(
                root=root,
                run_id=run_id,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": run_id,
                    "status": "fail",
                    "reason": "rerun_blocked:deterministic_green_llm_not_clean",
                    "reuse_mode": "deterministic-only-reuse",
                    "steps": [
                        {"name": "sc-test", "status": "ok", "rc": 0},
                        {"name": "sc-acceptance-check", "status": "ok", "rc": 0},
                        {"name": "sc-llm-review", "status": "fail", "rc": 1},
                    ],
                },
                execution_context_payload={
                    "run_id": run_id,
                    "delivery_profile": "fast-ship",
                    "security_profile": "host-safe",
                    "approval": {},
                },
            )
            run_events_path = out_dir / "run-events.jsonl"
            run_events_path.write_text(
                "\n".join(
                    json.dumps(item, ensure_ascii=False)
                    for item in [
                        {
                            "schema_version": "1.0.0",
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "event": "run_started",
                            "event_family": "run",
                            "task_id": "14",
                            "run_id": run_id,
                            "turn_id": f"{run_id}:turn-1",
                            "turn_seq": 1,
                            "delivery_profile": "fast-ship",
                            "security_profile": "host-safe",
                            "item_kind": "run",
                            "item_id": run_id,
                            "step_name": None,
                            "status": "ok",
                            "details": {},
                        },
                        {
                            "schema_version": "1.0.0",
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "event": "run_resumed",
                            "event_family": "run",
                            "task_id": "14",
                            "run_id": run_id,
                            "turn_id": f"{run_id}:turn-2",
                            "turn_seq": 2,
                            "delivery_profile": "fast-ship",
                            "security_profile": "host-safe",
                            "item_kind": "run",
                            "item_id": run_id,
                            "step_name": None,
                            "status": "ok",
                            "details": {},
                        },
                        {
                            "schema_version": "1.0.0",
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "event": "approval_request_written",
                            "event_family": "approval",
                            "task_id": "14",
                            "run_id": run_id,
                            "turn_id": f"{run_id}:turn-2",
                            "turn_seq": 2,
                            "delivery_profile": "fast-ship",
                            "security_profile": "host-safe",
                            "item_kind": "approval",
                            "item_id": f"{run_id}:fork",
                            "step_name": None,
                            "status": "pending",
                            "details": {"action": "fork", "request_id": f"{run_id}:fork", "transition": "created"},
                        },
                        {
                            "schema_version": "1.0.0",
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "event": "reviewer_completed",
                            "event_family": "reviewer",
                            "task_id": "14",
                            "run_id": run_id,
                            "turn_id": f"{run_id}:turn-2",
                            "turn_seq": 2,
                            "delivery_profile": "fast-ship",
                            "security_profile": "host-safe",
                            "item_kind": "reviewer",
                            "item_id": "code-reviewer",
                            "step_name": None,
                            "status": "fail",
                            "details": {"reviewer": "code-reviewer", "review_verdict": "needs-fix"},
                        },
                        {
                            "schema_version": "1.0.0",
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "event": "sidecar_execution_context_synced",
                            "event_family": "sidecar",
                            "task_id": "14",
                            "run_id": run_id,
                            "turn_id": f"{run_id}:turn-2",
                            "turn_seq": 2,
                            "delivery_profile": "fast-ship",
                            "security_profile": "host-safe",
                            "item_kind": "sidecar",
                            "item_id": "execution-context.json",
                            "step_name": None,
                            "status": "ok",
                            "details": {"sidecar": "execution-context.json"},
                        },
                        {
                            "schema_version": "1.0.0",
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "event": "run_completed",
                            "event_family": "run",
                            "task_id": "14",
                            "run_id": run_id,
                            "turn_id": f"{run_id}:turn-2",
                            "turn_seq": 2,
                            "delivery_profile": "fast-ship",
                            "security_profile": "host-safe",
                            "item_kind": "run",
                            "item_id": run_id,
                            "step_name": None,
                            "status": "fail",
                            "details": {},
                        },
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id=run_id,
                status="fail",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )
            markdown = active_task_sidecar.render_active_task_markdown(payload)

            self.assertEqual(2, payload["run_event_summary"]["latest_turn_seq"])
            self.assertEqual(f"{run_id}:turn-2", payload["run_event_summary"]["latest_turn_id"])
            self.assertEqual(f"{run_id}:turn-1", payload["run_event_summary"]["previous_turn_id"])
            self.assertTrue(payload["run_event_summary"]["approval_changed"])
            self.assertIn("- Run events event count: 6", markdown)
            self.assertIn(f"- Run events latest turn: {run_id}:turn-2 seq=2", markdown)
            self.assertIn(f"- Run events previous turn: {run_id}:turn-1 seq=1", markdown)
            self.assertIn("- Run events latest event: run_completed", markdown)
            self.assertIn("- Run events families: run=3, approval=1, reviewer=1, sidecar=1", markdown)
            self.assertIn("- Run events previous turn families: run=1", markdown)
            self.assertIn("- Run events latest turn families: run=2, approval=1, reviewer=1, sidecar=1", markdown)
            self.assertIn("- Run events turn family delta: approval=+1, reviewer=+1, run=+1, sidecar=+1", markdown)
            self.assertIn("- Run events new reviewers: code-reviewer", markdown)
            self.assertIn("- Run events new sidecars: execution-context.json", markdown)
            self.assertIn("- Run events approval changed: True", markdown)
            self.assertIn("- Reviewer activity: code-reviewer:fail/reviewer_completed", markdown)
            self.assertIn("- Sidecar activity: execution-context.json:ok/sidecar_execution_context_synced", markdown)
            self.assertIn(f"- Approval activity: pending/approval_request_written action=fork request_id={run_id}:fork transition=created", markdown)


    def test_build_active_task_payload_should_prefer_needs_fix_fast_when_rerun_guard_blocks_repeat_review_needs_fix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, latest_path = self._build_bundle(
                root=root,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    "status": "fail",
                    "reason": "rerun_blocked:repeat_review_needs_fix",
                    "reuse_mode": "none",
                    "steps": [
                        {"name": "sc-llm-review", "status": "ok"},
                    ],
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-07",
                    "task_id": "14",
                    "requested_run_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    "run_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    "status": "fail",
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
                    "diagnostics": {
                        "rerun_guard": {
                            "kind": "repeat_review_needs_fix",
                            "blocked": True,
                            "recommended_path": "needs-fix-fast",
                        }
                    },
                },
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                status="fail",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )

            self.assertEqual("needs-fix-fast", payload["recommended_action"])
            self.assertEqual("rerun_guard", payload["chapter6_hints"]["blocked_by"])
            self.assertTrue(payload["chapter6_hints"]["can_skip_6_7"])
            self.assertTrue(payload["chapter6_hints"]["can_go_to_6_8"])

            self.assertEqual(payload["candidate_commands"]["needs_fix_fast"], payload["recommended_command"])
            self.assertIn(payload["candidate_commands"]["rerun"], payload["forbidden_commands"])

            self.assertIn("needs fix family", payload["recommended_action_why"].lower())

    def test_build_active_task_payload_should_block_planned_only_terminal_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, latest_path = self._build_bundle(
                root=root,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "cccccccccccccccccccccccccccccccc",
                    "status": "fail",
                    "run_type": "planned-only",
                    "started_at_utc": "2026-04-08T00:00:00+00:00",
                    "finished_at_utc": "2026-04-08T00:00:03+00:00",
                    "reason": "planned_only_incomplete",
                    "reuse_mode": "none",
                    "steps": [
                        {"name": "sc-test", "status": "planned"},
                        {"name": "sc-acceptance-check", "status": "planned"},
                    ],
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-08",
                    "task_id": "14",
                    "requested_run_id": "cccccccccccccccccccccccccccccccc",
                    "run_id": "cccccccccccccccccccccccccccccccc",
                    "status": "fail",
                    "run_type": "planned-only",
                    "reason": "planned_only_incomplete",
                    "reuse_mode": "none",
                    "started_at_utc": "2026-04-08T00:00:00+00:00",
                    "finished_at_utc": "2026-04-08T00:00:03+00:00",
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
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id="cccccccccccccccccccccccccccccccc",
                status="fail",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )

            self.assertEqual("rerun", payload["recommended_action"])
            self.assertEqual("artifact_integrity", payload["chapter6_hints"]["blocked_by"])
            self.assertEqual("planned_only_incomplete", payload["diagnostics"]["artifact_integrity"]["kind"])
            self.assertEqual(payload["candidate_commands"]["rerun"], payload["recommended_command"])

    def test_build_active_task_payload_should_infer_legacy_planned_only_terminal_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, latest_path = self._build_bundle(
                root=root,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "dddddddddddddddddddddddddddddddd",
                    "status": "ok",
                    "steps": [
                        {"name": "sc-test", "status": "planned"},
                        {"name": "sc-acceptance-check", "status": "planned"},
                        {"name": "sc-llm-review", "status": "planned"},
                    ],
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-08",
                    "task_id": "14",
                    "requested_run_id": "dddddddddddddddddddddddddddddddd",
                    "run_id": "dddddddddddddddddddddddddddddddd",
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
            )
            latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
            latest_payload["reason"] = "in_progress"
            latest_path.write_text(json.dumps(latest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id="dddddddddddddddddddddddddddddddd",
                status="ok",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )

            self.assertEqual("planned-only", payload["latest_summary_signals"]["run_type"])
            self.assertEqual("planned_only_incomplete", payload["latest_summary_signals"]["reason"])
            self.assertEqual("artifact_integrity", payload["chapter6_hints"]["blocked_by"])
            self.assertEqual("rerun", payload["recommended_action"])
            self.assertEqual("planned_only_incomplete", payload["diagnostics"]["artifact_integrity"]["kind"])

    def test_build_active_task_payload_should_fallback_to_latest_reason_and_reuse_mode_for_legacy_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, latest_path = self._build_bundle(
                root=root,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "status": "fail",
                    "steps": [
                        {"name": "sc-test", "status": "fail"},
                    ],
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-07",
                    "task_id": "14",
                    "requested_run_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "run_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
            )
            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            latest["reason"] = "step_failed:sc-test"
            latest["reuse_mode"] = "none"
            latest_path.write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                status="fail",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )

            self.assertEqual("step_failed:sc-test", payload["latest_summary_signals"]["reason"])
            self.assertEqual("none", payload["latest_summary_signals"]["reuse_mode"])

    def test_build_active_task_payload_should_follow_latest_bundle_when_out_dir_argument_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_out_dir, latest_path = self._build_bundle(
                root=root,
                run_id="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                    "status": "ok",
                    "reason": "pipeline_clean",
                    "reuse_mode": "none",
                    "steps": [
                        {"name": "sc-test", "status": "ok"},
                    ],
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-07",
                    "task_id": "14",
                    "requested_run_id": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                    "run_id": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
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
            )
            stale_out_dir = root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-14-stale"
            stale_out_dir.mkdir(parents=True, exist_ok=True)
            _write_json(stale_out_dir / "summary.json", {"status": "fail", "steps": [{"name": "sc-test", "status": "planned"}]})
            _write_json(stale_out_dir / "execution-context.json", {"status": "fail", "diagnostics": {}})
            _write_json(stale_out_dir / "repair-guide.json", {"status": "needs-fix", "recommendations": []})
            (stale_out_dir / "repair-guide.md").write_text("# stale\n", encoding="utf-8")

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id="stale",
                status="fail",
                out_dir=stale_out_dir,
                latest_json_path=latest_path,
                root=root,
            )

            self.assertEqual("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", payload["run_id"])
            self.assertEqual("ok", payload["status"])
            self.assertEqual(latest_out_dir.as_posix().lower(), (root / payload["paths"]["out_dir"]).as_posix().lower())
            self.assertEqual("pipeline_clean", payload["latest_summary_signals"]["reason"])

    def test_build_active_task_payload_should_surface_artifact_integrity_when_run_completed_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, latest_path = self._build_bundle(
                root=root,
                run_id="ffffffffffffffffffffffffffffffff",
                include_run_completed=False,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "ffffffffffffffffffffffffffffffff",
                    "status": "ok",
                    "reason": "pipeline_clean",
                    "reuse_mode": "none",
                    "steps": [
                        {"name": "sc-test", "status": "ok"},
                    ],
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-07",
                    "task_id": "14",
                    "requested_run_id": "ffffffffffffffffffffffffffffffff",
                    "run_id": "ffffffffffffffffffffffffffffffff",
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
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id="ffffffffffffffffffffffffffffffff",
                status="ok",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )

            self.assertEqual("artifact_integrity", payload["chapter6_hints"]["blocked_by"])
            self.assertEqual("rerun", payload["recommended_action"])
            self.assertIn("completed producer run", payload["recommended_action_why"].lower())
            self.assertEqual("artifact_incomplete", payload["diagnostics"]["artifact_integrity"]["kind"])

    def test_build_active_task_payload_should_prefer_inspect_when_repeat_deterministic_failure_guard_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, latest_path = self._build_bundle(
                root=root,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    "status": "fail",
                    "reason": "rerun_blocked:repeat_deterministic_failure",
                    "reuse_mode": "none",
                    "steps": [
                        {"name": "sc-test", "status": "fail"},
                    ],
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-07",
                    "task_id": "14",
                    "requested_run_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    "run_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
                    "diagnostics": {
                        "rerun_guard": {
                            "kind": "repeat_deterministic_failure",
                            "blocked": True,
                            "fingerprint": "sc-test|unit|2|compile_error",
                        }
                    },
                },
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                status="fail",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )

            self.assertEqual("inspect", payload["recommended_action"])
            self.assertEqual("rerun_guard", payload["chapter6_hints"]["blocked_by"])
            self.assertFalse(payload["chapter6_hints"]["can_go_to_6_8"])
            self.assertTrue(payload["chapter6_hints"]["rerun_forbidden"])
            self.assertEqual("--allow-repeat-deterministic-failures", payload["chapter6_hints"]["rerun_override_flag"])
            self.assertIn("repeated deterministic", payload["recommended_action_why"].lower())

    def test_build_active_task_payload_should_prefer_inspect_when_dirty_worktree_rerun_guard_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, latest_path = self._build_bundle(
                root=root,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "dirty1111dirty1111dirty1111dirty11",
                    "status": "fail",
                    "reason": "rerun_blocked:dirty_worktree_unsafe_paths_ceiling",
                    "reuse_mode": "none",
                    "steps": [],
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-07",
                    "task_id": "14",
                    "requested_run_id": "dirty1111dirty1111dirty1111dirty11",
                    "run_id": "dirty1111dirty1111dirty1111dirty11",
                    "status": "fail",
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
                    "diagnostics": {
                        "rerun_guard": {
                            "kind": "dirty_worktree_unsafe_paths_ceiling",
                            "blocked": True,
                            "recommended_path": "inspect",
                            "allow_override_flag": "--allow-large-change-scope-rerun",
                        }
                    },
                },
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id="dirty1111dirty1111dirty1111dirty11",
                status="fail",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )

            self.assertEqual("inspect", payload["recommended_action"])
            self.assertEqual("rerun_guard", payload["chapter6_hints"]["blocked_by"])
            self.assertFalse(payload["chapter6_hints"]["can_go_to_6_8"])
            self.assertTrue(payload["chapter6_hints"]["rerun_forbidden"])
            self.assertEqual("--allow-large-change-scope-rerun", payload["chapter6_hints"]["rerun_override_flag"])
            self.assertEqual(payload["candidate_commands"]["resume_summary"], payload["recommended_command"])
            self.assertIn(payload["candidate_commands"]["rerun"], payload["forbidden_commands"])
            self.assertIn("safe scope", payload["recommended_action_why"].lower())

    def test_build_active_task_payload_should_route_first_llm_timeout_stop_loss_to_needs_fix_fast(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, latest_path = self._build_bundle(
                root=root,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "cccccccccccccccccccccccccccccccc",
                    "status": "fail",
                    "reason": "step_failed",
                    "reuse_mode": "none",
                    "steps": [
                        {"name": "sc-test", "status": "ok"},
                        {"name": "sc-acceptance-check", "status": "ok"},
                        {"name": "sc-llm-review", "status": "fail", "summary_file": str((root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-14-cccccccccccccccccccccccccccccccc" / "child-artifacts" / "sc-llm-review" / "summary.json"))},
                    ],
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-07",
                    "task_id": "14",
                    "requested_run_id": "cccccccccccccccccccccccccccccccc",
                    "run_id": "cccccccccccccccccccccccccccccccc",
                    "status": "fail",
                    "delivery_profile": "fast-ship",
                    "security_profile": "host-safe",
                    "failed_step": "sc-llm-review",
                    "paths": {},
                    "git": {},
                    "recovery": {},
                    "marathon": {},
                    "agent_review": {},
                    "llm_review": {},
                    "approval": {},
                    "diagnostics": {
                        "llm_retry_stop_loss": {
                            "kind": "single_timeout_after_deterministic_green",
                            "blocked": True,
                            "step_name": "sc-llm-review",
                        }
                    },
                },
                extra_files={
                    "child-artifacts/sc-llm-review/summary.json": {
                        "status": "fail",
                        "results": [
                            {"agent": "code-reviewer", "status": "fail", "rc": 124, "details": {"verdict": ""}},
                        ],
                    },
                },
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id="cccccccccccccccccccccccccccccccc",
                status="fail",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )
            markdown = active_task_sidecar.render_active_task_markdown(payload)

            self.assertEqual("needs-fix-fast", payload["recommended_action"])
            self.assertEqual("llm_retry_stop_loss", payload["chapter6_hints"]["blocked_by"])
            self.assertTrue(payload["chapter6_hints"]["rerun_forbidden"])
            self.assertEqual(payload["candidate_commands"]["needs_fix_fast"], payload["recommended_command"])
            self.assertIn(payload["candidate_commands"]["rerun"], payload["forbidden_commands"])
            self.assertIn("llm timeout", payload["recommended_action_why"].lower())
            self.assertIn("- Recommended command: `py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1`", markdown)
            self.assertIn("- Forbidden commands: `py -3 scripts/sc/run_review_pipeline.py --task-id 14`", markdown)
            self.assertIn("- Latest run type: full", markdown)
            self.assertIn("- Latest artifact integrity: none", markdown)
            self.assertIn(
                "- Chapter6 stop-loss note: This run already stopped after the first costly llm timeout; continue with the narrow llm-only closure path instead of reopening deterministic steps.",
                markdown,
            )
            self.assertIn("llm_retry_stop_loss", markdown)

    def test_render_active_task_markdown_should_surface_planned_only_artifact_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, latest_path = self._build_bundle(
                root=root,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "99999999999999999999999999999999",
                    "status": "ok",
                    "steps": [
                        {"name": "sc-test", "status": "planned"},
                        {"name": "sc-acceptance-check", "status": "planned"},
                    ],
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-08",
                    "task_id": "14",
                    "requested_run_id": "99999999999999999999999999999999",
                    "run_id": "99999999999999999999999999999999",
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
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id="99999999999999999999999999999999",
                status="ok",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )
            markdown = active_task_sidecar.render_active_task_markdown(payload)

            self.assertEqual("planned_only_incomplete", payload["latest_summary_signals"]["artifact_integrity_kind"])
            self.assertIn("- Latest run type: planned-only", markdown)
            self.assertIn("- Latest artifact integrity: planned_only_incomplete", markdown)
            self.assertIn("- Diagnostics artifact_integrity: blocked=True kind=planned_only_incomplete", markdown)

    def test_build_active_task_payload_should_route_sc_test_retry_stop_loss_to_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "cccc1111cccc1111cccc1111cccc1111"
            out_dir, latest_path = self._build_bundle(
                root=root,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": run_id,
                    "status": "fail",
                    "reason": "step_failed:sc-test",
                    "reuse_mode": "none",
                    "steps": [
                        {"name": "sc-test", "status": "fail"},
                    ],
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-07",
                    "task_id": "14",
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
                    "diagnostics": {
                        "sc_test_retry_stop_loss": {
                            "kind": "unit_failure_known",
                            "blocked": True,
                            "step_name": "sc-test",
                        }
                    },
                },
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id=run_id,
                status="fail",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )
            markdown = active_task_sidecar.render_active_task_markdown(payload)

            self.assertEqual("rerun", payload["recommended_action"])
            self.assertEqual("sc_test_retry_stop_loss", payload["chapter6_hints"]["blocked_by"])
            self.assertTrue(payload["chapter6_hints"]["rerun_forbidden"])
            self.assertEqual(payload["candidate_commands"]["rerun"], payload["recommended_command"])
            self.assertIn("known unit failure", payload["recommended_action_why"].lower())
            self.assertIn("- Diagnostics sc_test_retry_stop_loss:", markdown)

    def test_build_active_task_payload_should_surface_recent_failure_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for run_id in ("hist-new", "hist-old"):
                _out_dir, hist_latest_path = self._build_bundle(
                    root=root,
                    task_id="14",
                    run_id=run_id,
                    summary_payload={
                        "cmd": "sc-review-pipeline",
                        "task_id": "14",
                        "run_id": run_id,
                        "status": "fail",
                        "reason": "step_failed:sc-test",
                        "steps": [
                            {
                                "name": "sc-test",
                                "status": "fail",
                                "rc": 2,
                                "summary_file": str((root / "logs" / "ci" / "2026-04-07" / f"sc-review-pipeline-task-14-{run_id}" / "child-artifacts" / "sc-test" / "summary.json")),
                            },
                        ],
                    },
                    execution_context_payload={
                        "schema_version": "1.0.0",
                        "cmd": "sc-review-pipeline",
                        "date": "2026-04-07",
                        "task_id": "14",
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
                    extra_files={
                        "child-artifacts/sc-test/summary.json": {
                            "cmd": "sc-test",
                            "status": "fail",
                            "steps": [
                                {"name": "unit", "status": "fail", "rc": 2, "reason": "compile_error"},
                            ],
                        },
                    },
                )
                latest_payload = json.loads(hist_latest_path.read_text(encoding="utf-8"))
                latest_payload["status"] = "fail"
                hist_latest_path.write_text(json.dumps(latest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            out_dir = root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-14-hist-old"
            latest_path = root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-14" / "latest.json"
            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id="hist-old",
                status="fail",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )

            recent_failure_summary = payload["diagnostics"]["recent_failure_summary"]
            self.assertEqual(2, recent_failure_summary["same_family_count"])
            self.assertTrue(recent_failure_summary["stop_full_rerun_recommended"])
            self.assertEqual("inspect", payload["recommended_action"])
            self.assertEqual("recent_failure_summary", payload["chapter6_hints"]["blocked_by"])
            self.assertTrue(payload["chapter6_hints"]["rerun_forbidden"])
            self.assertEqual(payload["candidate_commands"]["resume_summary"], payload["recommended_command"])
            self.assertIn(payload["candidate_commands"]["rerun"], payload["forbidden_commands"])
            markdown = active_task_sidecar.render_active_task_markdown(payload)
            self.assertIn(
                "- Chapter6 stop-loss note: Recent runs already repeat the same failure family; inspect the repeated fingerprint and fix the root cause before rerunning 6.7.",
                markdown,
            )

    def test_build_active_task_payload_should_not_continue_when_repair_guide_needs_fix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
            out_dir, latest_path = self._build_bundle(
                root=root,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": run_id,
                    "status": "ok",
                    "reason": "pipeline_clean",
                    "reuse_mode": "none",
                    "steps": [
                        {"name": "sc-test", "status": "ok"},
                        {"name": "sc-acceptance-check", "status": "ok"},
                        {"name": "sc-llm-review", "status": "ok"},
                    ],
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-07",
                    "task_id": "14",
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
                repair_guide_payload={
                    "schema_version": "1.0.0",
                    "status": "needs-fix",
                    "task_id": "14",
                    "summary_status": "ok",
                    "failed_step": "",
                    "approval": {},
                    "generated_from": {},
                    "recommendations": [
                        {"title": "Close remaining review findings"},
                    ],
                },
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id=run_id,
                status="ok",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )

            self.assertEqual("needs-fix", payload["repair_status"])
            self.assertEqual("inspect", payload["recommended_action"])
            self.assertEqual("", payload["chapter6_hints"]["blocked_by"])
            self.assertEqual(payload["candidate_commands"]["resume_summary"], payload["recommended_command"])
            self.assertIn("repair", payload["recommended_action_why"].lower())

    def test_build_active_task_payload_should_surface_waste_signal_and_prefer_resume_for_sc_test_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "dddddddddddddddddddddddddddddddd"
            sc_test_summary_path = root / "logs" / "ci" / "2026-04-07" / f"sc-review-pipeline-task-14-{run_id}" / "child-artifacts" / "sc-test" / "summary.json"
            out_dir, latest_path = self._build_bundle(
                root=root,
                summary_payload={
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": run_id,
                    "status": "fail",
                    "reason": "step_failed",
                    "reuse_mode": "none",
                    "steps": [
                        {"name": "sc-test", "status": "fail", "summary_file": str(sc_test_summary_path)},
                    ],
                },
                execution_context_payload={
                    "schema_version": "1.0.0",
                    "cmd": "sc-review-pipeline",
                    "date": "2026-04-07",
                    "task_id": "14",
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
                extra_files={
                    "child-artifacts/sc-test/summary.json": {
                        "cmd": "sc-test",
                        "status": "fail",
                        "steps": [
                            {"name": "unit", "status": "fail", "rc": 2},
                            {"name": "gdunit-hard", "status": "fail", "rc": 1},
                        ],
                    },
                },
            )

            payload = active_task_sidecar.build_active_task_payload(
                task_id="14",
                run_id=run_id,
                status="fail",
                out_dir=out_dir,
                latest_json_path=latest_path,
                root=root,
            )

            self.assertTrue(payload["diagnostics"]["waste_signals"]["unit_failed_but_engine_lane_ran"])
            self.assertEqual("resume", payload["recommended_action"])
            self.assertEqual("waste_signals", payload["chapter6_hints"]["blocked_by"])
            self.assertIn("unit failure", payload["recommended_action_why"].lower())


if __name__ == "__main__":
    unittest.main()
