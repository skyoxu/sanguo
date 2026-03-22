from __future__ import annotations

from pathlib import Path
from typing import Any

from _sidecar_schema import validate_harness_capabilities_payload
from _util import write_json

SCHEMA_VERSION = "1.0.0"
PROTOCOL_VERSION = "1.0.0"
SUPPORTED_SIDECARS = [
    "summary.json",
    "execution-context.json",
    "repair-guide.json",
    "repair-guide.md",
    "marathon-state.json",
    "run-events.jsonl",
    "harness-capabilities.json",
    "approval-request.json",
    "approval-response.json",
    "agent-review.json",
    "agent-review.md",
]
SUPPORTED_RECOVERY_ACTIONS = ["resume", "refresh", "fork", "abort"]


def harness_capabilities_path(out_dir: Path) -> Path:
    return out_dir / "harness-capabilities.json"


def build_harness_capabilities(
    *,
    cmd: str,
    task_id: str,
    run_id: str,
    delivery_profile: str,
    security_profile: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "cmd": str(cmd).strip(),
        "task_id": str(task_id).strip(),
        "run_id": str(run_id).strip(),
        "delivery_profile": str(delivery_profile).strip(),
        "security_profile": str(security_profile).strip(),
        "supported_sidecars": list(SUPPORTED_SIDECARS),
        "supported_recovery_actions": list(SUPPORTED_RECOVERY_ACTIONS),
        "approval_contract_supported": True,
    }
    validate_harness_capabilities_payload(payload)
    return payload


def write_harness_capabilities(
    *,
    out_dir: Path,
    cmd: str,
    task_id: str,
    run_id: str,
    delivery_profile: str,
    security_profile: str,
) -> dict[str, Any]:
    payload = build_harness_capabilities(
        cmd=cmd,
        task_id=task_id,
        run_id=run_id,
        delivery_profile=delivery_profile,
        security_profile=security_profile,
    )
    write_json(harness_capabilities_path(out_dir), payload)
    return payload
