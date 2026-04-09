from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _approval_contract import (
    approval_request_path,
    approval_response_path,
    build_approval_request,
)
from _sidecar_schema import SidecarSchemaError, validate_approval_response_payload
from _util import write_json


def approval_request_id(run_id: str, action: str) -> str:
    return f"{str(run_id).strip()}:{str(action).strip()}"


def _stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _fork_requested(summary: dict[str, Any], repair_guide: dict[str, Any], marathon_state: dict[str, Any], *, explicit_fork: bool) -> tuple[bool, str]:
    if explicit_fork:
        return True, "Operator requested a forked continuation run."
    approval = repair_guide.get("approval") if isinstance(repair_guide.get("approval"), dict) else {}
    approval_required_action = str(approval.get("required_action") or "").strip().lower()
    approval_status = str(approval.get("status") or "").strip().lower()
    approval_reason = str(approval.get("reason") or "").strip()
    if approval_required_action == "fork" and approval_status in {"pending", "approved", "denied", "invalid", "mismatched"}:
        return True, approval_reason or "Existing fork approval state is still active for this run."
    agent_review = (marathon_state.get("agent_review") or {}) if isinstance(marathon_state, dict) else {}
    if str(agent_review.get("recommended_action") or "").strip().lower() == "fork":
        reasons = [str(item) for item in (agent_review.get("recommended_refresh_reasons") or []) if str(item).strip()]
        tail = f" Reasons: {', '.join(reasons[:3])}." if reasons else ""
        return True, f"Agent review recommended an isolated fork recovery.{tail}"
    recs = repair_guide.get("recommendations") or []
    if any(str(item.get("id") or "").strip() == "pipeline-fork" for item in recs if isinstance(item, dict)):
        if str((marathon_state or {}).get("stop_reason") or "").strip().lower() == "wall_time_exceeded":
            return True, "The run hit the wall-time stop-loss and exposes fork as the isolated recovery path."
        if bool((marathon_state or {}).get("context_refresh_needed")):
            return True, "Context refresh was requested and the repair guide includes fork for isolated continuation."
        if str(summary.get("status") or "").strip().lower() == "fail":
            return True, "The repair guide includes fork so the failing artifact set can stay immutable."
    return False, ""


def _requested_commands(task_id: str, repair_guide: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    for item in repair_guide.get("recommendations") or []:
        if not isinstance(item, dict):
            continue
        for command in item.get("commands") or []:
            text = str(command or "").strip()
            if "--fork" in text:
                commands.append(text)
    commands.append(f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --fork")
    return _stable_unique(commands)


def _requested_files(out_dir: Path) -> list[str]:
    candidates = [
        out_dir / "summary.json",
        out_dir / "execution-context.json",
        out_dir / "repair-guide.json",
        out_dir / "repair-guide.md",
        out_dir / "marathon-state.json",
        out_dir / "agent-review.json",
        out_dir / "agent-review.md",
    ]
    return [str(path) for path in candidates if path.exists()]


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _write_if_changed(path: Path, payload: dict[str, Any]) -> str:
    existing = _load_json(path)
    if existing == payload:
        return "unchanged"
    write_json(path, payload)
    return "updated" if existing is not None else "created"


def sync_soft_approval_sidecars(
    *,
    out_dir: Path,
    task_id: str,
    run_id: str,
    summary: dict[str, Any],
    repair_guide: dict[str, Any],
    marathon_state: dict[str, Any] | None,
    explicit_fork: bool,
) -> dict[str, Any]:
    request_path = approval_request_path(out_dir)
    response_path = approval_response_path(out_dir)
    required, reason = _fork_requested(summary, repair_guide, marathon_state or {}, explicit_fork=explicit_fork)
    result: dict[str, Any] = {
        "soft_gate": True,
        "required_action": "fork" if required else "",
        "status": "not-needed",
        "decision": "",
        "reason": reason,
        "request_id": approval_request_id(run_id, "fork") if required else "",
        "request_path": "",
        "response_path": "",
        "events": [],
    }

    if required:
        request_payload = build_approval_request(
            task_id=task_id,
            run_id=run_id,
            action="fork",
            reason=reason,
            requested_files=_requested_files(out_dir),
            requested_commands=_requested_commands(task_id, repair_guide),
            request_id=result["request_id"],
        )
        transition = _write_if_changed(request_path, request_payload)
        result["request_path"] = str(request_path)
        result["status"] = "pending"
        if transition in {"created", "updated"}:
            result["events"].append(
                {
                    "event": "approval_request_written",
                    "status": "pending",
                    "details": {
                        "action": "fork",
                        "request_id": result["request_id"],
                        "transition": transition,
                    },
                }
            )
    elif request_path.exists():
        request_path.unlink(missing_ok=True)
        result["events"].append(
            {
                "event": "approval_request_cleared",
                "status": "not-needed",
                "details": {"action": "fork"},
            }
        )

    response_payload = _load_json(response_path)
    if response_payload is not None:
        result["response_path"] = str(response_path)
        try:
            validate_approval_response_payload(response_payload)
            result["decision"] = str(response_payload.get("decision") or "").strip()
            response_request_id = str(response_payload.get("request_id") or "").strip()
            if required and response_request_id != result["request_id"]:
                result["status"] = "mismatched"
            else:
                result["status"] = result["decision"] or result["status"]
        except SidecarSchemaError:
            result["status"] = "invalid"

    return result
