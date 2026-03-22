#!/usr/bin/env python3
"""
Run a deterministic local review pipeline with one shared run_id:
1) sc-test
2) sc-acceptance-check
3) sc-llm-review
"""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path
from typing import Any

from agent_to_agent_review import write_agent_review
from _agent_review_policy import apply_agent_review_policy, apply_agent_review_signal
from _delivery_profile import (
    default_security_profile_for_delivery,
    profile_acceptance_defaults,
    profile_llm_review_defaults,
    resolve_delivery_profile,
)
from _harness_capabilities import write_harness_capabilities
from _marathon_policy import (
    apply_context_refresh_policy,
    cap_step_timeout,
    mark_wall_time_exceeded,
    refresh_diff_stats,
    wall_time_exceeded,
)
from _marathon_state import (
    build_forked_state,
    build_initial_state,
    can_retry_failed_step,
    load_marathon_state,
    mark_aborted,
    record_step_result,
    resolve_existing_out_dir,
    resume_state,
    save_marathon_state,
    step_is_already_complete,
)
from _pipeline_approval import sync_soft_approval_sidecars
from _pipeline_events import append_run_event
from _pipeline_helpers import allocate_out_dir as _allocate_out_dir_impl
from _pipeline_helpers import append_step_event as _append_step_event_impl
from _pipeline_helpers import build_parser as _build_parser_impl
from _pipeline_helpers import load_source_run as _load_source_run_impl
from _pipeline_helpers import pipeline_latest_index_path as _pipeline_latest_index_path_impl
from _pipeline_helpers import pipeline_run_dir as _pipeline_run_dir_impl
from _pipeline_helpers import prepare_env as _prepare_env_impl
from _pipeline_helpers import run_agent_review_post_hook as _run_agent_review_post_hook_impl
from _pipeline_helpers import task_root_id as _task_root_id_impl
from _pipeline_helpers import write_latest_index as _write_latest_index_impl
from _pipeline_plan import build_pipeline_steps
from _pipeline_session import PipelineSession
from _pipeline_support import (
    load_existing_summary as _load_existing_summary,
    resolve_agent_review_mode as _resolve_agent_review_mode,
    run_step as _run_step,
    upsert_step as _upsert_step,
)
from _repair_guidance import build_execution_context, build_repair_guide, render_repair_guide_markdown
from _taskmaster import resolve_triplet
from _technical_debt import write_low_priority_debt_artifacts
from _llm_review_tier import resolve_llm_review_tier_plan
from _summary_schema import SummarySchemaError, validate_pipeline_summary
from _util import write_json, write_text


def build_parser() -> argparse.ArgumentParser:
    return _build_parser_impl()


def _task_root_id(task_id: str) -> str:
    return _task_root_id_impl(task_id)


def _prepare_env(run_id: str, delivery_profile: str, security_profile: str) -> None:
    _prepare_env_impl(run_id, delivery_profile, security_profile)


def _pipeline_run_dir(task_id: str, run_id: str) -> Path:
    return _pipeline_run_dir_impl(task_id, run_id)


def _pipeline_latest_index_path(task_id: str) -> Path:
    return _pipeline_latest_index_path_impl(task_id)


def _write_latest_index(*, task_id: str, run_id: str, out_dir: Path, status: str) -> None:
    _write_latest_index_impl(
        task_id=task_id,
        run_id=run_id,
        out_dir=out_dir,
        status=status,
        latest_index_path_fn=_pipeline_latest_index_path,
    )


def _allocate_out_dir(task_id: str, requested_run_id: str, *, force_new_run_id: bool, allow_overwrite: bool) -> tuple[str, Path]:
    return _allocate_out_dir_impl(
        task_id,
        requested_run_id,
        force_new_run_id=force_new_run_id,
        allow_overwrite=allow_overwrite,
        run_dir_fn=_pipeline_run_dir,
    )


_refresh_diff_stats = refresh_diff_stats


