from __future__ import annotations

import argparse
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Callable

from _approval_contract import approval_request_path, approval_response_path
from _harness_capabilities import harness_capabilities_path
from _pipeline_events import run_events_path
from _util import repo_root, today_str, write_json, write_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run task review pipeline with strict run_id binding.")
    parser.add_argument("--task-id", required=True, help="Task id (e.g. 1 or 1.3).")
    parser.add_argument("--run-id", default=None, help="New run id for normal/fork mode, or selector for resume/abort.")
    parser.add_argument("--fork-from-run-id", default=None, help="Optional source run id selector when using --fork.")
    parser.add_argument("--godot-bin", default=None, help="Godot binary path (or env GODOT_BIN).")
    parser.add_argument("--delivery-profile", default=None, choices=["playable-ea", "fast-ship", "standard"], help="Delivery profile (default: env DELIVERY_PROFILE or fast-ship).")
    parser.add_argument("--security-profile", default=None, choices=["strict", "host-safe"])
    parser.add_argument(
        "--reselect-profile",
        action="store_true",
        help="Allow a fresh run to switch away from the latest task-scoped delivery/security profile lock.",
    )
    parser.add_argument("--skip-test", action="store_true", help="Skip sc-test step.")
    parser.add_argument("--skip-acceptance", action="store_true", help="Skip sc-acceptance-check step.")
    parser.add_argument("--skip-llm-review", action="store_true", help="Skip sc-llm-review step.")
    parser.add_argument("--skip-agent-review", action="store_true", help="Skip the post-pipeline agent review sidecar.")
    parser.add_argument(
        "--allow-full-rerun",
        action="store_true",
        help="Bypass the narrow-path rerun guard and allow a full rerun when deterministic steps are already green.",
    )
    parser.add_argument(
        "--allow-repeat-deterministic-failures",
        action="store_true",
        help="Bypass the repeated deterministic failure guard and rerun even when recent sc-test failures share the same fingerprint.",
    )
    parser.add_argument(
        "--allow-large-change-scope-rerun",
        action="store_true",
        help="Bypass the dirty-worktree ceiling and allow a full rerun when changed/unsafe paths exceed the standard Chapter 6 scope guard.",
    )
    parser.add_argument(
        "--allow-full-unit-fallback",
        action="store_true",
        help="Pass through to sc-test: when task-scoped unit coverage is 0.0%%, retry once without the task filter.",
    )
    parser.add_argument("--llm-agents", default=None, help="llm_review --agents value. Default follows delivery profile.")
    parser.add_argument("--llm-timeout-sec", type=int, default=None, help="llm_review total timeout. Default follows delivery profile.")
    parser.add_argument("--llm-agent-timeout-sec", type=int, default=None, help="llm_review per-agent timeout. Default follows delivery profile.")
    parser.add_argument("--llm-agent-timeouts", default="", help="llm_review per-agent timeout overrides: agent=sec,agent=sec.")
    parser.add_argument("--llm-semantic-gate", default=None, choices=["skip", "warn", "require"])
    parser.add_argument("--llm-base", default="origin/main", help="llm_review --base value.")
    parser.add_argument("--llm-diff-mode", default=None, choices=["full", "summary", "none"], help="llm_review --diff-mode value. Default follows delivery profile.")
    parser.add_argument("--llm-no-uncommitted", action="store_true", help="Do not pass --uncommitted to llm_review.")
    parser.add_argument("--llm-strict", action="store_true", help="Pass --strict to llm_review.")
    parser.add_argument("--review-template", default="scripts/sc/templates/llm_review/bmad-godot-review-template.txt", help="llm_review template path.")
    parser.add_argument("--resume", action="store_true", help="Resume the latest matching run for this task.")
    parser.add_argument("--abort", action="store_true", help="Abort the latest matching run for this task without running steps.")
    parser.add_argument("--fork", action="store_true", help="Fork the latest matching run into a new run id and continue there.")
    parser.add_argument("--max-step-retries", type=int, default=None, help="Automatic retry count for a failing step inside this invocation. Default follows delivery profile.")
    parser.add_argument("--max-wall-time-sec", type=int, default=0, help="Per-run wall-time budget. 0 disables the budget.")
    parser.add_argument("--context-refresh-after-failures", type=int, default=3, help="Flag context refresh when one step fails this many times. 0 disables.")
    parser.add_argument("--context-refresh-after-resumes", type=int, default=2, help="Flag context refresh when resume count reaches this value. 0 disables.")
    parser.add_argument("--context-refresh-after-diff-lines", type=int, default=300, help="Flag context refresh when working-tree diff grows by this many lines from the run baseline. 0 disables.")
    parser.add_argument("--context-refresh-after-diff-categories", type=int, default=2, help="Flag context refresh when new diff categories added from the run baseline reach this count. 0 disables.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned commands without executing.")
    parser.add_argument("--allow-overwrite", action="store_true", help="Allow reusing an existing task+run_id output directory by deleting it first.")
    parser.add_argument("--force-new-run-id", action="store_true", help="When task+run_id directory exists, auto-generate a new run_id instead of failing.")
    return parser


