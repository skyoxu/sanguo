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
import time
import uuid
from datetime import datetime, timezone
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
from _pipeline_helpers import derive_pipeline_run_type as _derive_pipeline_run_type_impl
from _pipeline_helpers import has_materialized_pipeline_steps as _has_materialized_pipeline_steps_impl
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
from _llm_review_cli import parse_agent_timeout_overrides, resolve_agents
from _change_scope import classify_change_scope_between_snapshots
from _repair_guidance import build_execution_context, build_repair_guide, render_repair_guide_markdown
from _risk_profile_floor import derive_delivery_profile_floor
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


_ACCEPTANCE_PRECHECK_STEP_GROUPS: dict[str, list[str]] = {
    "adr": ["adr-compliance"],
    "links": ["task-links-validate", "task-test-refs", "acceptance-refs", "acceptance-anchors"],
    "subtasks": ["subtasks-coverage"],
    "overlay": ["validate-task-overlays"],
    "contracts": ["validate-contracts"],
    "arch": ["architecture-boundary"],
    "build": ["dotnet-build-warnaserror"],
}


def _extract_acceptance_only_groups(cmd: list[str]) -> list[str]:
    for idx, token in enumerate(cmd):
        if str(token) == "--only" and idx + 1 < len(cmd):
            return [part.strip() for part in str(cmd[idx + 1]).split(",") if part.strip()]
    return []


def _acceptance_summary_covers_planned_groups(*, summary_path: Path | None, planned_cmd: list[str]) -> bool:
    planned_groups = _extract_acceptance_only_groups(planned_cmd)
    if not planned_groups:
        return False
    if summary_path is None or not summary_path.exists():
        return False
    payload = _read_json(summary_path)
    if str(payload.get("status") or "").strip().lower() != "ok":
        return False
    steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []
    step_map = {
        str(step.get("name") or "").strip(): step
        for step in steps
        if isinstance(step, dict) and str(step.get("name") or "").strip()
    }
    required_steps: list[str] = []
    for group in planned_groups:
        required_steps.extend(_ACCEPTANCE_PRECHECK_STEP_GROUPS.get(group) or [])
    for step_name in required_steps:
        step = step_map.get(step_name)
        if not isinstance(step, dict):
            return False
        if str(step.get("status") or "").strip().lower() != "ok":
            return False
        if int(step.get("rc") or 0) != 0:
            return False
    return True