def _apply_runtime_policy(
    state: dict[str, Any],
    *,
    failure_threshold: int,
    resume_threshold: int,
    diff_lines_threshold: int,
    diff_categories_threshold: int,
) -> dict[str, Any]:
    return apply_context_refresh_policy(
        _refresh_diff_stats(state),
        failure_threshold=failure_threshold,
        resume_threshold=resume_threshold,
        diff_lines_threshold=diff_lines_threshold,
        diff_categories_threshold=diff_categories_threshold,
    )


def _append_step_event(
    *,
    out_dir: Path,
    task_id: str,
    run_id: str,
    delivery_profile: str,
    security_profile: str,
    step: dict[str, Any],
) -> None:
    _append_step_event_impl(
        out_dir=out_dir,
        task_id=task_id,
        run_id=run_id,
        delivery_profile=delivery_profile,
        security_profile=security_profile,
        step=step,
        append_run_event_fn=append_run_event,
    )


def _run_agent_review_post_hook(*, out_dir: Path, mode: str, marathon_state: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    return _run_agent_review_post_hook_impl(
        out_dir=out_dir,
        mode=mode,
        marathon_state=marathon_state,
        write_agent_review_fn=write_agent_review,
        apply_agent_review_policy_fn=apply_agent_review_policy,
    )


def _load_source_run(task_id: str, selector_run_id: str | None) -> tuple[Path, dict[str, Any], dict[str, Any] | None]:
    return _load_source_run_impl(
        task_id,
        selector_run_id,
        latest_index_path=_pipeline_latest_index_path(task_id),
        resolve_existing_out_dir_fn=resolve_existing_out_dir,
        load_existing_summary_fn=_load_existing_summary,
        load_marathon_state_fn=load_marathon_state,
    )


def main() -> int:
    args = build_parser().parse_args()
    task_id = _task_root_id(args.task_id)
    if not task_id:
        print("[sc-review-pipeline] ERROR: invalid --task-id")
        return 2
    if bool(args.allow_overwrite) and bool(args.force_new_run_id):
        print("[sc-review-pipeline] ERROR: --allow-overwrite and --force-new-run-id are mutually exclusive.")
        return 2
    if sum(bool(x) for x in (args.resume, args.abort, args.fork)) > 1:
        print("[sc-review-pipeline] ERROR: --resume, --abort, and --fork are mutually exclusive.")
        return 2

    delivery_profile = resolve_delivery_profile(args.delivery_profile)
    security_profile = str(args.security_profile or default_security_profile_for_delivery(delivery_profile)).strip().lower()
    acceptance_defaults = profile_acceptance_defaults(delivery_profile)
    llm_defaults = profile_llm_review_defaults(delivery_profile)
    agent_review_mode = _resolve_agent_review_mode(delivery_profile)
    try:
        triplet = resolve_triplet(task_id=task_id)
    except Exception:
        triplet = None
    llm_review_plan = resolve_llm_review_tier_plan(
        delivery_profile=delivery_profile,
        triplet=triplet,
        profile_defaults=llm_defaults,
    )
    llm_agents = str(args.llm_agents or llm_review_plan.get("agents") or llm_defaults.get("agents") or "all")
    llm_timeout_sec = int(args.llm_timeout_sec or llm_review_plan.get("timeout_sec") or llm_defaults.get("timeout_sec") or 900)
    llm_agent_timeout_sec = int(args.llm_agent_timeout_sec or llm_review_plan.get("agent_timeout_sec") or llm_defaults.get("agent_timeout_sec") or 300)
    llm_semantic_gate = str(args.llm_semantic_gate or llm_review_plan.get("semantic_gate") or llm_defaults.get("semantic_gate") or "require")
    llm_strict = bool(args.llm_strict) or bool(llm_review_plan.get("strict", False))
    llm_execution_context = {
        **llm_review_plan,
        "agents": llm_agents,
        "timeout_sec": llm_timeout_sec,
        "agent_timeout_sec": llm_agent_timeout_sec,
        "semantic_gate": llm_semantic_gate,
        "strict": llm_strict,
        "task_id": task_id,
    }
    requested_run_id = str(args.run_id or "").strip() or uuid.uuid4().hex
    run_id = requested_run_id

    try:
        if args.resume or args.abort:
            out_dir, summary, marathon_state = _load_source_run(task_id, (args.run_id or "").strip() or None)
            run_id = str(summary.get("run_id") or "").strip() or run_id
            requested_run_id = str(summary.get("requested_run_id") or run_id).strip() or run_id
        elif args.fork:
            source_out_dir, source_summary, source_state = _load_source_run(task_id, (args.fork_from_run_id or "").strip() or None)
            run_id, out_dir = _allocate_out_dir(
                task_id,
                requested_run_id,
                force_new_run_id=bool(args.force_new_run_id),
                allow_overwrite=bool(args.allow_overwrite),
            )
            summary, marathon_state = build_forked_state(
                source_out_dir=source_out_dir,
                source_summary=source_summary,
                source_state=source_state,
                new_run_id=run_id,
                requested_run_id=requested_run_id,
                max_step_retries=args.max_step_retries,
                max_wall_time_sec=args.max_wall_time_sec,
            )
        else:
            run_id, out_dir = _allocate_out_dir(
                task_id,
                requested_run_id,
                force_new_run_id=bool(args.force_new_run_id),
                allow_overwrite=bool(args.allow_overwrite),
            )
            summary = {
                "cmd": "sc-review-pipeline",
                "task_id": task_id,
                "requested_run_id": requested_run_id,
                "run_id": run_id,
                "allow_overwrite": bool(args.allow_overwrite),
                "force_new_run_id": bool(args.force_new_run_id),
                "status": "ok",
                "steps": [],
            }
            marathon_state = None
    except FileExistsError:
        print("[sc-review-pipeline] ERROR: output directory already exists for this task/run_id. Use a new --run-id, --force-new-run-id, or pass --allow-overwrite.")
        return 2
    except RuntimeError as exc:
        print(f"[sc-review-pipeline] ERROR: {exc}")
        return 2
    except FileNotFoundError:
        print("[sc-review-pipeline] ERROR: no existing pipeline run found for resume/abort/fork.")
        return 2

    _prepare_env(run_id, delivery_profile, security_profile)
    write_text(out_dir / "run_id.txt", run_id + "\n")
    marathon_state = marathon_state or load_marathon_state(out_dir) or build_initial_state(
        task_id=task_id,
        run_id=run_id,
        requested_run_id=requested_run_id,
        max_step_retries=args.max_step_retries,
        max_wall_time_sec=args.max_wall_time_sec,
        summary=summary,
    )
    write_harness_capabilities(
        out_dir=out_dir,
        cmd="sc-review-pipeline",
        task_id=task_id,
        run_id=run_id,
        delivery_profile=delivery_profile,
        security_profile=security_profile,
    )
    if args.abort:
        append_run_event(
            out_dir=out_dir,
            event="run_aborted",
            task_id=task_id,
            run_id=run_id,
            delivery_profile=delivery_profile,
            security_profile=security_profile,
            status="aborted",
            details={"reason": "operator_requested"},
        )
        save_marathon_state(out_dir, mark_aborted(marathon_state, reason="operator_requested"))
        _write_latest_index(task_id=task_id, run_id=run_id, out_dir=out_dir, status="aborted")
        print(f"SC_REVIEW_PIPELINE status=aborted out={out_dir}")
        return 0
    if args.resume:
        if str(marathon_state.get("status") or "").strip().lower() == "aborted":
            print("[sc-review-pipeline] ERROR: the selected run is aborted and cannot be resumed.")
            return 2
        marathon_state = resume_state(marathon_state, max_step_retries=args.max_step_retries, max_wall_time_sec=args.max_wall_time_sec)

    append_run_event(
        out_dir=out_dir,
        event="run_resumed" if args.resume else "run_forked" if args.fork else "run_started",
        task_id=task_id,
        run_id=run_id,
        delivery_profile=delivery_profile,
        security_profile=security_profile,
        status=str(summary.get("status") or "ok"),
        details={"requested_run_id": requested_run_id, "mode": "resume" if args.resume else "fork" if args.fork else "start"},
    )
    marathon_state = _apply_runtime_policy(
        marathon_state,
        failure_threshold=args.context_refresh_after_failures,
        resume_threshold=args.context_refresh_after_resumes,
        diff_lines_threshold=args.context_refresh_after_diff_lines,
        diff_categories_threshold=args.context_refresh_after_diff_categories,
    )

    session = PipelineSession(
        args=args,
        out_dir=out_dir,
        task_id=task_id,
        run_id=run_id,
        requested_run_id=requested_run_id,
        delivery_profile=delivery_profile,
        security_profile=security_profile,
        llm_review_context=llm_execution_context,
        summary=summary,
        marathon_state=marathon_state,
        agent_review_mode=agent_review_mode,
        schema_error_log=out_dir / "summary-schema-validation-error.log",
        apply_runtime_policy=lambda state: _apply_runtime_policy(
            state,
            failure_threshold=args.context_refresh_after_failures,
            resume_threshold=args.context_refresh_after_resumes,
            diff_lines_threshold=args.context_refresh_after_diff_lines,
            diff_categories_threshold=args.context_refresh_after_diff_categories,
        ),
        apply_agent_review_signal=apply_agent_review_signal,
        validate_pipeline_summary=validate_pipeline_summary,
        summary_schema_error=SummarySchemaError,
        write_harness_capabilities=write_harness_capabilities,
        write_json=write_json,
        write_text=write_text,
        save_marathon_state=save_marathon_state,
        build_repair_guide=build_repair_guide,
        sync_soft_approval_sidecars=sync_soft_approval_sidecars,
        build_execution_context=build_execution_context,
        render_repair_guide_markdown=render_repair_guide_markdown,
        append_run_event=append_run_event,
        write_latest_index=_write_latest_index,
        record_step_result=record_step_result,
        upsert_step=_upsert_step,
        append_step_event=_append_step_event,
        run_step=_run_step,
        can_retry_failed_step=can_retry_failed_step,
        step_is_already_complete=step_is_already_complete,
        wall_time_exceeded=wall_time_exceeded,
        mark_wall_time_exceeded=mark_wall_time_exceeded,
        cap_step_timeout=cap_step_timeout,
        run_agent_review_post_hook=_run_agent_review_post_hook,
    )
    if not session.persist():
        return 2

    steps = build_pipeline_steps(
        args=args,
        task_id=task_id,
        run_id=run_id,
        delivery_profile=delivery_profile,
        security_profile=security_profile,
        acceptance_defaults=acceptance_defaults,
        llm_agents=llm_agents,
        llm_timeout_sec=llm_timeout_sec,
        llm_agent_timeout_sec=llm_agent_timeout_sec,
        llm_semantic_gate=llm_semantic_gate,
        llm_strict=llm_strict,
    )
    step_rc = session.execute_steps(steps, resume_or_fork=bool(args.resume or args.fork))
    if step_rc is not None:
        return step_rc
    final_rc = session.finish()
    try:
        write_low_priority_debt_artifacts(
            out_dir=out_dir,
            summary=session.summary,
            task_id=task_id,
            run_id=run_id,
            delivery_profile=delivery_profile,
        )
    except Exception as exc:
        write_text(out_dir / "technical-debt-sync.log", f"technical debt sync skipped: {exc}\n")
        print(f"[sc-review-pipeline] WARN: technical debt sync skipped: {exc}")
    print(f"SC_REVIEW_PIPELINE status={session.summary['status']} out={out_dir}")
    return final_rc


if __name__ == "__main__":
    raise SystemExit(main())
