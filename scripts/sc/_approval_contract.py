from __future__ import annotations

from pathlib import Path
from typing import Any

from _sidecar_schema import validate_approval_request_payload, validate_approval_response_payload
from _util import write_json

SCHEMA_VERSION = "1.0.0"


def approval_request_path(out_dir: Path) -> Path:
    return out_dir / "approval-request.json"


def approval_response_path(out_dir: Path) -> Path:
    return out_dir / "approval-response.json"


def build_approval_request(
    *,
    task_id: str,
    run_id: str,
    action: str,
    reason: str,
    requested_files: list[str] | None = None,
    requested_commands: list[str] | None = None,
    request_id: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "request_id": str(request_id).strip(),
        "task_id": str(task_id).strip(),
        "run_id": str(run_id).strip(),
        "action": str(action).strip(),
        "reason": str(reason).strip(),
        "requested_files": [str(item).strip() for item in (requested_files or []) if str(item).strip()],
        "requested_commands": [str(item).strip() for item in (requested_commands or []) if str(item).strip()],
        "status": "pending",
    }
    validate_approval_request_payload(payload)
    return payload


def build_approval_response(
    *,
    request_id: str,
    decision: str,
    reviewer: str,
    reason: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "request_id": str(request_id).strip(),
        "decision": str(decision).strip(),
        "reviewer": str(reviewer).strip(),
        "reason": str(reason).strip(),
    }
    validate_approval_response_payload(payload)
    return payload


def write_approval_request(
    *,
    out_dir: Path,
    task_id: str,
    run_id: str,
    action: str,
    reason: str,
    requested_files: list[str] | None = None,
    requested_commands: list[str] | None = None,
    request_id: str,
) -> dict[str, Any]:
    payload = build_approval_request(
        task_id=task_id,
        run_id=run_id,
        action=action,
        reason=reason,
        requested_files=requested_files,
        requested_commands=requested_commands,
        request_id=request_id,
    )
    write_json(approval_request_path(out_dir), payload)
    return payload


def write_approval_response(
    *,
    out_dir: Path,
    request_id: str,
    decision: str,
    reviewer: str,
    reason: str,
) -> dict[str, Any]:
    payload = build_approval_response(
        request_id=request_id,
        decision=decision,
        reviewer=reviewer,
        reason=reason,
    )
    write_json(approval_response_path(out_dir), payload)
    return payload
