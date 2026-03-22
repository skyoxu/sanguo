from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def resolve_approval_state(*, out_dir: Path, approval_state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = {
        "soft_gate": False,
        "required_action": "",
        "status": "not-needed",
        "decision": "",
        "reason": "",
        "request_id": "",
        "request_path": "",
        "response_path": "",
    }
    if isinstance(approval_state, dict):
        for key in state:
            if key in approval_state:
                state[key] = approval_state.get(key)

    request_path = out_dir / "approval-request.json"
    response_path = out_dir / "approval-response.json"
    request_payload = _read_json(request_path)
    response_payload = _read_json(response_path)

    if request_payload is not None:
        state["soft_gate"] = True
        state["required_action"] = str(request_payload.get("action") or state["required_action"] or "").strip()
        state["status"] = str(request_payload.get("status") or state["status"] or "pending").strip()
        state["reason"] = str(request_payload.get("reason") or state["reason"] or "").strip()
        state["request_id"] = str(request_payload.get("request_id") or state["request_id"] or "").strip()
        state["request_path"] = str(request_path)

    if response_payload is not None:
        state["soft_gate"] = True
        state["decision"] = str(response_payload.get("decision") or state["decision"] or "").strip()
        state["reason"] = str(response_payload.get("reason") or state["reason"] or "").strip()
        state["request_id"] = str(response_payload.get("request_id") or state["request_id"] or "").strip()
        state["response_path"] = str(response_path)
        if state["decision"] in {"approved", "denied"}:
            state["status"] = state["decision"]
        elif state["status"] == "not-needed":
            state["status"] = "invalid"

    for key in ("required_action", "status", "decision", "reason", "request_id", "request_path", "response_path"):
        state[key] = str(state.get(key) or "").strip()
    state["soft_gate"] = bool(state.get("soft_gate") or False)
    return state


def _approval_recommendation(*, rec_id: str, title: str, why: str, commands: list[str], files: list[str]) -> dict[str, Any]:
    return {
        "id": rec_id,
        "title": title,
        "why": why,
        "actions": [],
        "commands": commands,
        "files": [item for item in files if str(item).strip()],
    }


def _strip_fork_commands(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stripped: list[dict[str, Any]] = []
    for item in recommendations:
        if not isinstance(item, dict):
            continue
        cloned = dict(item)
        commands = [str(cmd).strip() for cmd in (cloned.get("commands") or []) if str(cmd).strip()]
        cloned["commands"] = [cmd for cmd in commands if "--fork" not in cmd]
        stripped.append(cloned)
    return stripped


def apply_approval_to_recommendations(
    *,
    task_id: str,
    out_dir: Path,
    recommendations: list[dict[str, Any]],
    approval_state: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    approval = resolve_approval_state(out_dir=out_dir, approval_state=approval_state)
    if approval["required_action"] != "fork":
        return recommendations, approval

    files = [approval["request_path"], approval["response_path"]]
    filtered = [item for item in recommendations if str(item.get("id") or "").strip() != "pipeline-fork"]
    status = approval["status"]
    if status in {"pending", "denied", "invalid", "mismatched"}:
        filtered = _strip_fork_commands(filtered)

    prefix: dict[str, Any] | None = None
    if status == "approved":
        prefix = _approval_recommendation(
            rec_id="approval-fork-approved",
            title="Fork recovery is approved",
            why=approval["reason"] or "The operator approved the isolated fork recovery path.",
            commands=[f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --fork"],
            files=files,
        )
    elif status == "denied":
        prefix = _approval_recommendation(
            rec_id="approval-fork-denied",
            title="Fork recovery was denied",
            why=approval["reason"] or "The operator denied the isolated fork recovery path.",
            commands=[f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --resume"],
            files=files,
        )
    elif status == "pending":
        prefix = _approval_recommendation(
            rec_id="approval-fork-pending",
            title="Fork recovery is pending approval",
            why=approval["reason"] or "A fork request exists, but no approval response is available yet.",
            commands=[],
            files=files,
        )
    elif status in {"invalid", "mismatched"}:
        prefix = _approval_recommendation(
            rec_id="approval-fork-invalid",
            title="Fork approval response is invalid or mismatched",
            why=approval["reason"] or "The stored approval response does not match the current fork request.",
            commands=[],
            files=files,
        )

    if prefix is not None:
        filtered = [prefix, *filtered]
    return filtered, approval
