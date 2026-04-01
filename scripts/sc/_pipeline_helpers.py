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
    parser.add_argument("--skip-test", action="store_true", help="Skip sc-test step.")
    parser.add_argument("--skip-acceptance", action="store_true", help="Skip sc-acceptance-check step.")
    parser.add_argument("--skip-llm-review", action="store_true", help="Skip sc-llm-review step.")
    parser.add_argument("--skip-agent-review", action="store_true", help="Skip the post-pipeline agent review sidecar.")
    parser.add_argument("--llm-agents", default=None, help="llm_review --agents value. Default follows delivery profile.")
    parser.add_argument("--llm-timeout-sec", type=int, default=None, help="llm_review total timeout. Default follows delivery profile.")
    parser.add_argument("--llm-agent-timeout-sec", type=int, default=None, help="llm_review per-agent timeout. Default follows delivery profile.")
    parser.add_argument("--llm-semantic-gate", default=None, choices=["skip", "warn", "require"])
    parser.add_argument("--llm-base", default="main", help="llm_review --base value.")
    parser.add_argument("--llm-diff-mode", default=None, choices=["full", "summary", "none"], help="llm_review --diff-mode value. Default follows delivery profile.")
    parser.add_argument("--llm-no-uncommitted", action="store_true", help="Do not pass --uncommitted to llm_review.")
    parser.add_argument("--llm-strict", action="store_true", help="Pass --strict to llm_review.")
    parser.add_argument("--review-template", default="scripts/sc/templates/llm_review/bmad-godot-review-template.txt", help="llm_review template path.")
    parser.add_argument("--resume", action="store_true", help="Resume the latest matching run for this task.")
    parser.add_argument("--abort", action="store_true", help="Abort the latest matching run for this task without running steps.")
    parser.add_argument("--fork", action="store_true", help="Fork the latest matching run into a new run id and continue there.")
    parser.add_argument("--max-step-retries", type=int, default=0, help="Automatic retry count for a failing step inside this invocation.")
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


def write_latest_index(
    *,
    task_id: str,
    run_id: str,
    out_dir: Path,
    status: str,
    latest_index_path_fn: Callable[[str], Path],
) -> None:
    path = latest_index_path_fn(task_id)
    payload = {
        "task_id": task_id,
        "run_id": run_id,
        "status": status,
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
