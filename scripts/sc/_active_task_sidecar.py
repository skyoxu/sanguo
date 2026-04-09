from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _pipeline_helpers import derive_pipeline_run_type
from _pipeline_history import collect_recent_failure_summary
from _util import repo_root, write_json, write_text

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "scripts" / "python") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "python"))

from _chapter6_recovery_common import chapter6_stop_loss_note as _chapter6_stop_loss_note


def active_task_dir(root: Path | None = None) -> Path:
    base = root.resolve() if root else repo_root()
    return base / "logs" / "ci" / "active-tasks"


def active_task_json_path(task_id: str, root: Path | None = None) -> Path:
    return active_task_dir(root) / f"task-{str(task_id).strip()}.active.json"


def active_task_md_path(task_id: str, root: Path | None = None) -> Path:
    return active_task_dir(root) / f"task-{str(task_id).strip()}.active.md"


def _repo_rel(path: Path, *, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_jsonl_soft(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = str(line or "").strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except Exception:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _normalize_llm_verdict(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"ok", "pass", "passed"}:
        return "OK"
    if raw in {"needs fix", "needs_fix", "need fix", "fail", "failed"}:
        return "Needs Fix"
    return "Unknown"


def _resolve_path(raw: str, *, root: Path) -> Path | None:
    raw_text = str(raw or "").strip()
    if not raw_text:
        return None
    candidate = Path(raw_text)
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
    return candidate if candidate.exists() else None


def _resolve_latest_out_dir(latest_payload: dict[str, Any], *, root: Path) -> Path | None:
    if not isinstance(latest_payload, dict):
        return None
    direct = _resolve_path(str(latest_payload.get("latest_out_dir") or "").strip(), root=root)
    if direct is not None:
        return direct
    summary_path = _resolve_path(str(latest_payload.get("summary_path") or "").strip(), root=root)
    if summary_path is not None:
        return summary_path.parent
    execution_context_path = _resolve_path(str(latest_payload.get("execution_context_path") or "").strip(), root=root)
    if execution_context_path is not None:
        return execution_context_path.parent
    return None


def _infer_root_from_paths(*, latest_json_path: Path, out_dir: Path) -> Path:
    candidates = [latest_json_path.resolve(), out_dir.resolve()]
    for candidate in candidates:
        parts_lower = [part.lower() for part in candidate.parts]
        for idx in range(len(parts_lower) - 1):
            if parts_lower[idx] == "logs" and parts_lower[idx + 1] == "ci":
                return Path(*candidate.parts[:idx]).resolve()
    latest_parent = latest_json_path.resolve().parent
    if latest_parent.name.startswith("sc-review-pipeline-task-"):
        return latest_parent.parent.resolve()
    out_name = out_dir.resolve().name
    if out_name.startswith("sc-review-pipeline-task-"):
        return out_dir.resolve().parent.resolve()
    return repo_root()


def _normalize_pipeline_summary(
    *,
    summary: dict[str, Any],
    latest_payload: dict[str, Any],
    effective_status: str,
    run_events_path: Path | None,
    run_id: str,
) -> dict[str, Any]:
    normalized = dict(summary)
    normalized_status = str(normalized.get("status") or effective_status or latest_payload.get("status") or "").strip().lower()
    if not str(normalized.get("run_type") or "").strip():
        normalized["run_type"] = derive_pipeline_run_type(normalized)
    run_type = str(normalized.get("run_type") or "").strip().lower()
    has_run_completed = _has_run_completed_event(run_events_path=run_events_path, run_id=run_id)
    current_reason = str(normalized.get("reason") or "").strip().lower()
    if run_type == "planned-only" and has_run_completed and current_reason in {"", "in_progress", "dry_run", "dry-run", "pipeline_clean"}:
        normalized["reason"] = "planned_only_incomplete"
    if not str(normalized.get("started_at_utc") or "").strip():
        normalized["started_at_utc"] = str(latest_payload.get("started_at_utc") or "").strip() or "unknown"
    if not str(normalized.get("finished_at_utc") or "").strip():
        normalized["finished_at_utc"] = str(latest_payload.get("finished_at_utc") or "").strip()
    if not str(normalized.get("reuse_mode") or "").strip():
        normalized["reuse_mode"] = str(latest_payload.get("reuse_mode") or "").strip().lower() or "none"
    if not str(normalized.get("reason") or "").strip():
        latest_reason = str(latest_payload.get("reason") or "").strip()
        if latest_reason:
            normalized["reason"] = latest_reason
            return normalized
        if normalized_status == "aborted":
            normalized["reason"] = "aborted"
        elif normalized_status == "running":
            normalized["reason"] = "in_progress"
        elif normalized_status == "fail":
            normalized["reason"] = "step_failed"
        else:
            normalized["reason"] = "pipeline_clean"
    return normalized


def _derive_step_summary(summary: dict[str, Any]) -> dict[str, str]:
    steps = summary.get("steps")
    if not isinstance(steps, list):
        return {"latest_step": "", "latest_step_status": "", "failed_step": "", "last_completed_step": ""}
    latest_step = ""
    latest_step_status = ""
    failed_step = ""
    last_completed = ""
    for item in steps:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        status = str(item.get("status") or "").strip()
        if name:
            latest_step = name
            latest_step_status = status
        if not failed_step and status == "fail":
            failed_step = name
        if status == "ok":
            last_completed = name
    return {
        "latest_step": latest_step,
        "latest_step_status": latest_step_status,
        "failed_step": failed_step,
        "last_completed_step": last_completed,
    }


def _derive_clean_state(*, summary: dict[str, Any], out_dir: Path, root: Path) -> dict[str, Any]:
    steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
    run_type = str(summary.get("run_type") or "").strip().lower()
    step_map = {
        str(item.get("name") or "").strip(): item
        for item in steps
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    test_status = str((step_map.get("sc-test") or {}).get("status") or "").strip().lower()
    acceptance_status = str((step_map.get("sc-acceptance-check") or {}).get("status") or "").strip().lower()
    llm_step = step_map.get("sc-llm-review") or {}
    llm_status = str(llm_step.get("status") or "").strip().lower()
    llm_summary_path = _resolve_path(str(llm_step.get("summary_file") or "").strip(), root=root)
    needs_fix_agents: list[str] = []
    unknown_agents: list[str] = []
    timeout_agents: list[str] = []
    if llm_summary_path is not None:
        payload = _read_json(llm_summary_path)
        results = payload.get("results") if isinstance(payload.get("results"), list) else []
        for row in results:
            if not isinstance(row, dict):
                continue
            agent = str(row.get("agent") or "").strip()
            verdict = _normalize_llm_verdict(str(((row.get("details") or {}) if isinstance(row.get("details"), dict) else {}).get("verdict") or ""))
            rc = int(row.get("rc") or 0)
            status = str(row.get("status") or "").strip().lower()
            if verdict == "Needs Fix" and agent:
                needs_fix_agents.append(agent)
            if (verdict == "Unknown" or status not in {"ok", "skipped"} or rc != 0) and agent:
                unknown_agents.append(agent)
            if rc == 124 and agent:
                timeout_agents.append(agent)
    deterministic_ok = test_status == "ok" and acceptance_status == "ok"
    llm_clean = llm_status == "ok" and not needs_fix_agents and not unknown_agents
    if deterministic_ok and llm_clean:
        state = "clean"
    elif deterministic_ok and (needs_fix_agents or unknown_agents or llm_status == "fail"):
        state = "deterministic_ok_llm_not_clean"
    elif deterministic_ok and llm_status == "skipped":
        state = "deterministic_only"
    else:
        state = "not_clean"
    if run_type == "planned-only" and str(summary.get("finished_at_utc") or "").strip():
        state = "not_clean"
    return {
        "state": state,
        "run_type": run_type,
        "deterministic_ok": deterministic_ok,
        "llm_status": llm_status,
        "llm_summary_path": _repo_rel(llm_summary_path, root=root) if llm_summary_path else "",
        "needs_fix_agents": sorted(needs_fix_agents),
        "unknown_agents": sorted(set(unknown_agents)),
        "timeout_agents": sorted(set(timeout_agents)),
    }


def _derive_waste_signals(*, summary: dict[str, Any], root: Path) -> dict[str, bool]:
    steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
    step_map = {
        str(item.get("name") or "").strip(): item
        for item in steps
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    sc_test_step = step_map.get("sc-test") or {}
    sc_test_summary_path = _resolve_path(str(sc_test_step.get("summary_file") or "").strip(), root=root)
    signal = False
    if sc_test_summary_path is not None:
        payload = _read_json(sc_test_summary_path)
        sc_steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []
        sc_step_map = {
            str(item.get("name") or "").strip(): item
            for item in sc_steps
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        }
        unit_status = str((sc_step_map.get("unit") or {}).get("status") or "").strip().lower()
        engine_ran = any(
            str((sc_step_map.get(name) or {}).get("status") or "").strip().lower() in {"ok", "fail"}
            for name in ("gdunit-hard", "smoke")
        )
        signal = unit_status == "fail" and engine_ran
    return {
        "unit_failed_but_engine_lane_ran": signal,
    }


def _signal_driven_recommendation(
    *,
    diagnostics: dict[str, Any],
    failed_step: str,
    clean_state: dict[str, Any],
) -> tuple[str, str, str] | None:
    rerun_guard = diagnostics.get("rerun_guard") if isinstance(diagnostics.get("rerun_guard"), dict) else {}
    if bool(rerun_guard.get("blocked")):
        kind = str(rerun_guard.get("kind") or "").strip()
        if kind == "deterministic_green_llm_not_clean":
            return (
                "needs-fix-fast",
                "Rerun guard blocked another full 6.7 because deterministic steps are already green; continue with the narrow llm-only closure path.",
                "rerun_guard",
            )
        if kind == "repeat_deterministic_failure":
            return (
                "inspect",
                "Rerun guard blocked another full rerun after repeated deterministic failures; inspect the repeated sc-test fingerprint and fix the root cause first.",
                "rerun_guard",
            )
        if kind in {"dirty_worktree_unsafe_paths_ceiling", "dirty_worktree_changed_paths_ceiling", "profile_drift_change_scope_ceiling"}:
            return (
                "inspect",
                "Rerun guard blocked another full rerun because the current changes exceed the standard Chapter 6 safe scope; shrink the dirty worktree or inspect/reset the drift first.",
                "rerun_guard",
            )

    llm_retry_stop_loss = diagnostics.get("llm_retry_stop_loss") if isinstance(diagnostics.get("llm_retry_stop_loss"), dict) else {}
    if bool(llm_retry_stop_loss.get("blocked")):
        return (
            "needs-fix-fast",
            "Deterministic steps are already green and the pipeline stopped after the first llm timeout; continue with targeted llm closure instead of paying for another full run.",
            "llm_retry_stop_loss",
        )

    sc_test_retry_stop_loss = diagnostics.get("sc_test_retry_stop_loss") if isinstance(diagnostics.get("sc_test_retry_stop_loss"), dict) else {}
    if bool(sc_test_retry_stop_loss.get("blocked")) and str(failed_step or "").strip() == "sc-test":
        return (
            "rerun",
            "The pipeline stopped the same-run sc-test retry after a known unit failure; fix the unit root cause first, then start a fresh run instead of paying for another identical retry.",
            "sc_test_retry_stop_loss",
        )

    waste_signals = diagnostics.get("waste_signals") if isinstance(diagnostics.get("waste_signals"), dict) else {}
    if bool(waste_signals.get("unit_failed_but_engine_lane_ran")) and str(failed_step or "").strip() == "sc-test":
        return (
            "resume",
            "Unit failure was already known before engine lane work continued; fix the unit failure first and resume only after that to avoid paying the same engine-lane cost again.",
            "waste_signals",
        )
    recent_failure_summary = diagnostics.get("recent_failure_summary") if isinstance(diagnostics.get("recent_failure_summary"), dict) else {}
    if bool(recent_failure_summary.get("stop_full_rerun_recommended")):
        return (
            "inspect",
            "Recent failed runs already repeat the same failure family; inspect the repeated fingerprint and fix the root cause before paying for another full rerun.",
            "recent_failure_summary",
        )
    return None


def _recommended_action(*, status: str, failed_step: str, repair_guide: dict[str, Any], clean_state: dict[str, Any]) -> tuple[str, str]:
    normalized = str(status or "").strip().lower()
    derived_state = str(clean_state.get("state") or "").strip().lower()
    repair_status = str(repair_guide.get("status") or "").strip().lower()
    first_fix_title = ""
    recommendations = repair_guide.get("recommendations")
    if isinstance(recommendations, list):
        for item in recommendations:
            if isinstance(item, dict):
                first_fix_title = str(item.get("title") or "").strip()
                if first_fix_title:
                    break
    if derived_state == "deterministic_ok_llm_not_clean":
        if clean_state.get("timeout_agents") or clean_state.get("unknown_agents"):
            return "needs-fix-fast", "Deterministic steps are already green, but llm_review is incomplete; rerun only the LLM closure path instead of paying for a full pipeline."
        return "needs-fix-fast", "Deterministic steps are already green, but llm_review still reports actionable findings; continue with the task-scoped Needs Fix loop."
    if normalized == "aborted":
        return "rerun", "The latest run was aborted; start a fresh run instead of resuming frozen artifacts."
    if repair_status == "needs-approval":
        return "fork", "Repair guidance requires approval or isolation; prefer fork after reviewing the approval sidecar."
    if repair_status == "needs-fix":
        why = "Repair guidance still reports actionable follow-up; inspect the repair guide and close the remaining findings before continuing."
        if first_fix_title:
            why += f" Suggested first fix: {first_fix_title}."
        return "inspect", why
    if normalized == "ok":
        return "continue", "Pipeline is green; continue the task or start the next task."
    if failed_step:
        why = f"Fix the first blocking step `{failed_step}` and resume the same run."
        if first_fix_title:
            why += f" Suggested first fix: {first_fix_title}."
        return "resume", why
    return "inspect", "Inspect summary, execution-context, and repair-guide before choosing resume or fork."


def _chapter6_rerun_policy(*, blocked_by: str, diagnostics: dict[str, Any]) -> tuple[bool, str]:
    blocked = str(blocked_by or "").strip().lower()
    rerun_guard = diagnostics.get("rerun_guard") if isinstance(diagnostics.get("rerun_guard"), dict) else {}
    guard_kind = str(rerun_guard.get("kind") or "").strip()
    if blocked == "rerun_guard":
        if guard_kind == "repeat_deterministic_failure":
            return True, "--allow-repeat-deterministic-failures"
        if guard_kind in {"dirty_worktree_unsafe_paths_ceiling", "dirty_worktree_changed_paths_ceiling", "profile_drift_change_scope_ceiling"}:
            return True, "--allow-large-change-scope-rerun"
        return True, "--allow-full-rerun"
    if blocked in {"llm_retry_stop_loss", "sc_test_retry_stop_loss", "waste_signals", "recent_failure_summary"}:
        return True, ""
    return False, ""




def _derive_latest_summary_signals(
    *,
    status: str,
    failed_step: str,
    summary: dict[str, Any],
    latest_payload: dict[str, Any],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    normalized_status = str(status or "").strip().lower() or str(summary.get("status") or "").strip().lower()
    reason = str(summary.get("reason") or latest_payload.get("reason") or "").strip()
    if not reason:
        if normalized_status == "aborted":
            reason = "aborted"
        elif normalized_status == "running":
            reason = "in_progress"
        elif normalized_status == "fail":
            reason = f"step_failed:{failed_step}" if failed_step else "pipeline_failed"
        else:
            reason = "pipeline_clean"
    reuse_mode = str(summary.get("reuse_mode") or latest_payload.get("reuse_mode") or "").strip().lower() or "none"
    artifact_integrity = diagnostics.get("artifact_integrity") if isinstance(diagnostics.get("artifact_integrity"), dict) else {}
    return {
        "reason": reason,
        "run_type": str(summary.get("run_type") or latest_payload.get("run_type") or "").strip(),
        "reuse_mode": reuse_mode,
        "artifact_integrity_kind": str(artifact_integrity.get("kind") or "").strip(),
        "diagnostics_keys": sorted(str(key).strip() for key in diagnostics.keys() if str(key).strip()),
    }


def _has_run_completed_event(*, run_events_path: Path | None, run_id: str) -> bool:
    for payload in _load_jsonl_soft(run_events_path):
        if str(payload.get("event") or "").strip() != "run_completed":
            continue
        event_run_id = str(payload.get("run_id") or "").strip()
        if event_run_id and run_id and event_run_id != run_id:
            continue
        return True
    return False


def build_active_task_payload(
    *,
    task_id: str,
    run_id: str,
    status: str,
    out_dir: Path,
    latest_json_path: Path,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = root.resolve() if root else repo_root()
    latest_payload = _read_json(latest_json_path)
    effective_out_dir = _resolve_latest_out_dir(latest_payload, root=resolved_root) or out_dir
    effective_run_id = str(latest_payload.get("run_id") or run_id).strip() if effective_out_dir != out_dir else str(run_id).strip()
    effective_status = str(latest_payload.get("status") or status).strip() if effective_out_dir != out_dir else str(status).strip()
    summary_path = effective_out_dir / "summary.json"
    execution_context_path = effective_out_dir / "execution-context.json"
    repair_guide_json_path = effective_out_dir / "repair-guide.json"
    repair_guide_md_path = effective_out_dir / "repair-guide.md"
    run_events_path = _resolve_path(str(latest_payload.get("run_events_path") or "").strip(), root=resolved_root) or (effective_out_dir / "run-events.jsonl")
    summary = _read_json(summary_path)
    summary = _normalize_pipeline_summary(
        summary=summary,
        latest_payload=latest_payload,
        effective_status=effective_status,
        run_events_path=run_events_path,
        run_id=effective_run_id,
    )
    repair_guide = _read_json(repair_guide_json_path)
    execution_context = _read_json(execution_context_path)
    step_summary = _derive_step_summary(summary)
    clean_state = _derive_clean_state(summary=summary, out_dir=out_dir, root=resolved_root)
    diagnostics = dict(execution_context.get("diagnostics") or {}) if isinstance(execution_context.get("diagnostics"), dict) else {}
    recent_failure_summary = collect_recent_failure_summary(
        task_id=str(task_id).strip(),
        delivery_profile=str(execution_context.get("delivery_profile") or "").strip(),
        security_profile=str(execution_context.get("security_profile") or "").strip(),
        root=resolved_root,
        limit=3,
    )
    if recent_failure_summary:
        diagnostics["recent_failure_summary"] = recent_failure_summary
    waste_signals = _derive_waste_signals(summary=summary, root=resolved_root)
    if any(bool(value) for value in waste_signals.values()):
        diagnostics["waste_signals"] = waste_signals
    summary_status = str(summary.get("status") or effective_status).strip().lower()
    has_run_completed = _has_run_completed_event(run_events_path=run_events_path, run_id=effective_run_id)
    artifact_integrity: dict[str, Any] | None = None
    if str(summary.get("run_type") or "").strip().lower() == "planned-only" and (
        str(summary.get("finished_at_utc") or "").strip() or has_run_completed
    ):
        artifact_integrity = {
            "kind": "planned_only_incomplete",
            "blocked": True,
        }
    if summary_status in {"ok", "fail", "aborted"}:
        if run_events_path is None or not run_events_path.exists():
            artifact_integrity = {
                "kind": "artifact_missing",
                "blocked": True,
            }
        elif not has_run_completed:
            artifact_integrity = {
                "kind": "artifact_incomplete",
                "blocked": True,
            }
    if artifact_integrity is not None:
        diagnostics["artifact_integrity"] = artifact_integrity
    signal_recommendation = _signal_driven_recommendation(
        diagnostics=diagnostics,
        failed_step=step_summary["failed_step"],
        clean_state=clean_state,
    )
    blocked_by = ""
    if artifact_integrity is not None:
        recommended_action = "rerun"
        recommended_why = "Latest recovery bundle is missing a completed producer run; inspect the stale artifacts only for evidence, then start a fresh real run."
        blocked_by = "artifact_integrity"
    elif signal_recommendation is not None:
        recommended_action, recommended_why, blocked_by = signal_recommendation
    else:
        recommended_action, recommended_why = _recommended_action(
            status=status,
            failed_step=step_summary["failed_step"],
            repair_guide=repair_guide,
            clean_state=clean_state,
        )
        if recommended_action == "needs-fix-fast":
            blocked_by = "rerun_guard"
        elif step_summary["failed_step"]:
            blocked_by = "deterministic_failure"
    latest_summary_signals = _derive_latest_summary_signals(
        status=status,
        failed_step=step_summary["failed_step"],
        summary=summary,
        latest_payload=latest_payload,
        diagnostics=diagnostics,
    )
    rerun_forbidden, rerun_override_flag = _chapter6_rerun_policy(blocked_by=blocked_by, diagnostics=diagnostics)
    chapter6_hints = {
        "next_action": recommended_action,
        "can_skip_6_7": recommended_action in {"continue", "needs-fix-fast"},
        "can_go_to_6_8": recommended_action == "needs-fix-fast",
        "blocked_by": blocked_by,
        "rerun_forbidden": rerun_forbidden,
        "rerun_override_flag": rerun_override_flag,
    }
    return {
        "cmd": "active-task-sidecar",
        "task_id": str(task_id).strip(),
        "run_id": effective_run_id,
        "status": effective_status,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "paths": {
            "latest_json": _repo_rel(latest_json_path, root=resolved_root),
            "out_dir": _repo_rel(effective_out_dir, root=resolved_root),
            "summary_json": _repo_rel(summary_path, root=resolved_root),
            "execution_context_json": _repo_rel(execution_context_path, root=resolved_root),
            "repair_guide_json": _repo_rel(repair_guide_json_path, root=resolved_root),
            "repair_guide_md": _repo_rel(repair_guide_md_path, root=resolved_root),
        },
        "step_summary": step_summary,
        "clean_state": clean_state,
        "diagnostics": diagnostics,
        "latest_summary_signals": latest_summary_signals,
        "chapter6_hints": chapter6_hints,
        "recommended_action": recommended_action,
        "recommended_action_why": recommended_why,
        "candidate_commands": {
            "resume": f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --resume",
            "fork": f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --fork",
            "rerun": f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id}",
            "needs_fix_fast": f"py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id {task_id} --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            "resume_summary": f"py -3 scripts/python/dev_cli.py resume-task --task-id {task_id}",
        },
        "repair_status": str(repair_guide.get("status") or "").strip(),
        "agent_review_recommended_action": str(
            ((execution_context.get("agent_review") or {}).get("recommended_action")) or ""
        ).strip(),
    }


def render_active_task_markdown(payload: dict[str, Any]) -> str:
    paths = payload.get("paths") or {}
    steps = payload.get("step_summary") or {}
    commands = payload.get("candidate_commands") or {}
    clean_state = payload.get("clean_state") or {}
    diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
    profile_drift = diagnostics.get("profile_drift") if isinstance(diagnostics.get("profile_drift"), dict) else {}
    waste_signals = diagnostics.get("waste_signals") if isinstance(diagnostics.get("waste_signals"), dict) else {}
    rerun_guard = diagnostics.get("rerun_guard") if isinstance(diagnostics.get("rerun_guard"), dict) else {}
    reuse_decision = diagnostics.get("reuse_decision") if isinstance(diagnostics.get("reuse_decision"), dict) else {}
    llm_timeout_memory = diagnostics.get("llm_timeout_memory") if isinstance(diagnostics.get("llm_timeout_memory"), dict) else {}
    llm_retry_stop_loss = diagnostics.get("llm_retry_stop_loss") if isinstance(diagnostics.get("llm_retry_stop_loss"), dict) else {}
    latest_summary_signals = payload.get("latest_summary_signals") if isinstance(payload.get("latest_summary_signals"), dict) else {}
    chapter6_hints = payload.get("chapter6_hints") if isinstance(payload.get("chapter6_hints"), dict) else {}
    chapter6_stop_loss_note = _chapter6_stop_loss_note(chapter6_hints, latest_summary_signals)
    lines = [
        "# Active Task Summary",
        "",
        f"- Task id: `{payload.get('task_id')}`",
        f"- Run id: `{payload.get('run_id')}`",
        f"- Status: {payload.get('status')}",
        f"- Updated at UTC: {payload.get('updated_at_utc')}",
        f"- Latest pointer: `{paths.get('latest_json')}`" if paths.get("latest_json") else "- Latest pointer: n/a",
        f"- Pipeline out dir: `{paths.get('out_dir')}`" if paths.get("out_dir") else "- Pipeline out dir: n/a",
        f"- Latest step: {steps.get('latest_step') or 'n/a'}",
        f"- Latest step status: {steps.get('latest_step_status') or 'n/a'}",
        f"- Failed step: {steps.get('failed_step') or 'none'}",
        f"- Last completed step: {steps.get('last_completed_step') or 'none'}",
        f"- Recommended action: {payload.get('recommended_action') or 'inspect'}",
        f"- Recommended action why: {payload.get('recommended_action_why') or 'n/a'}",
        f"- Clean state: {clean_state.get('state') or 'unknown'}",
        f"- Deterministic ok: {clean_state.get('deterministic_ok')}",
        f"- Latest reason: {latest_summary_signals.get('reason') or 'n/a'}",
        f"- Latest run type: {latest_summary_signals.get('run_type') or 'n/a'}",
        f"- Latest reuse mode: {latest_summary_signals.get('reuse_mode') or 'n/a'}",
        f"- Latest artifact integrity: {latest_summary_signals.get('artifact_integrity_kind') or 'none'}",
        f"- Latest diagnostics keys: {', '.join(latest_summary_signals.get('diagnostics_keys') or []) or 'none'}",
        f"- Chapter6 next action: {chapter6_hints.get('next_action') or 'n/a'}",
        f"- Chapter6 can skip 6.7: {bool(chapter6_hints.get('can_skip_6_7'))}",
        f"- Chapter6 can go to 6.8: {bool(chapter6_hints.get('can_go_to_6_8'))}",
        f"- Chapter6 blocked by: {chapter6_hints.get('blocked_by') or 'n/a'}",
        f"- Chapter6 rerun forbidden: {bool(chapter6_hints.get('rerun_forbidden'))}",
        f"- Chapter6 rerun override: {chapter6_hints.get('rerun_override_flag') or 'n/a'}",
        f"- Chapter6 stop-loss note: {chapter6_stop_loss_note or 'n/a'}",
        f"- Resume summary command: `{commands.get('resume_summary')}`" if commands.get("resume_summary") else "- Resume summary command: n/a",
        f"- Resume command: `{commands.get('resume')}`" if commands.get("resume") else "- Resume command: n/a",
        f"- Fork command: `{commands.get('fork')}`" if commands.get("fork") else "- Fork command: n/a",
        f"- Rerun command: `{commands.get('rerun')}`" if commands.get("rerun") else "- Rerun command: n/a",
        f"- Needs Fix command: `{commands.get('needs_fix_fast')}`" if commands.get("needs_fix_fast") else "- Needs Fix command: n/a",
    ]
    if profile_drift:
        lines.append(f"- Diagnostics profile_drift: True ({profile_drift.get('previous_delivery_profile')} -> {profile_drift.get('current_delivery_profile')})")
    if waste_signals:
        lines.append(
            f"- Diagnostics unit_failed_but_engine_lane_ran: {bool(waste_signals.get('unit_failed_but_engine_lane_ran'))}"
        )
    if rerun_guard:
        lines.append(
            f"- Diagnostics rerun_guard: blocked={bool(rerun_guard.get('blocked'))} kind={rerun_guard.get('kind') or 'n/a'} recommended_path={rerun_guard.get('recommended_path') or 'n/a'}"
        )
    if reuse_decision:
        lines.append(
            f"- Diagnostics reuse_decision: mode={reuse_decision.get('mode') or 'n/a'}"
        )
    if llm_timeout_memory:
        override_keys = ",".join(sorted(str(key) for key in dict(llm_timeout_memory.get("overrides") or {}).keys())) or "none"
        lines.append(f"- Diagnostics llm_timeout_memory: overrides={override_keys}")
    if llm_retry_stop_loss:
        lines.append(
            f"- Diagnostics llm_retry_stop_loss: blocked={bool(llm_retry_stop_loss.get('blocked'))} kind={llm_retry_stop_loss.get('kind') or 'n/a'} step_name={llm_retry_stop_loss.get('step_name') or 'n/a'}"
        )
    sc_test_retry_stop_loss = diagnostics.get("sc_test_retry_stop_loss") if isinstance(diagnostics.get("sc_test_retry_stop_loss"), dict) else {}
    if sc_test_retry_stop_loss:
        lines.append(
            f"- Diagnostics sc_test_retry_stop_loss: blocked={bool(sc_test_retry_stop_loss.get('blocked'))} kind={sc_test_retry_stop_loss.get('kind') or 'n/a'} step_name={sc_test_retry_stop_loss.get('step_name') or 'n/a'}"
        )
    artifact_integrity = diagnostics.get("artifact_integrity") if isinstance(diagnostics.get("artifact_integrity"), dict) else {}
    if artifact_integrity:
        lines.append(
            f"- Diagnostics artifact_integrity: blocked={bool(artifact_integrity.get('blocked'))} kind={artifact_integrity.get('kind') or 'n/a'}"
        )
    recent_failure_summary = diagnostics.get("recent_failure_summary") if isinstance(diagnostics.get("recent_failure_summary"), dict) else {}
    if recent_failure_summary:
        lines.append(
            f"- Diagnostics recent_failure_summary: family={recent_failure_summary.get('latest_failure_family') or 'n/a'} same_family_count={int(recent_failure_summary.get('same_family_count') or 0)} stop_full_rerun_recommended={bool(recent_failure_summary.get('stop_full_rerun_recommended'))}"
        )
    return "\n".join(lines) + "\n"


def write_active_task_sidecar(
    *,
    task_id: str,
    run_id: str,
    status: str,
    out_dir: Path,
    latest_json_path: Path,
    root: Path | None = None,
) -> tuple[Path, Path]:
    resolved_root = root.resolve() if root else _infer_root_from_paths(latest_json_path=latest_json_path, out_dir=out_dir)
    payload = build_active_task_payload(
        task_id=task_id,
        run_id=run_id,
        status=status,
        out_dir=out_dir,
        latest_json_path=latest_json_path,
        root=resolved_root,
    )
    json_path = active_task_json_path(task_id, resolved_root)
    md_path = active_task_md_path(task_id, resolved_root)
    write_json(json_path, payload)
    write_text(md_path, render_active_task_markdown(payload))
    return json_path, md_path