def task_root_id(task_id: str) -> str:
    return str(task_id).strip().split(".", 1)[0].strip()


def prepare_env(run_id: str, delivery_profile: str, security_profile: str) -> None:
    os.environ["SC_PIPELINE_RUN_ID"] = run_id
    os.environ["SC_TEST_RUN_ID"] = run_id
    os.environ["SC_ACCEPTANCE_RUN_ID"] = run_id
    os.environ["DELIVERY_PROFILE"] = delivery_profile
    os.environ["SECURITY_PROFILE"] = security_profile


def pipeline_run_dir(task_id: str, run_id: str) -> Path:
    return repo_root() / "logs" / "ci" / today_str() / f"sc-review-pipeline-task-{task_id}-{run_id}"


def pipeline_latest_index_path(task_id: str) -> Path:
    return repo_root() / "logs" / "ci" / today_str() / f"sc-review-pipeline-task-{task_id}" / "latest.json"


_LATEST_REUSE_MODES = {
    "none",
    "full-clean-reuse",
    "deterministic-only-reuse",
    "sc-test-reuse",
    "mixed-reuse",
}

_PIPELINE_RUN_TYPES = {
    "planned-only",
    "preflight-only",
    "llm-only",
    "deterministic-only",
    "full",
}

_DETERMINISTIC_STEP_NAMES = {
    "sc-build-tdd-refactor-preflight",
    "sc-test",
    "sc-acceptance-check",
}


def _has_run_completed_event(*, out_dir: Path, run_id: str) -> bool:
    events_path = run_events_path(out_dir)
    if not events_path.exists():
        return False
    try:
        for line in events_path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            if str(payload.get("event") or "").strip() != "run_completed":
                continue
            event_run_id = str(payload.get("run_id") or "").strip()
            if event_run_id and event_run_id != str(run_id or "").strip():
                continue
            return True
    except OSError:
        return False
    return False


def derive_pipeline_run_type(summary_payload: dict[str, Any]) -> str:
    steps = summary_payload.get("steps") if isinstance(summary_payload.get("steps"), list) else []
    if not steps:
        return "full"
    materialized_names: set[str] = set()
    for step in steps:
        if not isinstance(step, dict):
            continue
        status = str(step.get("status") or "").strip().lower()
        if not status or status == "planned":
            continue
        name = str(step.get("name") or "").strip()
        if name:
            materialized_names.add(name)

    if not materialized_names:
        return "planned-only"
    if materialized_names == {"sc-build-tdd-refactor-preflight"}:
        return "preflight-only"

    has_llm = "sc-llm-review" in materialized_names
    has_deterministic = bool(materialized_names.intersection(_DETERMINISTIC_STEP_NAMES))
    if has_llm and not has_deterministic:
        return "llm-only"
    if has_deterministic and not has_llm:
        return "deterministic-only"
    return "full"


def has_materialized_pipeline_steps(summary_payload: dict[str, Any]) -> bool:
    return derive_pipeline_run_type(summary_payload) != "planned-only"


def is_planned_only_terminal_run(*, summary_payload: dict[str, Any], out_dir: Path, run_id: str) -> bool:
    return derive_pipeline_run_type(summary_payload) == "planned-only" and _has_run_completed_event(out_dir=out_dir, run_id=run_id)


