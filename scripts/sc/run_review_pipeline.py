#!/usr/bin/env python3
"""
Run a deterministic local review pipeline with one shared run_id:
1) sc-test
2) sc-acceptance-check
3) sc-llm-review
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from agent_to_agent_review import write_agent_review
from _agent_review_policy import apply_agent_review_policy, apply_agent_review_signal
from _delivery_profile import (
    default_security_profile_for_delivery,
    profile_acceptance_defaults,
    profile_review_pipeline_defaults,
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
from _pipeline_plan import build_acceptance_command, build_pipeline_steps
from _pipeline_session import PipelineSession
from _pipeline_support import (
    load_existing_summary as _load_existing_summary,
    resolve_agent_review_mode as _resolve_agent_review_mode,
    run_step as _run_step,
    upsert_step as _upsert_step,
)
from _llm_review_cli import resolve_agents
from _change_scope import classify_change_scope_between_snapshots
from _repair_guidance import build_execution_context, build_repair_guide, render_repair_guide_markdown
from _taskmaster import resolve_triplet
from _technical_debt import write_low_priority_debt_artifacts
from _llm_review_tier import resolve_llm_review_tier_plan
from _summary_schema import SummarySchemaError, validate_pipeline_summary
from _util import repo_root, write_json, write_text
from _active_task_sidecar import write_active_task_sidecar as _write_active_task_sidecar_impl


def current_git_fingerprint() -> dict[str, Any]:
    from _util import repo_root, run_cmd

    rc_head, out_head = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_root(), timeout_sec=30)
    rc_status, out_status = run_cmd(["git", "status", "--short"], cwd=repo_root(), timeout_sec=30)
    return {
        "head": out_head.strip() if rc_head == 0 else "",
        "status_short": sorted([line.rstrip() for line in out_status.splitlines() if line.strip()]) if rc_status == 0 else [],
    }


def _normalize_cmd_for_reuse(cmd: list[str]) -> list[str]:
    out: list[str] = []
    idx = 0
    while idx < len(cmd):
        token = str(cmd[idx])
        if token == "--run-id":
            idx += 2
            continue
        out.append(token)
        idx += 1
    return out


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _snapshot_directory(*, source_dir: Path, target_dir: Path) -> tuple[str, str]:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)
    summary_path = target_dir / "summary.json"
    return str(target_dir), str(summary_path) if summary_path.exists() else ""


def _find_reusable_sc_test_step(
    *,
    out_dir: Path,
    task_id: str,
    delivery_profile: str,
    security_profile: str,
    planned_cmd: list[str],
    git_fingerprint: dict[str, Any],
) -> dict[str, Any] | None:
    logs_root = repo_root() / "logs" / "ci"
    if not logs_root.exists():
        return None
    current_head = str(git_fingerprint.get("head") or "").strip()
    current_status = sorted([str(line).rstrip() for line in (git_fingerprint.get("status_short") or []) if str(line).strip()])
    normalized_planned_cmd = _normalize_cmd_for_reuse(planned_cmd)
    candidates = sorted(
        [item for item in logs_root.rglob(f"sc-review-pipeline-task-{task_id}-*") if item.is_dir()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        summary_path = candidate / "summary.json"
        execution_context_path = candidate / "execution-context.json"
        if not summary_path.exists() or not execution_context_path.exists():
            continue
        summary = _read_json(summary_path)
        execution_context = _read_json(execution_context_path)
        if not summary or not execution_context:
            continue
        if str(execution_context.get("delivery_profile") or "").strip().lower() != delivery_profile:
            continue
        if str(execution_context.get("security_profile") or "").strip().lower() != security_profile:
            continue
        git_info = execution_context.get("git") if isinstance(execution_context.get("git"), dict) else {}
        previous_status = sorted([str(line).rstrip() for line in (git_info.get("status_short") or []) if str(line).strip()])
        exact_snapshot_match = str(git_info.get("head") or "").strip() == current_head and previous_status == current_status
        change_scope = (
            {
                "sc_test_reuse_allowed": True,
                "deterministic_strategy": "reuse-latest",
                "changed_paths": [],
                "unsafe_paths": [],
            }
            if exact_snapshot_match
            else classify_change_scope_between_snapshots(previous_git=git_info, current_git=git_fingerprint)
        )
        if not exact_snapshot_match and str(delivery_profile or "").strip().lower() == "standard":
            continue
        if not bool(change_scope.get("sc_test_reuse_allowed")):
            continue
        steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
        sc_test_step = next((step for step in steps if isinstance(step, dict) and str(step.get("name") or "") == "sc-test"), None)
        if not isinstance(sc_test_step, dict):
            continue
        if str(sc_test_step.get("status") or "").strip().lower() != "ok":
            continue
        if _normalize_cmd_for_reuse(list(sc_test_step.get("cmd") or [])) != normalized_planned_cmd:
            continue
        source_dir_raw = str(sc_test_step.get("reported_out_dir") or "").strip()
        source_summary_raw = str(sc_test_step.get("summary_file") or "").strip()
        if source_dir_raw and Path(source_dir_raw).is_dir():
            snapshot_dir, snapshot_summary = _snapshot_directory(
                source_dir=Path(source_dir_raw),
                target_dir=out_dir / "child-artifacts" / "sc-test",
            )
        elif source_summary_raw and Path(source_summary_raw).is_file():
            target_dir = out_dir / "child-artifacts" / "sc-test"
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(source_summary_raw), target_dir / "summary.json")
            snapshot_dir, snapshot_summary = str(target_dir), str(target_dir / "summary.json")
        else:
            continue
        log_path = out_dir / "sc-test.log"
        write_text(
            log_path,
            "\n".join(
                [
                    "[sc-review-pipeline] reused sc-test from matching git snapshot"
                    if exact_snapshot_match
                    else "[sc-review-pipeline] reused sc-test after semantic-only git delta",
                    f"source_run_dir={candidate}",
                    f"source_summary={summary_path}",
                    f"source_step_summary={source_summary_raw}",
                    f"change_scope_strategy={str(change_scope.get('deterministic_strategy') or '').strip()}",
                    f"changed_paths={json.dumps(change_scope.get('changed_paths') or [], ensure_ascii=False)}",
                    f"SC_TEST status=ok out={snapshot_dir}",
                ]
            )
            + "\n",
        )
        return {
            "name": "sc-test",
            "cmd": planned_cmd,
            "rc": 0,
            "status": "ok",
            "log": str(log_path),
            "reported_out_dir": snapshot_dir,
            "summary_file": snapshot_summary,
        }
    return None


def _format_agent_timeout_overrides(overrides: dict[str, int]) -> str:
    return ",".join(f"{agent}={int(seconds)}" for agent, seconds in overrides.items() if int(seconds) > 0)


def _derive_llm_agent_timeout_overrides(
    *,
    current_out_dir: Path,
    task_id: str,
    delivery_profile: str,
    security_profile: str,
    llm_agents: str,
    llm_semantic_gate: str,
    llm_timeout_sec: int,
    llm_agent_timeout_sec: int,
) -> dict[str, int]:
    logs_root = repo_root() / "logs" / "ci"
    if not logs_root.exists():
        return {}
    planned_agents = resolve_agents(llm_agents, llm_semantic_gate)
    if not planned_agents:
        return {}
    escalated_timeout = min(int(llm_timeout_sec), max(int(llm_agent_timeout_sec) * 2, int(llm_agent_timeout_sec) + 120))
    if escalated_timeout <= int(llm_agent_timeout_sec):
        return {}
    planned_agent_set = set(planned_agents)
    current_out_dir_resolved = current_out_dir.resolve()
    candidates = sorted(
        [item for item in logs_root.rglob(f"sc-review-pipeline-task-{task_id}-*") if item.is_dir()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        if candidate.resolve() == current_out_dir_resolved:
            continue
        summary_path = candidate / "summary.json"
        execution_context_path = candidate / "execution-context.json"
        if not summary_path.exists() or not execution_context_path.exists():
            continue
        summary = _read_json(summary_path)
        execution_context = _read_json(execution_context_path)
        if not summary or not execution_context:
            continue
        if str(execution_context.get("delivery_profile") or "").strip().lower() != delivery_profile:
            continue
        if str(execution_context.get("security_profile") or "").strip().lower() != security_profile:
            continue
        steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
        llm_step = next((step for step in steps if isinstance(step, dict) and str(step.get("name") or "") == "sc-llm-review"), None)
        if not isinstance(llm_step, dict):
            continue
        llm_summary_raw = str(llm_step.get("summary_file") or "").strip()
        if not llm_summary_raw:
            continue
        llm_summary_path = Path(llm_summary_raw)
        if not llm_summary_path.is_absolute():
            llm_summary_path = (repo_root() / llm_summary_path).resolve()
        if not llm_summary_path.exists():
            continue
        llm_summary = _read_json(llm_summary_path)
        timed_out_agents: set[str] = set()
        for result in llm_summary.get("results", []):
            if not isinstance(result, dict):
                continue
            agent = str(result.get("agent") or "").strip()
            if not agent or agent not in planned_agent_set:
                continue
            if int(result.get("rc") or 0) == 124:
                timed_out_agents.add(agent)
        if timed_out_agents:
            return {agent: escalated_timeout for agent in planned_agents if agent in timed_out_agents}
    return {}


def _run_cli_capability_preflight(*, out_dir: Path, step_name: str, cmd: list[str], timeout_sec: int = 120) -> dict[str, Any] | None:
    if len(cmd) < 4:
        return None
    script = str(cmd[3]).replace("\\", "/")
    if script not in {"scripts/sc/test.py", "scripts/sc/acceptance_check.py", "scripts/sc/llm_review.py"}:
        return None
    from _util import repo_root, run_cmd

    preflight_cmd = [*cmd, "--self-check"]
    rc, out = run_cmd(preflight_cmd, cwd=repo_root(), timeout_sec=timeout_sec)
    log_path = out_dir / f"cli-preflight-{step_name}.log"
    write_text(log_path, out)
    if rc == 0:
        return None
    return {
        "name": step_name,
        "cmd": preflight_cmd,
        "rc": rc,
        "status": "fail",
        "log": str(log_path),
        "reported_out_dir": "",
        "summary_file": "",
    }


def _latest_tdd_stage_summary(*, task_id: str, stage: str) -> tuple[Path | None, dict[str, Any]]:
    logs_root = repo_root() / "logs" / "ci"
    if not logs_root.exists():
        return None, {}
    candidates = sorted(logs_root.glob("*/sc-build-tdd/summary.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    for candidate in candidates:
        payload = _read_json(candidate)
        task_meta = payload.get("task") if isinstance(payload.get("task"), dict) else {}
        payload_task_id = str(task_meta.get("task_id") or payload.get("task_id") or "").strip()
        if payload_task_id != str(task_id).strip():
            continue
        if str(payload.get("stage") or "").strip() != stage:
            continue
        return candidate, payload
    return None, {}


def run_review_prerequisite_check(*, out_dir: Path, task_id: str) -> dict[str, Any] | None:
    summary_path, payload = _latest_tdd_stage_summary(task_id=task_id, stage="refactor")
    if summary_path is not None and str(payload.get("status") or "").strip() == "ok":
        return None
    log_path = out_dir / "sc-build-tdd-refactor-preflight.log"
    reason = "missing_refactor_summary" if summary_path is None else "refactor_stage_not_ok"
    lines = [
        f"SC_REVIEW_PREREQUISITE status=fail reason={reason}",
        f"summary_path: {summary_path}" if summary_path is not None else "summary_path: (missing)",
    ]
    if summary_path is not None:
        lines.append(f"status: {str(payload.get('status') or '').strip() or '(missing)'}")
    lines.append("error: latest refactor-stage sc-build-tdd summary must exist and be ok before running review pipeline")
    write_text(log_path, "\n".join(lines) + "\n")
    return {
        "name": "sc-build-tdd-refactor-preflight",
        "cmd": ["internal:review_prerequisite_check"],
        "rc": 1,
        "status": "fail",
        "log": str(log_path),
        "reported_out_dir": "",
        "summary_file": str(summary_path) if summary_path is not None else "",
    }


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


def _write_active_task_sidecar(*, task_id: str, run_id: str, out_dir: Path, status: str) -> None:
    _write_active_task_sidecar_impl(
        task_id=task_id,
        run_id=run_id,
        out_dir=out_dir,
        status=status,
        latest_json_path=_pipeline_latest_index_path(task_id),
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


def _run_acceptance_preflight(
    *,
    session: PipelineSession,
    args: Any,
    task_id: str,
    run_id: str,
    delivery_profile: str,
    security_profile: str,
    acceptance_defaults: dict[str, Any],
) -> int | None:
    if bool(args.dry_run) or bool(args.resume) or bool(args.fork):
        return None
    if bool(args.skip_test) or bool(args.skip_acceptance):
        return None

    cmd = build_acceptance_command(
        args=args,
        task_id=task_id,
        run_id=run_id,
        delivery_profile=delivery_profile,
        security_profile=security_profile,
        acceptance_defaults=acceptance_defaults,
        preflight=True,
    )
    preflight_step = session.run_step(
        out_dir=session.out_dir,
        name="sc-acceptance-preflight",
        cmd=cmd,
        timeout_sec=600,
    )
    if preflight_step.get("status") == "ok":
        session.append_run_event(
            out_dir=session.out_dir,
            event="acceptance_preflight_completed",
            task_id=task_id,
            run_id=run_id,
            delivery_profile=delivery_profile,
            security_profile=security_profile,
            status="ok",
            details={
                "rc": preflight_step.get("rc"),
                "log": preflight_step.get("log"),
                "summary_file": preflight_step.get("summary_file"),
                "reported_out_dir": preflight_step.get("reported_out_dir"),
            },
        )
        return None

    preflight_step["name"] = "sc-acceptance-check"
    if not session.add_step(preflight_step):
        if session.schema_error_log.exists():
            return 2
    return session.finish()


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
    pipeline_defaults = profile_review_pipeline_defaults(delivery_profile)
    llm_defaults = profile_llm_review_defaults(delivery_profile)
    agent_review_mode = _resolve_agent_review_mode(delivery_profile)
    max_step_retries = int(args.max_step_retries if args.max_step_retries is not None else pipeline_defaults.get("max_step_retries", 0))
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
    llm_diff_mode = str(args.llm_diff_mode or llm_review_plan.get("diff_mode") or llm_defaults.get("diff_mode") or "full")
    llm_execution_context = {
        **llm_review_plan,
        "agents": llm_agents,
        "timeout_sec": llm_timeout_sec,
        "agent_timeout_sec": llm_agent_timeout_sec,
        "semantic_gate": llm_semantic_gate,
        "strict": llm_strict,
        "diff_mode": llm_diff_mode,
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
                max_step_retries=max_step_retries,
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
        max_step_retries=max_step_retries,
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
    llm_agent_timeout_overrides = _derive_llm_agent_timeout_overrides(
        current_out_dir=out_dir,
        task_id=task_id,
        delivery_profile=delivery_profile,
        security_profile=security_profile,
        llm_agents=llm_agents,
        llm_semantic_gate=llm_semantic_gate,
        llm_timeout_sec=llm_timeout_sec,
        llm_agent_timeout_sec=llm_agent_timeout_sec,
    )
    llm_agent_timeouts = _format_agent_timeout_overrides(llm_agent_timeout_overrides)
    if llm_agent_timeout_overrides:
        llm_execution_context["agent_timeout_overrides"] = llm_agent_timeout_overrides
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
        _write_active_task_sidecar(task_id=task_id, run_id=run_id, out_dir=out_dir, status="aborted")
        print(f"SC_REVIEW_PIPELINE status=aborted out={out_dir}")
        return 0
    if args.resume:
        if str(marathon_state.get("status") or "").strip().lower() == "aborted":
            print("[sc-review-pipeline] ERROR: the selected run is aborted and cannot be resumed.")
            return 2
        marathon_state = resume_state(marathon_state, max_step_retries=max_step_retries, max_wall_time_sec=args.max_wall_time_sec)

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
        write_active_task_sidecar=_write_active_task_sidecar,
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
        triplet=triplet,
        llm_agents=llm_agents,
        llm_timeout_sec=llm_timeout_sec,
        llm_agent_timeout_sec=llm_agent_timeout_sec,
        llm_agent_timeouts=llm_agent_timeouts,
        llm_semantic_gate=llm_semantic_gate,
        llm_strict=llm_strict,
        llm_diff_mode=llm_diff_mode,
    )
    reused_sc_test_step: dict[str, Any] | None = None
    if not bool(args.resume or args.fork or args.dry_run or args.skip_test):
        reused_sc_test_step = _find_reusable_sc_test_step(
            out_dir=out_dir,
            task_id=task_id,
            delivery_profile=delivery_profile,
            security_profile=security_profile,
            planned_cmd=list(steps[0][1]),
            git_fingerprint=current_git_fingerprint(),
        )
        if reused_sc_test_step is not None:
            os.environ["SC_TEST_REUSE_SUMMARY"] = str(reused_sc_test_step.get("summary_file") or "")
            if not session.add_step(reused_sc_test_step):
                return 2
    else:
        os.environ.pop("SC_TEST_REUSE_SUMMARY", None)

    if not bool(args.dry_run or args.resume or args.fork):
        review_preflight_failed = run_review_prerequisite_check(out_dir=out_dir, task_id=task_id)
        if review_preflight_failed is not None:
            if not session.add_step(review_preflight_failed):
                return 2 if session.schema_error_log.exists() else 1
            print(f"SC_REVIEW_PIPELINE status={session.summary['status']} out={out_dir}")
            return session.finish()
        for step_name, cmd, _timeout_sec, skipped in steps:
            if skipped:
                continue
            if step_name == "sc-test" and reused_sc_test_step is not None:
                continue
            preflight_failed = _run_cli_capability_preflight(out_dir=out_dir, step_name=step_name, cmd=cmd)
            if preflight_failed is not None:
                if not session.add_step(preflight_failed):
                    return 2 if session.schema_error_log.exists() else 1
                print(f"SC_REVIEW_PIPELINE status={session.summary['status']} out={out_dir}")
                return session.finish()
    preflight_rc = _run_acceptance_preflight(
        session=session,
        args=args,
        task_id=task_id,
        run_id=run_id,
        delivery_profile=delivery_profile,
        security_profile=security_profile,
        acceptance_defaults=acceptance_defaults,
    )
    if preflight_rc is not None:
        print(f"SC_REVIEW_PIPELINE status={session.summary['status']} out={out_dir}")
        return preflight_rc
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
