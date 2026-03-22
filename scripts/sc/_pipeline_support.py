from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from agent_to_agent_review import write_agent_review
from _approval_contract import approval_request_path, approval_response_path
from _delivery_profile import profile_agent_review_defaults
from _harness_capabilities import harness_capabilities_path
from _pipeline_events import run_events_path
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


def run_step(*, out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> dict[str, Any]:
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=timeout_sec)
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
            reported_out_dir = str(candidate_path)
            summary_candidate = candidate_path / "summary.json"
            if summary_candidate.exists():
                summary_file = str(summary_candidate)
            break
    return {
        "name": name,
        "cmd": cmd,
        "rc": rc,
        "status": "ok" if rc == 0 else "fail",
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
    return payload if isinstance(payload, dict) else None


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
