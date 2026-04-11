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


def _normalized_action_list(value: Any) -> list[str]:
    return [str(item).strip() for item in list(value or []) if str(item).strip()]


def _expected_contract(*, required_action: str, status: str) -> dict[str, Any]:
    state = {
        "required_action": str(required_action or "").strip(),
        "status": str(status or "").strip(),
        "recommended_action": "",
        "allowed_actions": [],
        "blocked_actions": [],
    }
    _apply_approval_action_contract(state)
    return {
        "recommended_action": str(state.get("recommended_action") or "").strip(),
        "allowed_actions": _normalized_action_list(state.get("allowed_actions")),
        "blocked_actions": _normalized_action_list(state.get("blocked_actions")),
    }


def _response_contract_error(*, response_payload: dict[str, Any], required_action: str, status: str) -> str:
    has_contract_fields = any(key in response_payload for key in ("recommended_action", "allowed_actions", "blocked_actions"))
    if not has_contract_fields:
        return ""
    if not all(key in response_payload for key in ("recommended_action", "allowed_actions", "blocked_actions")):
        return "Approval response contract is incomplete; expected recommended_action, allowed_actions, and blocked_actions together."
    expected = _expected_contract(required_action=required_action, status=status)
    actual = {
        "recommended_action": str(response_payload.get("recommended_action") or "").strip(),
        "allowed_actions": _normalized_action_list(response_payload.get("allowed_actions")),
        "blocked_actions": _normalized_action_list(response_payload.get("blocked_actions")),
    }
    if actual != expected:
        return (
            "Approval response contract does not match the current request/decision state. "
            f"expected={expected} actual={actual}"
        )
    return ""


