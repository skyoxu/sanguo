from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from _util import repo_root

try:
    import jsonschema  # type: ignore
except ImportError:  # pragma: no cover
    jsonschema = None


class SidecarSchemaError(RuntimeError):
    pass


def _schemas_dir() -> Path:
    return repo_root() / "scripts" / "sc" / "schemas"


def run_event_schema_path() -> Path:
    return _schemas_dir() / "sc-run-event.schema.json"


def harness_capabilities_schema_path() -> Path:
    return _schemas_dir() / "sc-harness-capabilities.schema.json"


def approval_request_schema_path() -> Path:
    return _schemas_dir() / "sc-approval-request.schema.json"


def approval_response_schema_path() -> Path:
    return _schemas_dir() / "sc-approval-response.schema.json"


def _load_schema(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise SidecarSchemaError(f"{label} schema not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SidecarSchemaError(f"invalid {label} schema JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SidecarSchemaError(f"{label} schema must be an object: {path}")
    return payload


def _format_path(path: list[Any]) -> str:
    if not path:
        return "$"
    parts = ["$"]
    for node in path:
        parts.append(f"[{node}]" if isinstance(node, int) else f".{node}")
    return "".join(parts)


def _validate_with_jsonschema(payload: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    assert jsonschema is not None
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{_format_path(list(err.path))}: {err.message}"
        for err in sorted(validator.iter_errors(payload), key=lambda x: (_format_path(list(x.path)), x.message))
    ]


def _build_error(label: str, errors: list[str]) -> SidecarSchemaError:
    joined = "\n".join(f"- {item}" for item in errors[:20])
    if len(errors) > 20:
        joined = f"{joined}\n- ... ({len(errors) - 20} more)"
    return SidecarSchemaError(f"{label} schema validation failed:\n{joined}")


def _require_string(payload: dict[str, Any], key: str, errors: list[str]) -> None:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"$.{key}: expected non-empty string")


def _require_bool(payload: dict[str, Any], key: str, errors: list[str]) -> None:
    if not isinstance(payload.get(key), bool):
        errors.append(f"$.{key}: expected boolean")


def _require_object(payload: dict[str, Any], key: str, errors: list[str]) -> None:
    if not isinstance(payload.get(key), dict):
        errors.append(f"$.{key}: expected object")


def _require_string_list(payload: dict[str, Any], key: str, errors: list[str]) -> None:
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        errors.append(f"$.{key}: expected array of non-empty strings")


def _validate_run_event_fallback(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("schema_version", "ts", "event", "task_id", "run_id", "delivery_profile", "security_profile"):
        _require_string(payload, key, errors)
    if payload.get("step_name") is not None and not isinstance(payload.get("step_name"), str):
        errors.append("$.step_name: expected string or null")
    if payload.get("status") is not None and not isinstance(payload.get("status"), str):
        errors.append("$.status: expected string or null")
    _require_object(payload, "details", errors)
    return errors


def _validate_harness_capabilities_fallback(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("schema_version", "protocol_version", "cmd", "task_id", "run_id", "delivery_profile", "security_profile"):
        _require_string(payload, key, errors)
    for key in ("supported_sidecars", "supported_recovery_actions"):
        _require_string_list(payload, key, errors)
    _require_bool(payload, "approval_contract_supported", errors)
    return errors


def _validate_approval_request_fallback(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("schema_version", "request_id", "task_id", "run_id", "action", "reason", "status"):
        _require_string(payload, key, errors)
    _require_string_list(payload, "requested_files", errors)
    _require_string_list(payload, "requested_commands", errors)
    if str(payload.get("status") or "").strip() != "pending":
        errors.append("$.status: expected 'pending'")
    return errors


def _validate_approval_response_fallback(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("schema_version", "request_id", "decision", "reviewer", "reason"):
        _require_string(payload, key, errors)
    if str(payload.get("decision") or "").strip() not in {"approved", "denied"}:
        errors.append("$.decision: expected 'approved' or 'denied'")
    return errors


def _validate_payload(
    *,
    payload: dict[str, Any],
    schema_path: Path,
    label: str,
    fallback_validator: Callable[[dict[str, Any]], list[str]],
) -> None:
    schema = _load_schema(schema_path, label)
    errors = _validate_with_jsonschema(payload, schema) if jsonschema is not None else fallback_validator(payload)
    if errors:
        raise _build_error(label, errors)


def validate_run_event_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=run_event_schema_path(),
        label="sc-run-event",
        fallback_validator=_validate_run_event_fallback,
    )


def validate_harness_capabilities_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=harness_capabilities_schema_path(),
        label="sc-harness-capabilities",
        fallback_validator=_validate_harness_capabilities_fallback,
    )


def validate_approval_request_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=approval_request_schema_path(),
        label="sc-approval-request",
        fallback_validator=_validate_approval_request_fallback,
    )


def validate_approval_response_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=approval_response_schema_path(),
        label="sc-approval-response",
        fallback_validator=_validate_approval_response_fallback,
    )
