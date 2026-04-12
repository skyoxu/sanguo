from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Any

from agent_to_agent_review import write_agent_review
from _approval_contract import approval_request_path, approval_response_path
from _delivery_profile import profile_agent_review_defaults
from _harness_capabilities import harness_capabilities_path
from _pipeline_events import run_events_path
from _pipeline_helpers import derive_pipeline_run_type
from _util import repo_root, run_cmd, today_str, write_json, write_text


OUT_RE = re.compile(r"\bout=([^\r\n]+)")
AGENT_REVIEW_MODES = {"skip", "warn", "require"}


def pipeline_latest_index_path(task_id: str) -> Path:
    return repo_root() / "logs" / "ci" / today_str() / f"sc-review-pipeline-task-{task_id}" / "latest.json"


def write_latest_index(*, task_id: str, run_id: str, out_dir: Path, status: str) -> None:
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
    write_json(pipeline_latest_index_path(task_id), payload)


def _snapshot_child_artifacts(*, pipeline_out_dir: Path, step_name: str, reported_out_dir: Path) -> tuple[str, str]:
    resolved = reported_out_dir.resolve()
    if not resolved.exists() or not resolved.is_dir():
        return str(resolved), str((resolved / "summary.json")) if (resolved / "summary.json").exists() else ""
    try:
        resolved.relative_to(pipeline_out_dir.resolve())
        return str(resolved), str((resolved / "summary.json")) if (resolved / "summary.json").exists() else ""
    except ValueError:
        pass

    snapshot_dir = pipeline_out_dir / "child-artifacts" / step_name
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    shutil.copytree(resolved, snapshot_dir)
    summary_path = snapshot_dir / "summary.json"
    return str(snapshot_dir), str(summary_path) if summary_path.exists() else ""


def run_step(*, out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> dict[str, Any]:
    started = time.monotonic()
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=timeout_sec)
    duration_sec = round(max(0.0, time.monotonic() - started), 3)
    log_path = out_dir / f"{name}.log"
    write_text(log_path, out)
    reported_out_dir = ""
    summary_file = ""
    for line in reversed(out.splitlines()):
        matched = OUT_RE.search(line)
        if not matched:
            continue
        candidate = matched.group(1).strip().strip("\"'").strip()
        if not candidate:
            continue
        candidate_path = Path(candidate)
        if candidate_path.exists():
            reported_out_dir, summary_file = _snapshot_child_artifacts(
                pipeline_out_dir=out_dir,
                step_name=name,
                reported_out_dir=candidate_path,
            )
            break
    return {
        "name": name,
        "cmd": cmd,
        "rc": rc,
        "status": "ok" if rc == 0 else "fail",
        "duration_sec": duration_sec,
        "log": str(log_path),
        "reported_out_dir": reported_out_dir,
        "summary_file": summary_file,
    }


def load_existing_summary(out_dir: Path) -> dict[str, Any] | None:
    path = out_dir / "summary.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if str(payload.get("cmd") or "").strip() == "sc-review-pipeline":
        payload.setdefault("started_at_utc", "legacy")
        finished_at = payload.get("finished_at_utc")
        if not isinstance(finished_at, str):
            payload["finished_at_utc"] = ""
        payload.setdefault("run_type", derive_pipeline_run_type(payload))
        completed_event_seen = False
        events_path = run_events_path(out_dir)
        if events_path.exists():
            run_id = str(payload.get("run_id") or payload.get("requested_run_id") or "").strip()
            try:
                for line in events_path.read_text(encoding="utf-8").splitlines():
                    text = str(line or "").strip()
                    if not text:
                        continue
                    try:
                        event_payload = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(event_payload, dict):
                        continue
                    if str(event_payload.get("event") or "").strip() != "run_completed":
                        continue
                    event_run_id = str(event_payload.get("run_id") or "").strip()
                    if event_run_id and run_id and event_run_id != run_id:
                        continue
                    completed_event_seen = True
                    break
            except OSError:
                completed_event_seen = False
        status = str(payload.get("status") or "").strip().lower()
        current_reason = str(payload.get("reason") or "").strip().lower()
        if str(payload.get("run_type") or "").strip().lower() == "planned-only" and completed_event_seen and current_reason in {"", "in_progress", "dry_run", "dry-run", "pipeline_clean"}:
            payload["reason"] = "planned_only_incomplete"
        elif "reason" not in payload:
            if str(payload.get("run_type") or "").strip().lower() == "planned-only" and completed_event_seen:
                payload["reason"] = "planned_only_incomplete"
            else:
                payload["reason"] = "pipeline_clean" if status == "ok" else "step_failed"
        payload.setdefault("reuse_mode", "none")
        elapsed_sec = payload.get("elapsed_sec")
        if not isinstance(elapsed_sec, int) or int(elapsed_sec) < 0:
            payload["elapsed_sec"] = max(0, int(payload.get("elapsed_sec") or 0))
    return payload


def upsert_step(summary: dict[str, Any], step: dict[str, Any]) -> None:
    steps = summary.get("steps")
    if not isinstance(steps, list):
        summary["steps"] = [step]
        summary["status"] = "fail" if step.get("status") == "fail" else "ok"
        return
    for idx, current in enumerate(steps):
        if isinstance(current, dict) and str(current.get("name") or "") == str(step.get("name") or ""):
            steps[idx] = step
            break
    else:
        steps.append(step)
    summary["status"] = "fail" if any(str(item.get("status") or "") == "fail" for item in steps if isinstance(item, dict)) else "ok"


def resolve_agent_review_mode(delivery_profile: str) -> str:
    mode = str(profile_agent_review_defaults(delivery_profile).get("mode") or "warn").strip().lower()
    return mode if mode in AGENT_REVIEW_MODES else "warn"


def run_agent_review_post_hook(*, out_dir: Path, mode: str) -> int:
    payload, resolve_errors, validation_errors = write_agent_review(out_dir=out_dir, reviewer="artifact-reviewer")
    lines: list[str] = []
    for item in resolve_errors:
        lines.append(f"[sc-agent-review] ERROR: {item}")
    for item in validation_errors:
        lines.append(f"[sc-agent-review] ERROR: {item}")
    lines.append(f"SC_AGENT_REVIEW status={payload['review_verdict']} out={out_dir}")
    write_text(out_dir / "sc-agent-review.log", "\n".join(lines) + "\n")
    print("\n".join(lines))
    if resolve_errors or validation_errors:
        return 2
    verdict = str(payload.get("review_verdict") or "").strip().lower()
    if mode == "require" and verdict in {"needs-fix", "block"}:
        return 1
    return 0