def _request_contract_error(*, request_payload: dict[str, Any], required_action: str, status: str) -> str:
    has_contract_fields = any(key in request_payload for key in ("recommended_action", "allowed_actions", "blocked_actions"))
    if not has_contract_fields:
        return ""
    if not all(key in request_payload for key in ("recommended_action", "allowed_actions", "blocked_actions")):
        return "Approval request contract is incomplete; expected recommended_action, allowed_actions, and blocked_actions together."
    expected = _expected_contract(required_action=required_action, status=status)
    actual = {
        "recommended_action": str(request_payload.get("recommended_action") or "").strip(),
        "allowed_actions": _normalized_action_list(request_payload.get("allowed_actions")),
        "blocked_actions": _normalized_action_list(request_payload.get("blocked_actions")),
    }
    if actual != expected:
        return (
            "Approval request contract does not match the current request state. "
            f"expected={expected} actual={actual}"
        )
    return ""


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
        "recommended_action": "continue",
        "allowed_actions": [],
        "blocked_actions": [],
    }
    if isinstance(approval_state, dict):
        for key in state:
            if key in approval_state:
                state[key] = approval_state.get(key)

    request_path = out_dir / "approval-request.json"
    response_path = out_dir / "approval-response.json"
    request_payload = _read_json(request_path)
    response_payload = _read_json(response_path)
    request_id_from_request = ""

    if request_payload is not None:
        state["soft_gate"] = True
        state["required_action"] = str(request_payload.get("action") or state["required_action"] or "").strip()
        state["status"] = str(request_payload.get("status") or state["status"] or "pending").strip()
        state["reason"] = str(request_payload.get("reason") or state["reason"] or "").strip()
        state["request_id"] = str(request_payload.get("request_id") or state["request_id"] or "").strip()
        request_id_from_request = state["request_id"]
        state["request_path"] = str(request_path)
        request_contract_error = _request_contract_error(
            request_payload=request_payload,
            required_action=state["required_action"],
            status=state["status"],
        )
        if request_contract_error:
            state["status"] = "invalid"
            state["reason"] = request_contract_error

    if response_payload is not None:
        state["soft_gate"] = True
        response_decision = str(response_payload.get("decision") or state["decision"] or "").strip()
        response_reason = str(response_payload.get("reason") or state["reason"] or "").strip()
        response_request_id = str(response_payload.get("request_id") or state["request_id"] or "").strip()
        response_task_id = str(response_payload.get("task_id") or "").strip()
        response_run_id = str(response_payload.get("run_id") or "").strip()
        response_action = str(response_payload.get("action") or "").strip()
        state["decision"] = response_decision
        state["reason"] = response_reason
        state["response_path"] = str(response_path)
        if not request_id_from_request:
            state["status"] = "invalid"
            state["reason"] = response_reason or "Approval response exists without a matching approval request."
        elif response_action and response_action != state["required_action"]:
            state["status"] = "invalid"
            state["reason"] = (
                f"Approval response action '{response_action}' does not match current request action '{state['required_action']}'."
            )
        elif response_task_id and request_payload is not None and response_task_id != str(request_payload.get("task_id") or "").strip():
            state["status"] = "invalid"
            state["reason"] = (
                f"Approval response task_id '{response_task_id}' does not match current request task_id '{str(request_payload.get('task_id') or '').strip()}'."
            )
        elif response_run_id and request_payload is not None and response_run_id != str(request_payload.get("run_id") or "").strip():
            state["status"] = "invalid"
            state["reason"] = (
                f"Approval response run_id '{response_run_id}' does not match current request run_id '{str(request_payload.get('run_id') or '').strip()}'."
            )
        elif request_id_from_request and response_request_id and response_request_id != request_id_from_request:
            state["status"] = "mismatched"
            mismatch_reason = (
                f"Approval response request_id '{response_request_id}' does not match current request '{request_id_from_request}'."
            )
            state["reason"] = f"{mismatch_reason} {response_reason}".strip() if response_reason else mismatch_reason
        elif response_decision in {"approved", "denied"}:
            state["status"] = response_decision
            state["request_id"] = response_request_id
        elif state["status"] == "not-needed":
            state["status"] = "invalid"
            if response_reason:
                state["reason"] = response_reason
        contract_error = ""
        if state["status"] in {"approved", "denied"}:
            contract_error = _response_contract_error(
                response_payload=response_payload,
                required_action=state["required_action"],
                status=state["status"],
            )
        if contract_error:
            state["status"] = "invalid"
            state["reason"] = contract_error
        if state["status"] in {"invalid", "mismatched"}:
            state["request_id"] = request_id_from_request or response_request_id

    for key in ("required_action", "status", "decision", "reason", "request_id", "request_path", "response_path", "recommended_action"):
        state[key] = str(state.get(key) or "").strip()
    state["allowed_actions"] = [str(item).strip() for item in list(state.get("allowed_actions") or []) if str(item).strip()]
    state["blocked_actions"] = [str(item).strip() for item in list(state.get("blocked_actions") or []) if str(item).strip()]
    state["soft_gate"] = bool(state.get("soft_gate") or False)
    _apply_approval_action_contract(state)
    return state


def _apply_approval_action_contract(state: dict[str, Any]) -> None:
    required_action = str(state.get("required_action") or "").strip().lower()
    status = str(state.get("status") or "").strip().lower() or "not-needed"
    if required_action != "fork":
        state["recommended_action"] = "continue" if status == "not-needed" else "inspect"
        state["allowed_actions"] = ["continue"] if status == "not-needed" else ["inspect"]
        state["blocked_actions"] = []
        return
    if status == "pending":
        state["recommended_action"] = "pause"
        state["allowed_actions"] = ["inspect", "pause"]
        state["blocked_actions"] = ["fork", "resume", "rerun"]
        return
    if status == "approved":
        state["recommended_action"] = "fork"
        state["allowed_actions"] = ["fork", "inspect"]
        state["blocked_actions"] = ["resume", "rerun"]
        return
    if status == "denied":
        state["recommended_action"] = "resume"
        state["allowed_actions"] = ["resume", "inspect"]
        state["blocked_actions"] = ["fork"]
        return
    if status in {"invalid", "mismatched"}:
        state["recommended_action"] = "inspect"
        state["allowed_actions"] = ["inspect"]
        state["blocked_actions"] = ["fork", "resume", "rerun"]
        return
    state["recommended_action"] = "inspect"
    state["allowed_actions"] = ["inspect"]
    state["blocked_actions"] = []


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