def effective_pipeline_publish_status(*, status: str, out_dir: Path, run_id: str, summary_payload: dict[str, Any] | None = None) -> str:
    normalized = str(status or "").strip().lower()
    payload = summary_payload if isinstance(summary_payload, dict) else {}
    if normalized == "ok" and payload and is_planned_only_terminal_run(summary_payload=payload, out_dir=out_dir, run_id=run_id):
        return "fail"
    if normalized == "ok" and not _has_run_completed_event(out_dir=out_dir, run_id=run_id):
        return "running"
    return normalized or "fail"


def _derive_latest_reason(
    *,
    summary_payload: dict[str, Any],
    execution_context_payload: dict[str, Any],
    status: str,
    out_dir: Path,
    run_id: str,
) -> str:
    normalized_status = (
        str(status or "").strip().lower()
        or str(summary_payload.get("status") or "").strip().lower()
        or str(execution_context_payload.get("status") or "").strip().lower()
    )
    if is_planned_only_terminal_run(summary_payload=summary_payload, out_dir=out_dir, run_id=run_id):
        return "planned_only_incomplete"
    if normalized_status == "running":
        return "in_progress"
    if normalized_status == "aborted":
        return "aborted"
    explicit_reason = str(summary_payload.get("reason") or "").strip()
    if explicit_reason:
        return explicit_reason
    steps = summary_payload.get("steps") if isinstance(summary_payload.get("steps"), list) else []
    failed_step = next(
        (
            str(step.get("name") or "").strip()
            for step in steps
            if isinstance(step, dict) and str(step.get("status") or "").strip().lower() == "fail"
        ),
        "",
    )
    if not failed_step:
        failed_step = str(execution_context_payload.get("failed_step") or "").strip()

    if normalized_status == "aborted":
        return "aborted"
    if normalized_status == "running":
        return "in_progress"
    if normalized_status == "fail":
        return f"step_failed:{failed_step}" if failed_step else "pipeline_failed"
    if any(isinstance(step, dict) and str(step.get("status") or "").strip().lower() == "planned" for step in steps):
        return "in_progress"
    return "pipeline_clean"


def _derive_latest_reuse_mode(summary_payload: dict[str, Any]) -> str:
    reuse_mode = str(summary_payload.get("reuse_mode") or "").strip().lower()
    if reuse_mode in _LATEST_REUSE_MODES:
        return reuse_mode
    return "none"


def _derive_deterministic_bundle(summary_payload: dict[str, Any]) -> dict[str, Any]:
    steps = summary_payload.get("steps") if isinstance(summary_payload.get("steps"), list) else []
    step_map = {
        str(step.get("name") or "").strip(): step
        for step in steps
        if isinstance(step, dict) and str(step.get("name") or "").strip()
    }
    sc_test_step = step_map.get("sc-test") if isinstance(step_map.get("sc-test"), dict) else {}
    acceptance_step = step_map.get("sc-acceptance-check") if isinstance(step_map.get("sc-acceptance-check"), dict) else {}
    test_status = str(sc_test_step.get("status") or "").strip().lower()
    acceptance_status = str(acceptance_step.get("status") or "").strip().lower()
    if test_status not in {"ok", "reused"} and acceptance_status not in {"ok", "reused"}:
        return {}
    reported_out_dirs = [
        str(value).strip()
        for value in (sc_test_step.get("reported_out_dir"), acceptance_step.get("reported_out_dir"))
        if str(value or "").strip()
    ]
    return {
        "available": True,
        "reuse_mode": _derive_latest_reuse_mode(summary_payload),
        "test_summary_path": str(sc_test_step.get("summary_file") or "").strip(),
        "acceptance_summary_path": str(acceptance_step.get("summary_file") or "").strip(),
        "reported_out_dirs": reported_out_dirs,
    }


def _is_real_canonical_latest_candidate(existing_payload: Any) -> bool:
    if not isinstance(existing_payload, dict):
        return False
    run_id = str(existing_payload.get("run_id") or "").strip()
    latest_out_dir = str(existing_payload.get("latest_out_dir") or "").strip()
    if not run_id or not latest_out_dir:
        return False
    run_type = str(existing_payload.get("run_type") or "").strip().lower()
    reason = str(existing_payload.get("reason") or "").strip().lower()
    if run_type == "planned-only":
        return False
    if reason == "planned_only_incomplete":
        return False
    return True