REUSE_MODES = {
    "none",
    "full-clean-reuse",
    "deterministic-only-reuse",
    "sc-test-reuse",
    "mixed-reuse",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

DIRTY_WORKTREE_CHANGED_PATHS_CEILING = 20
DIRTY_WORKTREE_UNSAFE_PATHS_CEILING = 8
PROFILE_DRIFT_CHANGED_PATHS_CEILING = 8
PROFILE_DRIFT_UNSAFE_PATHS_CEILING = 1


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_execution_context(out_dir: Path) -> dict[str, Any]:
    return _read_json(out_dir / "execution-context.json")


def _normalize_profile_value(value: str | None) -> str:
    return str(value or "").strip().lower()


def _normalize_scope_paths(values: list[Any] | None) -> list[str]:
    normalized: list[str] = []
    for item in list(values or []):
        text = str(item or "").strip().replace("\\", "/")
        if text:
            normalized.append(text)
    return normalized


def _resolve_pipeline_profiles(
    *,
    requested_delivery_profile: str | None,
    requested_security_profile: str | None,
    source_execution_context: dict[str, Any] | None,
    inherit_from_source: bool,
    allow_profile_reselect: bool = False,
) -> tuple[str, str]:
    source_context = source_execution_context if isinstance(source_execution_context, dict) else {}
    source_delivery_profile = _normalize_profile_value(source_context.get("delivery_profile"))
    source_security_profile = _normalize_profile_value(source_context.get("security_profile"))
    explicit_delivery_profile = resolve_delivery_profile(requested_delivery_profile) if requested_delivery_profile else ""
    explicit_security_profile = _normalize_profile_value(requested_security_profile)

    profile_locked = bool(source_delivery_profile) and (inherit_from_source or not allow_profile_reselect)
    security_locked = bool(source_security_profile) and (inherit_from_source or not allow_profile_reselect)

    if profile_locked:
        if explicit_delivery_profile and explicit_delivery_profile != source_delivery_profile:
            raise RuntimeError(
                f"delivery profile mismatch: source run uses {source_delivery_profile}, explicit request uses {explicit_delivery_profile}."
            )
        delivery_profile = source_delivery_profile
    else:
        delivery_profile = resolve_delivery_profile(requested_delivery_profile)

    if security_locked:
        if explicit_security_profile and explicit_security_profile != source_security_profile:
            raise RuntimeError(
                f"security profile mismatch: source run uses {source_security_profile}, explicit request uses {explicit_security_profile}."
            )
        security_profile = source_security_profile
    else:
        security_profile = _normalize_profile_value(requested_security_profile or default_security_profile_for_delivery(delivery_profile))
    return delivery_profile, security_profile


def _derive_delivery_profile_floor(
    *,
    delivery_profile: str,
    security_profile: str,
    change_scope: dict[str, Any] | None,
    explicit_security_profile: bool,
) -> dict[str, Any]:
    return derive_delivery_profile_floor(
        delivery_profile=delivery_profile,
        security_profile=security_profile,
        change_scope=change_scope,
        explicit_security_profile=explicit_security_profile,
    )


def _derive_profile_floor_change_scope(
    *,
    source_execution_context: dict[str, Any] | None,
    current_git: dict[str, Any],
) -> dict[str, Any]:
    source_context = source_execution_context if isinstance(source_execution_context, dict) else {}
    previous_git = source_context.get("git") if isinstance(source_context.get("git"), dict) else None
    if not isinstance(previous_git, dict):
        return {}
    return classify_change_scope_between_snapshots(previous_git=previous_git, current_git=current_git)


def _load_latest_task_execution_context(task_id: str) -> dict[str, Any] | None:
    try:
        out_dir, _summary, _state = _load_source_run(task_id, None)
    except FileNotFoundError:
        return None
    except Exception:
        return None
    execution_context = _read_execution_context(out_dir)
    return execution_context if execution_context else None


def _detect_latest_profile_drift(
    *,
    current_out_dir: Path,
    task_id: str,
    delivery_profile: str,
    security_profile: str,
) -> dict[str, Any] | None:
    logs_root = repo_root() / "logs" / "ci"
    if not logs_root.exists():
        return None
    current_out_dir_resolved = current_out_dir.resolve()
    candidates = sorted(
        [item for item in logs_root.rglob(f"sc-review-pipeline-task-{task_id}-*") if item.is_dir()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        if candidate.resolve() == current_out_dir_resolved:
            continue
        execution_context = _read_execution_context(candidate)
        if not execution_context:
            continue
        previous_delivery_profile = _normalize_profile_value(execution_context.get("delivery_profile"))
        previous_security_profile = _normalize_profile_value(execution_context.get("security_profile"))
        if not previous_delivery_profile:
            continue
        if previous_delivery_profile == delivery_profile and previous_security_profile == security_profile:
            return None
        return {
            "kind": "profile_drift",
            "previous_run_id": str(execution_context.get("run_id") or "").strip(),
            "previous_out_dir": str(candidate),
            "previous_delivery_profile": previous_delivery_profile,
            "previous_security_profile": previous_security_profile,
            "current_delivery_profile": delivery_profile,
            "current_security_profile": security_profile,
        }
    return None


def _derive_change_scope_ceiling_guard(
    *,
    change_scope: dict[str, Any] | None,
    profile_drift: dict[str, Any] | None,
) -> dict[str, Any] | None:
    scope = change_scope if isinstance(change_scope, dict) else {}
    changed_paths = _normalize_scope_paths(list(scope.get("changed_paths") or []))
    unsafe_paths = _normalize_scope_paths(list(scope.get("unsafe_paths") or []))
    if not changed_paths and not unsafe_paths:
        return None
    deterministic_strategy = str(scope.get("deterministic_strategy") or "").strip()
    if deterministic_strategy == "reuse-latest" and not unsafe_paths:
        return None

    profile_drift_present = isinstance(profile_drift, dict) and bool(profile_drift)
    kind = ""
    if len(unsafe_paths) > DIRTY_WORKTREE_UNSAFE_PATHS_CEILING:
        kind = "dirty_worktree_unsafe_paths_ceiling"
    elif len(changed_paths) > DIRTY_WORKTREE_CHANGED_PATHS_CEILING:
        kind = "dirty_worktree_changed_paths_ceiling"
    elif profile_drift_present and (
        len(unsafe_paths) >= PROFILE_DRIFT_UNSAFE_PATHS_CEILING or len(changed_paths) > PROFILE_DRIFT_CHANGED_PATHS_CEILING
    ):
        kind = "profile_drift_change_scope_ceiling"
    if not kind:
        return None

    return {
        "kind": kind,
        "blocked": True,
        "recommended_path": "inspect",
        "deterministic_strategy": deterministic_strategy,
        "changed_paths_count": len(changed_paths),
        "unsafe_paths_count": len(unsafe_paths),
        "allow_override_flag": "--allow-large-change-scope-rerun",
        "changed_paths_sample": changed_paths[:5],
        "unsafe_paths_sample": unsafe_paths[:5],
        "profile_drift_present": profile_drift_present,
        "ceilings": {
            "changed_paths": DIRTY_WORKTREE_CHANGED_PATHS_CEILING,
            "unsafe_paths": DIRTY_WORKTREE_UNSAFE_PATHS_CEILING,
            "profile_drift_changed_paths": PROFILE_DRIFT_CHANGED_PATHS_CEILING,
            "profile_drift_unsafe_paths": PROFILE_DRIFT_UNSAFE_PATHS_CEILING,
        },
    }


def _derive_rerun_forbidden_payload(active_guard: dict[str, Any] | None) -> dict[str, Any] | None:
    guard = active_guard if isinstance(active_guard, dict) else {}
    if not bool(guard.get("blocked")):
        return None
    kind = str(guard.get("kind") or "").strip()
    if not kind:
        return None
    override_flag = str(guard.get("allow_override_flag") or "").strip()
    if not override_flag:
        if kind == "repeat_deterministic_failure":
            override_flag = "--allow-repeat-deterministic-failures"
        elif kind in {"dirty_worktree_unsafe_paths_ceiling", "dirty_worktree_changed_paths_ceiling", "profile_drift_change_scope_ceiling"}:
            override_flag = "--allow-large-change-scope-rerun"
        else:
            override_flag = "--allow-full-rerun"
    return {
        "blocked": True,
        "kind": kind,
        "recommended_path": str(guard.get("recommended_path") or "").strip(),
        "override_flag": override_flag,
    }


def _snapshot_directory(*, source_dir: Path, target_dir: Path) -> tuple[str, str]:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)
    summary_path = target_dir / "summary.json"
    return str(target_dir), str(summary_path) if summary_path.exists() else ""


def _snapshot_step_artifacts(*, step: dict[str, Any], out_dir: Path, step_name: str) -> tuple[str, str]:
    source_dir_raw = str(step.get("reported_out_dir") or "").strip()
    source_summary_raw = str(step.get("summary_file") or "").strip()
    target_dir = out_dir / "child-artifacts" / step_name
    if source_dir_raw and Path(source_dir_raw).is_dir():
        return _snapshot_directory(source_dir=Path(source_dir_raw), target_dir=target_dir)
    if source_summary_raw and Path(source_summary_raw).is_file():
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(source_summary_raw), target_dir / "summary.json")
        return str(target_dir), str(target_dir / "summary.json")
    return "", ""


def _normalize_llm_verdict(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"ok", "pass", "passed"}:
        return "OK"
    if raw in {"needs fix", "needs_fix", "need fix", "fail", "failed"}:
        return "Needs Fix"
    return "Unknown"


def _resolve_summary_path(raw_path: str) -> Path | None:
    raw_text = str(raw_path or "").strip()
    if not raw_text:
        return None
    candidate = Path(raw_text)
    if not candidate.is_absolute():
        candidate = (repo_root() / candidate).resolve()
    return candidate if candidate.exists() else None


def _llm_step_is_clean(step: dict[str, Any]) -> bool:
    if str(step.get("status") or "").strip().lower() != "ok":
        return False
    summary_path = _resolve_summary_path(str(step.get("summary_file") or "").strip())
    if summary_path is None:
        return False
    payload = _read_json(summary_path)
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    if not results:
        return False
    for row in results:
        if not isinstance(row, dict):
            return False
        status = str(row.get("status") or "").strip().lower()
        rc = int(row.get("rc") or 0)
        details = row.get("details") if isinstance(row.get("details"), dict) else {}
        verdict = _normalize_llm_verdict(str(details.get("verdict") or ""))
        if rc != 0 or status != "ok" or verdict != "OK":
            return False
    return True


def _build_step_map(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
    return {
        str(step.get("name") or "").strip(): step
        for step in steps
        if isinstance(step, dict) and str(step.get("name") or "").strip()
    }


def _normalize_failure_fragment(value: Any, *, limit: int = 160) -> str:
    text = " ".join(str(value or "").strip().split())
    return text[:limit]


def _derive_sc_test_failure_fingerprint_from_payload(payload: dict[str, Any]) -> str:
    steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []
    for step in steps:
        if not isinstance(step, dict):
            continue
        if str(step.get("status") or "").strip().lower() != "fail":
            continue
        parts = [
            "sc-test",
            _normalize_failure_fragment(step.get("name")),
            str(int(step.get("rc") or 0)),
            _normalize_failure_fragment(step.get("reason")),
            _normalize_failure_fragment(step.get("error")),
        ]
        while parts and not parts[-1]:
            parts.pop()
        return "|".join(parts)
    status = _normalize_failure_fragment(payload.get("status"))
    return f"sc-test|summary|{status}" if status else ""


def _resolve_sc_test_failure_fingerprint(step: dict[str, Any]) -> str:
    summary_path = _resolve_summary_path(str(step.get("summary_file") or "").strip())
    if summary_path is not None:
        payload = _read_json(summary_path)
        fingerprint = _derive_sc_test_failure_fingerprint_from_payload(payload)
        if fingerprint:
            return fingerprint
    parts = [
        "sc-test",
        _normalize_failure_fragment(step.get("name")),
        str(int(step.get("rc") or 0)),
        _normalize_failure_fragment(step.get("status")),
    ]
    return "|".join(parts)


def _find_recent_deterministic_green_llm_not_clean_run(
    *,
    current_out_dir: Path,
    task_id: str,
    delivery_profile: str,
    security_profile: str,
    git_fingerprint: dict[str, Any],
) -> dict[str, Any] | None:
    logs_root = repo_root() / "logs" / "ci"
    if not logs_root.exists():
        return None
    current_head = str(git_fingerprint.get("head") or "").strip()
    current_status = sorted([str(line).rstrip() for line in (git_fingerprint.get("status_short") or []) if str(line).strip()])
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
        if _normalize_profile_value(execution_context.get("delivery_profile")) != delivery_profile:
            continue
        if _normalize_profile_value(execution_context.get("security_profile")) != security_profile:
            continue
        git_info = execution_context.get("git") if isinstance(execution_context.get("git"), dict) else {}
        previous_status = sorted([str(line).rstrip() for line in (git_info.get("status_short") or []) if str(line).strip()])
        exact_snapshot_match = str(git_info.get("head") or "").strip() == current_head and previous_status == current_status
        change_scope = (
            {
                "deterministic_strategy": "reuse-latest",
                "changed_paths": [],
                "unsafe_paths": [],
            }
            if exact_snapshot_match
            else classify_change_scope_between_snapshots(previous_git=git_info, current_git=git_fingerprint)
        )
        if not exact_snapshot_match and str(delivery_profile or "").strip().lower() == "standard":
            continue
        if not exact_snapshot_match and str(change_scope.get("deterministic_strategy") or "").strip() != "reuse-latest":
            continue
        step_map = _build_step_map(summary)
        if str((step_map.get("sc-test") or {}).get("status") or "").strip().lower() != "ok":
            continue
        if str((step_map.get("sc-acceptance-check") or {}).get("status") or "").strip().lower() != "ok":
            continue
        llm_step = step_map.get("sc-llm-review")
        if not isinstance(llm_step, dict):
            continue
        if str(llm_step.get("status") or "").strip().lower() == "ok" and _llm_step_is_clean(llm_step):
            continue
        return {
            "kind": "deterministic_green_llm_not_clean",
            "blocked": True,
            "recommended_path": "llm-only",
            "source_run_id": str(execution_context.get("run_id") or "").strip(),
            "source_out_dir": str(candidate),
            "source_summary_path": str(summary_path),
            "exact_git_match": bool(exact_snapshot_match),
            "change_scope": change_scope,
            "llm_step_status": str(llm_step.get("status") or "").strip().lower(),
        }
    return None


def _find_repeated_deterministic_failure_guard(
    *,
    current_out_dir: Path,
    task_id: str,
    delivery_profile: str,
    security_profile: str,
) -> dict[str, Any] | None:
    logs_root = repo_root() / "logs" / "ci"
    if not logs_root.exists():
        return None
    current_out_dir_resolved = current_out_dir.resolve()
    candidates = sorted(
        [item for item in logs_root.rglob(f"sc-review-pipeline-task-{task_id}-*") if item.is_dir()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    matches: list[dict[str, Any]] = []
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
        if _normalize_profile_value(execution_context.get("delivery_profile")) != delivery_profile:
            continue
        if _normalize_profile_value(execution_context.get("security_profile")) != security_profile:
            continue
        sc_test_step = _build_step_map(summary).get("sc-test")
        if not isinstance(sc_test_step, dict):
            continue
        if str(sc_test_step.get("status") or "").strip().lower() != "fail":
            continue
        fingerprint = _resolve_sc_test_failure_fingerprint(sc_test_step)
        if not fingerprint:
            continue
        matches.append(
            {
                "run_id": str(execution_context.get("run_id") or "").strip(),
                "out_dir": str(candidate),
                "summary_path": str(summary_path),
                "fingerprint": fingerprint,
            }
        )
        if len(matches) >= 2:
            break
    if len(matches) < 2:
        return None
    if str(matches[0].get("fingerprint") or "") != str(matches[1].get("fingerprint") or ""):
        return None
    return {
        "kind": "repeat_deterministic_failure",
        "blocked": True,
        "recommended_path": "fix-before-rerun",
        "fingerprint": str(matches[0].get("fingerprint") or ""),
        "recent_runs": matches,
    }


def _derive_summary_reason(summary: dict[str, Any]) -> str:
    explicit_reason = str(summary.get("reason") or "").strip()
    if explicit_reason.startswith("rerun_blocked:"):
        return explicit_reason
    status = str(summary.get("status") or "").strip().lower()
    run_type = _derive_pipeline_run_type(summary)
    if run_type == "planned-only" and str(summary.get("finished_at_utc") or "").strip():
        return "planned_only_incomplete"
    steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
    failed_step = next(
        (
            str(step.get("name") or "").strip()
            for step in steps
            if isinstance(step, dict) and str(step.get("status") or "").strip().lower() == "fail"
        ),
        "",
    )
    if status == "fail":
        return f"step_failed:{failed_step}" if failed_step else "pipeline_failed"
    if any(isinstance(step, dict) and str(step.get("status") or "").strip().lower() == "planned" for step in steps):
        return "in_progress"
    return "pipeline_clean"


def _set_reuse_mode(summary: dict[str, Any], mode: str) -> None:
    current = str(summary.get("reuse_mode") or "none").strip().lower() or "none"
    next_mode = str(mode or "").strip().lower()
    if next_mode not in REUSE_MODES:
        next_mode = "none"
    if current == "none":
        summary["reuse_mode"] = next_mode
        return
    if current == next_mode:
        summary["reuse_mode"] = current
        return
    summary["reuse_mode"] = "mixed-reuse"


def _refresh_summary_meta(summary: dict[str, Any], *, script_start_monotonic: float) -> None:
    if not str(summary.get("started_at_utc") or "").strip():
        summary["started_at_utc"] = _utc_now_iso()
    run_type = _derive_pipeline_run_type(summary)
    summary["run_type"] = run_type
    if run_type == "planned-only" and str(summary.get("finished_at_utc") or "").strip():
        summary["status"] = "fail"
    summary["elapsed_sec"] = int(max(0.0, time.monotonic() - script_start_monotonic))
    summary["reason"] = _derive_summary_reason(summary)
    current_reuse = str(summary.get("reuse_mode") or "none").strip().lower() or "none"
    summary["reuse_mode"] = current_reuse if current_reuse in REUSE_MODES else "none"


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


def _find_reusable_clean_pipeline_steps(
    *,
    out_dir: Path,
    task_id: str,
    delivery_profile: str,
    security_profile: str,
    planned_steps: list[tuple[str, list[str], int, bool]],
    git_fingerprint: dict[str, Any],
) -> list[dict[str, Any]] | None:
    logs_root = repo_root() / "logs" / "ci"
    if not logs_root.exists():
        return None
    current_head = str(git_fingerprint.get("head") or "").strip()
    current_status = sorted([str(line).rstrip() for line in (git_fingerprint.get("status_short") or []) if str(line).strip()])
    normalized_planned = {
        step_name: _normalize_cmd_for_reuse(cmd)
        for step_name, cmd, _timeout_sec, skipped in planned_steps
        if not skipped
    }
    if not normalized_planned:
        return None
    candidates = sorted(
        [item for item in logs_root.rglob(f"sc-review-pipeline-task-{task_id}-*") if item.is_dir()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        if candidate.resolve() == out_dir.resolve():
            continue
        summary_path = candidate / "summary.json"
        execution_context_path = candidate / "execution-context.json"
        if not summary_path.exists() or not execution_context_path.exists():
            continue
        summary = _read_json(summary_path)
        execution_context = _read_json(execution_context_path)
        if not summary or not execution_context:
            continue
        if str(summary.get("status") or "").strip().lower() != "ok":
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
                "deterministic_strategy": "reuse-latest",
                "changed_paths": [],
                "unsafe_paths": [],
            }
            if exact_snapshot_match
            else classify_change_scope_between_snapshots(previous_git=git_info, current_git=git_fingerprint)
        )
        if not exact_snapshot_match and str(change_scope.get("deterministic_strategy") or "").strip() != "reuse-latest":
            continue
        steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
        step_map = {
            str(step.get("name") or "").strip(): step
            for step in steps
            if isinstance(step, dict) and str(step.get("name") or "").strip()
        }
        llm_step = step_map.get("sc-llm-review")
        if not isinstance(llm_step, dict) or not _llm_step_is_clean(llm_step):
            continue
        reused_steps: list[dict[str, Any]] = []
        for step_name, planned_cmd in normalized_planned.items():
            source_step = step_map.get(step_name)
            if not isinstance(source_step, dict):
                reused_steps = []
                break
            if str(source_step.get("status") or "").strip().lower() != "ok":
                reused_steps = []
                break
            if _normalize_cmd_for_reuse(list(source_step.get("cmd") or [])) != planned_cmd:
                reused_steps = []
                break
            snapshot_dir, snapshot_summary = _snapshot_step_artifacts(step=source_step, out_dir=out_dir, step_name=step_name)
            log_path = out_dir / f"{step_name}.log"
            write_text(
                log_path,
                "\n".join(
                    [
                        "[sc-review-pipeline] reused latest successful full pipeline"
                        if exact_snapshot_match
                        else "[sc-review-pipeline] reused latest successful full pipeline after non-task doc delta",
                        f"source_run_dir={candidate}",
                        f"source_summary={summary_path}",
                        f"change_scope_strategy={str(change_scope.get('deterministic_strategy') or '').strip()}",
                        f"changed_paths={json.dumps(change_scope.get('changed_paths') or [], ensure_ascii=False)}",
                        f"step_name={step_name}",
                        f"reported_out_dir={snapshot_dir}",
                        f"summary_file={snapshot_summary}",
                    ]
                )
                + "\n",
            )
            reused_steps.append(
                {
                    "name": step_name,
                    "cmd": list(source_step.get("cmd") or []),
                    "rc": 0,
                    "status": "ok",
                    "log": str(log_path),
                    "reported_out_dir": snapshot_dir,
                    "summary_file": snapshot_summary,
                }
            )
        if reused_steps:
            return reused_steps
    return None


def _find_reusable_deterministic_steps_from_llm_only_failure(
    *,
    out_dir: Path,
    task_id: str,
    delivery_profile: str,
    security_profile: str,
    planned_steps: list[tuple[str, list[str], int, bool]],
    git_fingerprint: dict[str, Any],
) -> list[dict[str, Any]] | None:
    logs_root = repo_root() / "logs" / "ci"
    if not logs_root.exists():
        return None
    current_head = str(git_fingerprint.get("head") or "").strip()
    current_status = sorted([str(line).rstrip() for line in (git_fingerprint.get("status_short") or []) if str(line).strip()])
    planned_map = {
        step_name: _normalize_cmd_for_reuse(cmd)
        for step_name, cmd, _timeout_sec, skipped in planned_steps
        if not skipped and step_name in {"sc-test", "sc-acceptance-check"}
    }
    if set(planned_map) != {"sc-test", "sc-acceptance-check"}:
        return None
    candidates = sorted(
        [item for item in logs_root.rglob(f"sc-review-pipeline-task-{task_id}-*") if item.is_dir()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        if candidate.resolve() == out_dir.resolve():
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
        git_info = execution_context.get("git") if isinstance(execution_context.get("git"), dict) else {}
        previous_status = sorted([str(line).rstrip() for line in (git_info.get("status_short") or []) if str(line).strip()])
        exact_snapshot_match = str(git_info.get("head") or "").strip() == current_head and previous_status == current_status
        change_scope = (
            {
                "deterministic_strategy": "reuse-latest",
                "changed_paths": [],
                "unsafe_paths": [],
            }
            if exact_snapshot_match
            else classify_change_scope_between_snapshots(previous_git=git_info, current_git=git_fingerprint)
        )
        if not exact_snapshot_match and str(delivery_profile or "").strip().lower() == "standard":
            continue
        if not exact_snapshot_match and str(change_scope.get("deterministic_strategy") or "").strip() != "reuse-latest":
            continue
        steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
        step_map = {
            str(step.get("name") or "").strip(): step
            for step in steps
            if isinstance(step, dict) and str(step.get("name") or "").strip()
        }
        llm_step = step_map.get("sc-llm-review")
        if not isinstance(llm_step, dict):
            continue
        llm_step_status = str(llm_step.get("status") or "").strip().lower()
        if llm_step_status == "ok" and _llm_step_is_clean(llm_step):
            continue
        reused_steps: list[dict[str, Any]] = []
        for step_name, planned_cmd in planned_map.items():
            source_step = step_map.get(step_name)
            if not isinstance(source_step, dict):
                reused_steps = []
                break
            if str(source_step.get("status") or "").strip().lower() != "ok":
                reused_steps = []
                break
            if _normalize_cmd_for_reuse(list(source_step.get("cmd") or [])) != planned_cmd:
                reused_steps = []
                break
            snapshot_dir, snapshot_summary = _snapshot_step_artifacts(step=source_step, out_dir=out_dir, step_name=step_name)
            log_path = out_dir / f"{step_name}.log"
            write_text(
                log_path,
                "\n".join(
                    [
                        "[sc-review-pipeline] reused deterministic steps from prior llm-only failure"
                        if exact_snapshot_match
                        else "[sc-review-pipeline] reused deterministic steps after task-semantic/doc delta; llm will rerun",
                        f"source_run_dir={candidate}",
                        f"source_summary={summary_path}",
                        f"change_scope_strategy={str(change_scope.get('deterministic_strategy') or '').strip()}",
                        f"changed_paths={json.dumps(change_scope.get('changed_paths') or [], ensure_ascii=False)}",
                        f"step_name={step_name}",
                        f"reported_out_dir={snapshot_dir}",
                        f"summary_file={snapshot_summary}",
                        f"llm_step_status={str(llm_step.get('status') or '').strip()}",
                    ]
                )
                + "\n",
            )
            reused_steps.append(
                {
                    "name": step_name,
                    "cmd": list(source_step.get("cmd") or []),
                    "rc": 0,
                    "status": "ok",
                    "log": str(log_path),
                    "reported_out_dir": snapshot_dir,
                    "summary_file": snapshot_summary,
                }
            )
        if reused_steps:
            return reused_steps
    return None


def _find_reusable_successful_acceptance_step(
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
        if candidate.resolve() == out_dir.resolve():
            continue
        summary_path = candidate / "summary.json"
        execution_context = _read_execution_context(candidate)
        if not summary_path.exists() or not execution_context:
            continue
        if _normalize_profile_value(execution_context.get("delivery_profile")) != delivery_profile:
            continue
        if _normalize_profile_value(execution_context.get("security_profile")) != security_profile:
            continue
        git_info = execution_context.get("git") if isinstance(execution_context.get("git"), dict) else {}
        previous_status = sorted([str(line).rstrip() for line in (git_info.get("status_short") or []) if str(line).strip()])
        exact_snapshot_match = str(git_info.get("head") or "").strip() == current_head and previous_status == current_status
        change_scope = (
            {
                "deterministic_strategy": "reuse-latest",
                "changed_paths": [],
                "unsafe_paths": [],
            }
            if exact_snapshot_match
            else classify_change_scope_between_snapshots(previous_git=git_info, current_git=git_fingerprint)
        )
        if not exact_snapshot_match and str(change_scope.get("deterministic_strategy") or "").strip() != "reuse-latest":
            continue
        summary = _read_json(summary_path)
        steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
        source_step = next(
            (
                step
                for step in steps
                if isinstance(step, dict) and str(step.get("name") or "").strip() == "sc-acceptance-check"
            ),
            None,
        )
        if not isinstance(source_step, dict):
            continue
        if str(source_step.get("status") or "").strip().lower() != "ok":
            continue
        source_cmd = list(source_step.get("cmd") or [])
        source_summary_path = _resolve_summary_path(str(source_step.get("summary_file") or "").strip())
        if _normalize_cmd_for_reuse(source_cmd) != normalized_planned_cmd:
            if not _acceptance_summary_covers_planned_groups(summary_path=source_summary_path, planned_cmd=planned_cmd):
                continue
        snapshot_dir, snapshot_summary = _snapshot_step_artifacts(step=source_step, out_dir=out_dir, step_name="sc-acceptance-check")
        log_path = out_dir / "sc-acceptance-preflight.log"
        write_text(
            log_path,
            "\n".join(
                [
                    "[sc-review-pipeline] skipped acceptance preflight because matching acceptance already succeeded"
                    if exact_snapshot_match
                    else "[sc-review-pipeline] skipped acceptance preflight after semantic/doc delta because matching acceptance already succeeded",
                    f"source_run_dir={candidate}",
                    f"source_summary={summary_path}",
                    f"change_scope_strategy={str(change_scope.get('deterministic_strategy') or '').strip()}",
                    f"changed_paths={json.dumps(change_scope.get('changed_paths') or [], ensure_ascii=False)}",
                    f"reported_out_dir={snapshot_dir}",
                    f"summary_file={snapshot_summary}",
                ]
            )
            + "\n",
        )
        return {
            "name": "sc-acceptance-check",
            "cmd": list(source_step.get("cmd") or []),
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
    complexity_bonus = 0
    if len(planned_agents) >= 4:
        complexity_bonus += 60
    if str(llm_semantic_gate or "").strip().lower() == "require":
        complexity_bonus += 60
    if len(planned_agents) >= 6:
        complexity_bonus += 60
    escalated_timeout = min(
        int(llm_timeout_sec),
        max(int(llm_agent_timeout_sec) * 2, int(llm_agent_timeout_sec) + 120) + complexity_bonus,
    )
    if escalated_timeout <= int(llm_agent_timeout_sec):
        return {}
    planned_agent_set = set(planned_agents)
    current_out_dir_resolved = current_out_dir.resolve()
    candidates = sorted(
        [item for item in logs_root.rglob(f"sc-review-pipeline-task-{task_id}-*") if item.is_dir()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    timed_out_agents: dict[str, int] = {}
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
        for result in llm_summary.get("results", []):
            if not isinstance(result, dict):
                continue
            agent = str(result.get("agent") or "").strip()
            if not agent or agent not in planned_agent_set:
                continue
            if int(result.get("rc") or 0) == 124:
                details = result.get("details") if isinstance(result.get("details"), dict) else {}
                llm_context = execution_context.get("llm_review") if isinstance(execution_context.get("llm_review"), dict) else {}
                context_overrides = llm_context.get("agent_timeout_overrides") if isinstance(llm_context.get("agent_timeout_overrides"), dict) else {}
                previous_effective_timeout = int(details.get("agent_timeout_sec") or 0)
                if previous_effective_timeout <= 0:
                    previous_effective_timeout = int(context_overrides.get(agent) or 0)
                if previous_effective_timeout <= 0:
                    previous_effective_timeout = int(llm_context.get("agent_timeout_sec") or 0)
                if previous_effective_timeout <= 0:
                    previous_effective_timeout = int(llm_agent_timeout_sec)
                timed_out_agents[agent] = max(int(timed_out_agents.get(agent) or 0), previous_effective_timeout)
    if not timed_out_agents:
        return {}
    return {
        agent: min(int(llm_timeout_sec), max(escalated_timeout, int(timed_out_agents.get(agent) or 0) + 120))
        for agent in planned_agents
        if agent in timed_out_agents
    }


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


def _has_materialized_pipeline_steps(summary: dict[str, Any]) -> bool:
    return _has_materialized_pipeline_steps_impl(summary)


def _derive_pipeline_run_type(summary: dict[str, Any]) -> str:
    return _derive_pipeline_run_type_impl(summary)


def _write_active_task_sidecar(*, task_id: str, run_id: str, out_dir: Path, status: str) -> None:
    effective_status = status
    latest_path = _pipeline_latest_index_path(task_id)
    if latest_path.exists():
        try:
            latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
            if isinstance(latest_payload, dict):
                latest_status = str(latest_payload.get("status") or "").strip()
                if latest_status:
                    effective_status = latest_status
        except Exception:
            pass
    _write_active_task_sidecar_impl(
        task_id=task_id,
        run_id=run_id,
        out_dir=out_dir,
        status=effective_status,
        latest_json_path=latest_path,
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
    planned_acceptance_cmd: list[str] | None,
    git_fingerprint: dict[str, Any],
) -> int | None:
    os.environ.pop("SC_ACCEPTANCE_REUSE_SUMMARY", None)
    if bool(args.dry_run) or bool(args.resume) or bool(args.fork):
        return None
    if bool(args.skip_test) or bool(args.skip_acceptance):
        return None
    if planned_acceptance_cmd:
        reusable_acceptance = _find_reusable_successful_acceptance_step(
            out_dir=session.out_dir,
            task_id=task_id,
            delivery_profile=delivery_profile,
            security_profile=security_profile,
            planned_cmd=planned_acceptance_cmd,
            git_fingerprint=git_fingerprint,
        )
        if reusable_acceptance is not None:
            diagnostics = session.marathon_state.setdefault("diagnostics", {})
            if isinstance(diagnostics, dict):
                diagnostics["acceptance_preflight"] = {
                    "status": "skipped",
                    "reason": "matching_acceptance_already_succeeded",
                    "source_summary_file": str(reusable_acceptance.get("summary_file") or ""),
                }
            os.environ["SC_ACCEPTANCE_REUSE_SUMMARY"] = str(reusable_acceptance.get("summary_file") or "")
            session.append_run_event(
                out_dir=session.out_dir,
                event="acceptance_preflight_skipped",
                task_id=task_id,
                run_id=run_id,
                delivery_profile=delivery_profile,
                security_profile=security_profile,
                status="skipped",
                details={
                    "reason": "matching_acceptance_already_succeeded",
                    "summary_file": str(reusable_acceptance.get("summary_file") or ""),
                },
            )
            if not session.persist():
                return 2
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
        os.environ["SC_ACCEPTANCE_REUSE_SUMMARY"] = str(preflight_step.get("summary_file") or "")
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
    script_start_monotonic = time.monotonic()
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

    requested_run_id = str(args.run_id or "").strip() or uuid.uuid4().hex
    run_id = requested_run_id
    source_execution_context: dict[str, Any] | None = None

    try:
        if args.resume or args.abort:
            out_dir, summary, marathon_state = _load_source_run(task_id, (args.run_id or "").strip() or None)
            source_execution_context = _read_execution_context(out_dir)
            run_id = str(summary.get("run_id") or "").strip() or run_id
            requested_run_id = str(summary.get("requested_run_id") or run_id).strip() or run_id
        elif args.fork:
            source_out_dir, source_summary, source_state = _load_source_run(task_id, (args.fork_from_run_id or "").strip() or None)
            source_execution_context = _read_execution_context(source_out_dir)
            source_delivery_profile, _source_security_profile = _resolve_pipeline_profiles(
                requested_delivery_profile=args.delivery_profile,
                requested_security_profile=args.security_profile,
                source_execution_context=source_execution_context,
                inherit_from_source=True,
            )
            source_pipeline_defaults = profile_review_pipeline_defaults(source_delivery_profile)
            source_max_step_retries = int(
                args.max_step_retries if args.max_step_retries is not None else source_pipeline_defaults.get("max_step_retries", 0)
            )
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
                max_step_retries=source_max_step_retries,
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
                "started_at_utc": _utc_now_iso(),
                "finished_at_utc": "",
                "elapsed_sec": 0,
                "run_type": "planned-only",
                "reason": "in_progress",
                "reuse_mode": "none",
            }
            marathon_state = None
            if not bool(args.reselect_profile):
                source_execution_context = _load_latest_task_execution_context(task_id)
    except FileExistsError:
        print("[sc-review-pipeline] ERROR: output directory already exists for this task/run_id. Use a new --run-id, --force-new-run-id, or pass --allow-overwrite.")
        return 2
    except RuntimeError as exc:
        print(f"[sc-review-pipeline] ERROR: {exc}")
        return 2
    except FileNotFoundError:
        print("[sc-review-pipeline] ERROR: no existing pipeline run found for resume/abort/fork.")
        return 2

    try:
        delivery_profile, security_profile = _resolve_pipeline_profiles(
            requested_delivery_profile=args.delivery_profile,
            requested_security_profile=args.security_profile,
            source_execution_context=source_execution_context,
            inherit_from_source=bool(args.resume or args.abort or args.fork),
            allow_profile_reselect=bool(args.reselect_profile),
        )
    except RuntimeError as exc:
        print(f"[sc-review-pipeline] ERROR: {exc}")
        return 2
    current_git = current_git_fingerprint()
    profile_floor_decision: dict[str, Any] | None = None
    change_scope_for_floor: dict[str, Any] = {}
    if not bool(args.resume or args.abort or args.fork):
        change_scope_for_floor = _derive_profile_floor_change_scope(
            source_execution_context=source_execution_context,
            current_git=current_git,
        )
        profile_floor_decision = _derive_delivery_profile_floor(
            delivery_profile=delivery_profile,
            security_profile=security_profile,
            change_scope=change_scope_for_floor,
            explicit_security_profile=bool(str(args.security_profile or "").strip()),
        )
        if bool(profile_floor_decision.get("applied")):
            delivery_profile = str(profile_floor_decision.get("delivery_profile") or delivery_profile)
            security_profile = str(profile_floor_decision.get("security_profile") or security_profile)
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
    diagnostics = marathon_state.setdefault("diagnostics", {})
    if isinstance(diagnostics, dict):
        if isinstance(profile_floor_decision, dict) and bool(profile_floor_decision.get("applied")):
            diagnostics["profile_floor"] = profile_floor_decision
        else:
            diagnostics.pop("profile_floor", None)
        profile_drift = _detect_latest_profile_drift(
            current_out_dir=out_dir,
            task_id=task_id,
            delivery_profile=delivery_profile,
            security_profile=security_profile,
        ) if not bool(args.resume or args.abort) else None
        if profile_drift is not None:
            diagnostics["profile_drift"] = profile_drift
        else:
            diagnostics.pop("profile_drift", None)
        change_scope_ceiling = _derive_change_scope_ceiling_guard(
            change_scope=change_scope_for_floor,
            profile_drift=diagnostics.get("profile_drift") if isinstance(diagnostics.get("profile_drift"), dict) else None,
        )
        if change_scope_ceiling is not None:
            diagnostics["change_scope_ceiling"] = change_scope_ceiling
        else:
            diagnostics.pop("change_scope_ceiling", None)
    write_harness_capabilities(
        out_dir=out_dir,
        cmd="sc-review-pipeline",
        task_id=task_id,
        run_id=run_id,
        delivery_profile=delivery_profile,
        security_profile=security_profile,
    )
    requested_llm_agent_timeout_overrides = parse_agent_timeout_overrides(getattr(args, "llm_agent_timeouts", ""))
    derived_llm_agent_timeout_overrides = _derive_llm_agent_timeout_overrides(
        current_out_dir=out_dir,
        task_id=task_id,
        delivery_profile=delivery_profile,
        security_profile=security_profile,
        llm_agents=llm_agents,
        llm_semantic_gate=llm_semantic_gate,
        llm_timeout_sec=llm_timeout_sec,
        llm_agent_timeout_sec=llm_agent_timeout_sec,
    )
    llm_agent_timeout_overrides = {**derived_llm_agent_timeout_overrides, **requested_llm_agent_timeout_overrides}
    llm_agent_timeouts = _format_agent_timeout_overrides(llm_agent_timeout_overrides)
    if derived_llm_agent_timeout_overrides:
        llm_execution_context["derived_agent_timeout_overrides"] = derived_llm_agent_timeout_overrides
    if requested_llm_agent_timeout_overrides:
        llm_execution_context["requested_agent_timeout_overrides"] = requested_llm_agent_timeout_overrides
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
        refresh_summary_meta=lambda current_summary: _refresh_summary_meta(
            current_summary,
            script_start_monotonic=script_start_monotonic,
        ),
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
    force_full_rerun = False
    if not bool(args.resume or args.fork or args.dry_run or args.skip_test or args.skip_acceptance or args.skip_llm_review):
        diagnostics = session.marathon_state.setdefault("diagnostics", {})
        if isinstance(diagnostics, dict):
            rerun_guard = _find_recent_deterministic_green_llm_not_clean_run(
                current_out_dir=out_dir,
                task_id=task_id,
                delivery_profile=delivery_profile,
                security_profile=security_profile,
                git_fingerprint=current_git,
            )
            if rerun_guard is not None:
                if bool(args.allow_full_rerun):
                    rerun_guard = {
                        **rerun_guard,
                        "blocked": False,
                        "override": "allow-full-rerun",
                    }
                    force_full_rerun = True
                diagnostics["rerun_guard"] = rerun_guard
            else:
                repeat_guard = _find_repeated_deterministic_failure_guard(
                    current_out_dir=out_dir,
                    task_id=task_id,
                    delivery_profile=delivery_profile,
                    security_profile=security_profile,
                )
                if repeat_guard is not None:
                    if bool(args.allow_repeat_deterministic_failures):
                        repeat_guard = {
                            **repeat_guard,
                            "blocked": False,
                            "override": "allow-repeat-deterministic-failures",
                        }
                    diagnostics["rerun_guard"] = repeat_guard
                else:
                    diagnostics.pop("rerun_guard", None)
            active_guard = diagnostics.get("rerun_guard") if isinstance(diagnostics.get("rerun_guard"), dict) else None
            if active_guard is None:
                change_scope_guard = diagnostics.get("change_scope_ceiling") if isinstance(diagnostics.get("change_scope_ceiling"), dict) else None
                if change_scope_guard is not None:
                    if bool(args.allow_large_change_scope_rerun):
                        change_scope_guard = {
                            **change_scope_guard,
                            "blocked": False,
                            "override": "allow-large-change-scope-rerun",
                        }
                    diagnostics["rerun_guard"] = change_scope_guard
                    active_guard = change_scope_guard
            active_guard = diagnostics.get("rerun_guard") if isinstance(diagnostics.get("rerun_guard"), dict) else None
            rerun_forbidden = _derive_rerun_forbidden_payload(active_guard)
            if rerun_forbidden is not None:
                diagnostics["rerun_forbidden"] = rerun_forbidden
            else:
                diagnostics.pop("rerun_forbidden", None)
            if isinstance(active_guard, dict) and bool(active_guard.get("blocked")):
                reason = f"rerun_blocked:{str(active_guard.get('kind') or 'guard').strip()}"
                session.summary["status"] = "fail"
                session.summary["reason"] = reason
                session.marathon_state["status"] = "stopped"
                session.marathon_state["stop_reason"] = reason
                append_run_event(
                    out_dir=out_dir,
                    event="rerun_blocked",
                    task_id=task_id,
                    run_id=run_id,
                    delivery_profile=delivery_profile,
                    security_profile=security_profile,
                    status="fail",
                    details=dict(active_guard),
                )
                if not session.persist():
                    return 2
                append_run_event(
                    out_dir=out_dir,
                    event="run_completed",
                    task_id=task_id,
                    run_id=run_id,
                    delivery_profile=delivery_profile,
                    security_profile=security_profile,
                    status="fail",
                    details={"agent_review_mode": "skip", "blocked": True},
                )
                print(f"SC_REVIEW_PIPELINE status={session.summary['status']} out={out_dir}")
                return 1
        else:
            diagnostics = {}
    if derived_llm_agent_timeout_overrides and isinstance(session.marathon_state.setdefault("diagnostics", {}), dict):
        session.marathon_state["diagnostics"]["llm_timeout_memory"] = {
            "overrides": dict(derived_llm_agent_timeout_overrides),
            "planned_agents": resolve_agents(llm_agents, llm_semantic_gate),
        }
    elif isinstance(session.marathon_state.setdefault("diagnostics", {}), dict):
        session.marathon_state["diagnostics"].pop("llm_timeout_memory", None)
    if not force_full_rerun and not bool(args.resume or args.fork or args.dry_run or args.skip_test or args.skip_acceptance or args.skip_llm_review):
        reusable_pipeline_steps = _find_reusable_clean_pipeline_steps(
            out_dir=out_dir,
            task_id=task_id,
            delivery_profile=delivery_profile,
            security_profile=security_profile,
            planned_steps=steps,
            git_fingerprint=current_git,
        )
        if reusable_pipeline_steps:
            _set_reuse_mode(session.summary, "full-clean-reuse")
            diagnostics = session.marathon_state.setdefault("diagnostics", {})
            if isinstance(diagnostics, dict):
                first_step = reusable_pipeline_steps[0] if reusable_pipeline_steps else {}
                diagnostics["reuse_decision"] = {
                    "mode": "full-clean-reuse",
                    "blocked": False,
                    "source_summary_file": str(first_step.get("summary_file") or ""),
                }
            for step in reusable_pipeline_steps:
                if not session.add_step(step):
                    return 2
            print(f"SC_REVIEW_PIPELINE status={session.summary['status']} out={out_dir}")
            return session.finish()
    if not force_full_rerun and not bool(args.resume or args.fork or args.dry_run or args.skip_test or args.skip_acceptance):
        reusable_deterministic_steps = _find_reusable_deterministic_steps_from_llm_only_failure(
            out_dir=out_dir,
            task_id=task_id,
            delivery_profile=delivery_profile,
            security_profile=security_profile,
            planned_steps=steps,
            git_fingerprint=current_git,
        )
        if reusable_deterministic_steps:
            _set_reuse_mode(session.summary, "deterministic-only-reuse")
            diagnostics = session.marathon_state.setdefault("diagnostics", {})
            if isinstance(diagnostics, dict):
                first_step = reusable_deterministic_steps[0] if reusable_deterministic_steps else {}
                diagnostics["reuse_decision"] = {
                    "mode": "deterministic-only-reuse",
                    "blocked": False,
                    "source_summary_file": str(first_step.get("summary_file") or ""),
                }
            for step in reusable_deterministic_steps:
                if not session.add_step(step):
                    return 2
    reused_sc_test_step: dict[str, Any] | None = None
    existing_step_names = {
        str(step.get("name") or "").strip()
        for step in (session.summary.get("steps") if isinstance(session.summary.get("steps"), list) else [])
        if isinstance(step, dict)
    }
    if not force_full_rerun and not bool(args.resume or args.fork or args.dry_run or args.skip_test) and "sc-test" not in existing_step_names:
        reused_sc_test_step = _find_reusable_sc_test_step(
            out_dir=out_dir,
            task_id=task_id,
            delivery_profile=delivery_profile,
            security_profile=security_profile,
            planned_cmd=list(steps[0][1]),
            git_fingerprint=current_git,
        )
        if reused_sc_test_step is not None:
            os.environ["SC_TEST_REUSE_SUMMARY"] = str(reused_sc_test_step.get("summary_file") or "")
            _set_reuse_mode(session.summary, "sc-test-reuse")
            diagnostics = session.marathon_state.setdefault("diagnostics", {})
            if isinstance(diagnostics, dict):
                diagnostics["reuse_decision"] = {
                    "mode": "sc-test-reuse",
                    "blocked": False,
                    "source_summary_file": str(reused_sc_test_step.get("summary_file") or ""),
                }
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
        planned_acceptance_cmd=next((cmd for step_name, cmd, _timeout, skipped in steps if step_name == "sc-acceptance-check" and not skipped), None),
        git_fingerprint=current_git,
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
