from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from _pipeline_helpers import has_materialized_pipeline_steps


@dataclass
class PipelineSession:
    args: Any
    out_dir: Path
    task_id: str
    run_id: str
    requested_run_id: str
    delivery_profile: str
    security_profile: str
    llm_review_context: dict[str, Any]
    summary: dict[str, Any]
    marathon_state: dict[str, Any]
    agent_review_mode: str
    schema_error_log: Path
    apply_runtime_policy: Callable[[dict[str, Any]], dict[str, Any]]
    apply_agent_review_signal: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
    validate_pipeline_summary: Callable[[dict[str, Any]], None]
    summary_schema_error: type[Exception]
    write_harness_capabilities: Callable[..., None]
    write_json: Callable[[Path, Any], None]
    write_text: Callable[[Path, str], None]
    save_marathon_state: Callable[[Path, dict[str, Any]], None]
    build_repair_guide: Callable[..., dict[str, Any]]
    sync_soft_approval_sidecars: Callable[..., dict[str, Any]]
    build_execution_context: Callable[..., dict[str, Any]]
    render_repair_guide_markdown: Callable[[dict[str, Any]], str]
    append_run_event: Callable[..., None]
    write_latest_index: Callable[..., None]
    write_active_task_sidecar: Callable[..., None]
    record_step_result: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
    upsert_step: Callable[[dict[str, Any], dict[str, Any]], None]
    append_step_event: Callable[..., None]
    run_step: Callable[..., dict[str, Any]]
    can_retry_failed_step: Callable[[dict[str, Any], str], bool]
    step_is_already_complete: Callable[[dict[str, Any], str], bool]
    wall_time_exceeded: Callable[[dict[str, Any]], bool]
    mark_wall_time_exceeded: Callable[[dict[str, Any]], dict[str, Any]]
    cap_step_timeout: Callable[[int, dict[str, Any]], int]
    run_agent_review_post_hook: Callable[..., tuple[int, dict[str, Any]]]
    refresh_summary_meta: Callable[[dict[str, Any]], None]

    def _should_publish_recovery_sidecars(self) -> bool:
        return not bool(getattr(self.args, "dry_run", False)) and has_materialized_pipeline_steps(self.summary)

    def persist(self) -> bool:
        self.refresh_summary_meta(self.summary)
        self.marathon_state = self.apply_runtime_policy(self.marathon_state)
        diagnostics = self.marathon_state.get("diagnostics")
        if isinstance(diagnostics, dict):
            self.summary["diagnostics"] = dict(diagnostics)
        else:
            self.summary.pop("diagnostics", None)
        if isinstance(self.marathon_state.get("agent_review"), dict):
            self.marathon_state = self.apply_agent_review_signal(self.marathon_state, self.marathon_state["agent_review"])
        try:
            self.validate_pipeline_summary(self.summary)
        except self.summary_schema_error as exc:
            self.write_text(self.schema_error_log, f"{exc}\n")
            self.write_json(self.out_dir / "summary.invalid.json", self.summary)
            self.save_marathon_state(self.out_dir, self.marathon_state)
            if self._should_publish_recovery_sidecars():
                self.write_latest_index(task_id=self.task_id, run_id=self.run_id, out_dir=self.out_dir, status="fail")
            print(f"[sc-review-pipeline] ERROR: summary schema validation failed. details={self.schema_error_log}")
            return False

        invalid_summary_path = self.out_dir / "summary.invalid.json"
        if self.schema_error_log.exists():
            self.schema_error_log.unlink(missing_ok=True)
        if invalid_summary_path.exists():
            invalid_summary_path.unlink(missing_ok=True)
        self.write_harness_capabilities(
            out_dir=self.out_dir,
            cmd="sc-review-pipeline",
            task_id=self.task_id,
            run_id=self.run_id,
            delivery_profile=self.delivery_profile,
            security_profile=self.security_profile,
        )
        self.write_json(self.out_dir / "summary.json", self.summary)
        self.save_marathon_state(self.out_dir, self.marathon_state)
        provisional_repair_guide = self.build_repair_guide(
            self.summary,
            task_id=self.task_id,
            out_dir=self.out_dir,
            marathon_state=self.marathon_state,
        )
        approval_state = self.sync_soft_approval_sidecars(
            out_dir=self.out_dir,
            task_id=self.task_id,
            run_id=self.run_id,
            summary=self.summary,
            repair_guide=provisional_repair_guide,
            marathon_state=self.marathon_state,
            explicit_fork=bool(self.args.fork),
        )
        repair_guide = self.build_repair_guide(
            self.summary,
            task_id=self.task_id,
            out_dir=self.out_dir,
            marathon_state=self.marathon_state,
            approval_state=approval_state,
        )
        self.write_json(self.out_dir / "repair-guide.json", repair_guide)
        self.write_text(self.out_dir / "repair-guide.md", self.render_repair_guide_markdown(repair_guide))
        self.write_json(
            self.out_dir / "execution-context.json",
            self.build_execution_context(
                task_id=self.task_id,
                requested_run_id=self.requested_run_id,
                run_id=self.run_id,
                out_dir=self.out_dir,
                delivery_profile=self.delivery_profile,
                security_profile=self.security_profile,
                llm_review_context=self.llm_review_context,
                summary=self.summary,
                marathon_state=self.marathon_state,
                approval_state=approval_state,
            ),
        )
        for event_payload in approval_state.get("events") or []:
            if not isinstance(event_payload, dict):
                continue
            self.append_run_event(
                out_dir=self.out_dir,
                event=str(event_payload.get("event") or "approval_updated"),
                task_id=self.task_id,
                run_id=self.run_id,
                delivery_profile=self.delivery_profile,
                security_profile=self.security_profile,
                status=str(event_payload.get("status") or "") or None,
                details=dict(event_payload.get("details") or {}),
            )
        if self._should_publish_recovery_sidecars():
            self.write_latest_index(
                task_id=self.task_id,
                run_id=self.run_id,
                out_dir=self.out_dir,
                status=str(self.summary.get("status", "fail")),
            )
            self.write_active_task_sidecar(
                task_id=self.task_id,
                run_id=self.run_id,
                out_dir=self.out_dir,
                status=str(self.summary.get("status", "fail")),
            )
        return True

    def add_step(self, step: dict[str, Any]) -> bool:
        self.upsert_step(self.summary, step)
        self.marathon_state = self.record_step_result(self.marathon_state, step)
        self.append_step_event(
            out_dir=self.out_dir,
            task_id=self.task_id,
            run_id=self.run_id,
            delivery_profile=self.delivery_profile,
            security_profile=self.security_profile,
            step=step,
        )
        if not self.persist():
            return False
        return step.get("status") != "fail"

    def _current_step_map(self) -> dict[str, dict[str, Any]]:
        steps = self.summary.get("steps") if isinstance(self.summary.get("steps"), list) else []
        return {
            str(item.get("name") or "").strip(): item
            for item in steps
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        }

    def _should_stop_retry_after_timeout(self, step_name: str) -> bool:
        if str(step_name or "").strip() != "sc-llm-review":
            return False
        step_state = (self.marathon_state.get("steps") or {}).get(step_name, {})
        if str(step_state.get("status") or "").strip().lower() != "fail":
            return False
        if int(step_state.get("last_rc") or 0) != 124:
            return False
        step_map = self._current_step_map()
        sc_test_status = str((step_map.get("sc-test") or {}).get("status") or "").strip().lower()
        acceptance_status = str((step_map.get("sc-acceptance-check") or {}).get("status") or "").strip().lower()
        return sc_test_status == "ok" and acceptance_status == "ok"

    def _should_stop_retry_after_sc_test_unit_failure(self, step_name: str) -> bool:
        if str(step_name or "").strip() != "sc-test":
            return False
        step_state = (self.marathon_state.get("steps") or {}).get(step_name, {})
        if str(step_state.get("status") or "").strip().lower() != "fail":
            return False
        summary_file = str(step_state.get("summary_file") or "").strip()
        if not summary_file:
            return False
        summary_path = Path(summary_file)
        if not summary_path.exists():
            return False
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        if not isinstance(payload, dict):
            return False
        steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []
        step_map = {
            str(item.get("name") or "").strip(): item
            for item in steps
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        }
        unit_status = str((step_map.get("unit") or {}).get("status") or "").strip().lower()
        return unit_status == "fail"

    def execute_steps(self, steps: list[tuple[str, list[str], int, bool]], *, resume_or_fork: bool) -> int | None:
        halt_pipeline = False
        for step_name, cmd, timeout_sec, skipped in steps:
            if self.step_is_already_complete(self.marathon_state, step_name):
                continue
            if skipped:
                if not self.add_step({"name": step_name, "status": "skipped", "rc": 0, "cmd": cmd}):
                    return 2 if self.schema_error_log.exists() else 1
                continue
            if self.args.dry_run:
                print(f"[dry-run] {step_name}: {' '.join(cmd)}")
                if not self.add_step({"name": step_name, "status": "planned", "rc": 0, "cmd": cmd}):
                    return 2 if self.schema_error_log.exists() else 1
                continue
            while True:
                if self.wall_time_exceeded(self.marathon_state):
                    self.summary["status"] = "fail"
                    self.marathon_state = self.mark_wall_time_exceeded(self.marathon_state)
                    self.append_run_event(
                        out_dir=self.out_dir,
                        event="wall_time_exceeded",
                        task_id=self.task_id,
                        run_id=self.run_id,
                        delivery_profile=self.delivery_profile,
                        security_profile=self.security_profile,
                        status="fail",
                        details={"step_name": step_name},
                    )
                    halt_pipeline = True
                    break
                step_timeout = self.cap_step_timeout(timeout_sec, self.marathon_state)
                ok = self.add_step(self.run_step(out_dir=self.out_dir, name=step_name, cmd=cmd, timeout_sec=step_timeout))
                if ok:
                    break
                if self.schema_error_log.exists():
                    return 2
                if self._should_stop_retry_after_timeout(step_name):
                    diagnostics = self.marathon_state.setdefault("diagnostics", {})
                    if isinstance(diagnostics, dict):
                        diagnostics["llm_retry_stop_loss"] = {
                            "kind": "single_timeout_after_deterministic_green",
                            "blocked": True,
                            "step_name": step_name,
                        }
                    break
                if self._should_stop_retry_after_sc_test_unit_failure(step_name):
                    diagnostics = self.marathon_state.setdefault("diagnostics", {})
                    if isinstance(diagnostics, dict):
                        diagnostics["sc_test_retry_stop_loss"] = {
                            "kind": "unit_failure_known",
                            "blocked": True,
                            "step_name": step_name,
                        }
                    break
                if not self.can_retry_failed_step(self.marathon_state, step_name):
                    break
            if halt_pipeline:
                break
            current_step = (self.marathon_state.get("steps") or {}).get(step_name, {})
            if str(current_step.get("status") or "") == "fail":
                break
        if halt_pipeline and not self.persist():
            return 2
        if not self.persist():
            return 2
        return None

    def finish(self) -> int:
        if not self.args.dry_run and not self.args.skip_agent_review and self.agent_review_mode != "skip":
            post_hook_rc, self.marathon_state = self.run_agent_review_post_hook(
                out_dir=self.out_dir,
                mode=self.agent_review_mode,
                marathon_state=self.marathon_state,
            )
            if not self.persist():
                return 2
            self._append_run_completed(agent_review_rc=post_hook_rc)
            if post_hook_rc != 0:
                return post_hook_rc
        else:
            self._append_run_completed(agent_review_rc=0)
        self.summary["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        if not self.persist():
            return 2
        return 0 if self.summary["status"] == "ok" else 1

    def _append_run_completed(self, *, agent_review_rc: int) -> None:
        details: dict[str, Any] = {"agent_review_rc": agent_review_rc}
        if agent_review_rc == 0 and (self.args.dry_run or self.args.skip_agent_review or self.agent_review_mode == "skip"):
            details["agent_review_mode"] = self.agent_review_mode
        self.append_run_event(
            out_dir=self.out_dir,
            event="run_completed",
            task_id=self.task_id,
            run_id=self.run_id,
            delivery_profile=self.delivery_profile,
            security_profile=self.security_profile,
            status=str(self.summary.get("status") or "fail"),
            details=details,
        )