def _should_preserve_existing_canonical_latest(
    *,
    existing_payload: Any,
    current_summary_payload: dict[str, Any],
    current_out_dir: Path,
    current_run_id: str,
) -> bool:
    if not _is_real_canonical_latest_candidate(existing_payload):
        return False
    return is_planned_only_terminal_run(
        summary_payload=current_summary_payload,
        out_dir=current_out_dir,
        run_id=current_run_id,
    )


def write_latest_index(
    *,
    task_id: str,
    run_id: str,
    out_dir: Path,
    status: str,
    latest_index_path_fn: Callable[[str], Path],
) -> None:
    path = latest_index_path_fn(task_id)
    summary_payload: dict[str, Any] = {}
    execution_context_payload: dict[str, Any] = {}
    summary_path = out_dir / "summary.json"
    execution_context_path = out_dir / "execution-context.json"
    if summary_path.exists():
        try:
            loaded = json.loads(summary_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                summary_payload = loaded
        except Exception:
            summary_payload = {}
    if execution_context_path.exists():
        try:
            loaded = json.loads(execution_context_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                execution_context_payload = loaded
        except Exception:
            execution_context_payload = {}
    effective_status = effective_pipeline_publish_status(
        status=status,
        out_dir=out_dir,
        run_id=run_id,
        summary_payload=summary_payload,
    )
    payload = {
        "task_id": task_id,
        "run_id": run_id,
        "status": effective_status,
        "date": today_str(),
        "latest_out_dir": str(out_dir),
        "summary_path": str(out_dir / "summary.json"),
        "execution_context_path": str(out_dir / "execution-context.json"),
        "repair_guide_json_path": str(out_dir / "repair-guide.json"),
        "repair_guide_md_path": str(out_dir / "repair-guide.md"),
        "marathon_state_path": str(out_dir / "marathon-state.json"),
        "run_events_path": str(run_events_path(out_dir)),
        "harness_capabilities_path": str(harness_capabilities_path(out_dir)),
    }
    payload["reason"] = _derive_latest_reason(
        summary_payload=summary_payload,
        execution_context_payload=execution_context_payload,
        status=effective_status,
        out_dir=out_dir,
        run_id=run_id,
    )
    payload["run_type"] = derive_pipeline_run_type(summary_payload)
    payload["reuse_mode"] = _derive_latest_reuse_mode(summary_payload)
    started_at = str(summary_payload.get("started_at_utc") or "").strip()
    finished_at = str(summary_payload.get("finished_at_utc") or "").strip()
    if started_at:
        payload["started_at_utc"] = started_at
    if "finished_at_utc" in summary_payload:
        payload["finished_at_utc"] = finished_at
    deterministic_bundle = _derive_deterministic_bundle(summary_payload)
    if deterministic_bundle:
        payload["deterministic_bundle"] = deterministic_bundle
    diagnostics = execution_context_payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        diagnostics = summary_payload.get("diagnostics")
    if isinstance(diagnostics, dict) and diagnostics:
        payload["diagnostics"] = diagnostics
    if approval_request_path(out_dir).exists():
        payload["approval_request_path"] = str(approval_request_path(out_dir))
    if approval_request_path(out_dir).exists() and approval_response_path(out_dir).exists():
        payload["approval_response_path"] = str(approval_response_path(out_dir))
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        same_run = (
            isinstance(existing, dict)
            and str(existing.get("run_id") or "").strip() == run_id
            and str(existing.get("latest_out_dir") or "").strip() == str(out_dir)
        )
        if (
            not same_run
            and _should_preserve_existing_canonical_latest(
                existing_payload=existing,
                current_summary_payload=summary_payload,
                current_out_dir=out_dir,
                current_run_id=run_id,
            )
        ):
            return
        if same_run:
            for key in ("agent_review_json_path", "agent_review_md_path"):
                value = str(existing.get(key) or "").strip()
                if value:
                    payload[key] = value
    write_json(path, payload)


def allocate_out_dir(
    task_id: str,
    requested_run_id: str,
    *,
    force_new_run_id: bool,
    allow_overwrite: bool,
    run_dir_fn: Callable[[str, str], Path],
) -> tuple[str, Path]:
    run_id = requested_run_id
    out_dir = run_dir_fn(task_id, run_id)
    if not out_dir.exists():
        return run_id, out_dir
    if force_new_run_id:
        original_run_id = run_id
        attempts = 0
        while out_dir.exists():
            run_id = uuid.uuid4().hex
            out_dir = run_dir_fn(task_id, run_id)
            attempts += 1
            if attempts > 16:
                raise RuntimeError("failed to allocate a unique run_id after 16 attempts")
        print(f"[sc-review-pipeline] INFO: run_id collision detected, remapped {original_run_id} -> {run_id}")
        return run_id, out_dir
    if not allow_overwrite:
        raise FileExistsError("output directory already exists for this task/run_id")
    shutil.rmtree(out_dir, ignore_errors=False)
    return run_id, out_dir


def append_step_event(
    *,
    out_dir: Path,
    task_id: str,
    run_id: str,
    turn_id: str | None,
    turn_seq: int | None,
    delivery_profile: str,
    security_profile: str,
    step: dict[str, Any],
    append_run_event_fn: Callable[..., None],
) -> None:
    status = str(step.get("status") or "").strip().lower()
    event_name = {
        "planned": "step_planned",
        "skipped": "step_skipped",
        "ok": "step_completed",
        "fail": "step_failed",
    }.get(status, "step_updated")
    details: dict[str, Any] = {}
    for key in ("rc", "log", "summary_file", "reported_out_dir"):
        value = step.get(key)
        if value not in (None, ""):
            details[key] = value
    append_run_event_fn(
        out_dir=out_dir,
        event=event_name,
        task_id=task_id,
        run_id=run_id,
        turn_id=turn_id,
        turn_seq=turn_seq,
        delivery_profile=delivery_profile,
        security_profile=security_profile,
        step_name=str(step.get("name") or "").strip() or None,
        status=status or None,
        details=details,
    )


def run_agent_review_post_hook(
    *,
    out_dir: Path,
    mode: str,
    marathon_state: dict[str, Any],
    write_agent_review_fn: Callable[..., tuple[dict[str, Any], list[str], list[str]]],
    apply_agent_review_policy_fn: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
) -> tuple[int, dict[str, Any]]:
    payload, resolve_errors, validation_errors = write_agent_review_fn(out_dir=out_dir, reviewer="artifact-reviewer")
    updated_state = apply_agent_review_policy_fn(marathon_state, payload)
    action = str(((updated_state.get("agent_review") or {}).get("recommended_action")) or "").strip() or "none"
    lines: list[str] = []
    for item in resolve_errors:
        lines.append(f"[sc-agent-review] ERROR: {item}")
    for item in validation_errors:
        lines.append(f"[sc-agent-review] ERROR: {item}")
    lines.append(f"SC_AGENT_REVIEW status={payload['review_verdict']} action={action} out={out_dir}")
    write_text(out_dir / "sc-agent-review.log", "\n".join(lines) + "\n")
    print("\n".join(lines))
    if resolve_errors or validation_errors:
        return 2, updated_state
    verdict = str(payload.get("review_verdict") or "").strip().lower()
    if mode == "require" and verdict in {"needs-fix", "block"}:
        return 1, updated_state
    return 0, updated_state


def load_source_run(
    task_id: str,
    selector_run_id: str | None,
    *,
    latest_index_path: Path,
    resolve_existing_out_dir_fn: Callable[..., Path | None],
    load_existing_summary_fn: Callable[[Path], dict[str, Any] | None],
    load_marathon_state_fn: Callable[[Path], dict[str, Any] | None],
) -> tuple[Path, dict[str, Any], dict[str, Any] | None]:
    out_dir = resolve_existing_out_dir_fn(task_id=task_id, run_id=selector_run_id, preferred_latest_index=latest_index_path)
    if out_dir is None:
        raise FileNotFoundError("no existing pipeline run found")
    summary = load_existing_summary_fn(out_dir) or {}
    if not summary:
        raise RuntimeError(f"existing summary.json is missing or invalid: {out_dir}")
    return out_dir, summary, load_marathon_state_fn(out_dir)
