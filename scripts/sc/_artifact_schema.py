from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from _artifact_schema_fallback import (
    validate_local_execution_context_without_jsonschema,
    validate_local_latest_index_without_jsonschema,
    validate_local_repair_guide_without_jsonschema,
    validate_pipeline_execution_context_without_jsonschema,
    validate_pipeline_latest_index_without_jsonschema,
    validate_pipeline_repair_guide_without_jsonschema,
)
from _util import repo_root

try:
    import jsonschema  # type: ignore
except ImportError:  # pragma: no cover
    jsonschema = None


class ArtifactSchemaError(RuntimeError):
    pass


def _schemas_dir() -> Path:
    return repo_root() / "scripts" / "sc" / "schemas"


def pipeline_execution_context_schema_path() -> Path:
    return _schemas_dir() / "sc-review-execution-context.schema.json"


def pipeline_repair_guide_schema_path() -> Path:
    return _schemas_dir() / "sc-review-repair-guide.schema.json"


def pipeline_latest_index_schema_path() -> Path:
    return _schemas_dir() / "sc-review-latest-index.schema.json"


def local_execution_context_schema_path() -> Path:
    return _schemas_dir() / "sc-local-hard-checks-execution-context.schema.json"


def local_repair_guide_schema_path() -> Path:
    return _schemas_dir() / "sc-local-hard-checks-repair-guide.schema.json"


def local_latest_index_schema_path() -> Path:
    return _schemas_dir() / "sc-local-hard-checks-latest-index.schema.json"


def _load_schema(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise ArtifactSchemaError(f"{label} schema not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArtifactSchemaError(f"invalid {label} schema JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ArtifactSchemaError(f"{label} schema must be an object: {path}")
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


def _build_error(label: str, errors: list[str]) -> ArtifactSchemaError:
    joined = "\n".join(f"- {item}" for item in errors[:20])
    if len(errors) > 20:
        joined = f"{joined}\n- ... ({len(errors) - 20} more)"
    return ArtifactSchemaError(f"{label} schema validation failed:\n{joined}")


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


def validate_pipeline_execution_context_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=pipeline_execution_context_schema_path(),
        label="sc-review execution-context",
        fallback_validator=validate_pipeline_execution_context_without_jsonschema,
    )


def validate_pipeline_repair_guide_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=pipeline_repair_guide_schema_path(),
        label="sc-review repair-guide",
        fallback_validator=validate_pipeline_repair_guide_without_jsonschema,
    )


def validate_pipeline_latest_index_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=pipeline_latest_index_schema_path(),
        label="sc-review latest-index",
        fallback_validator=validate_pipeline_latest_index_without_jsonschema,
    )


def validate_local_hard_checks_execution_context_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=local_execution_context_schema_path(),
        label="local-hard-checks execution-context",
        fallback_validator=validate_local_execution_context_without_jsonschema,
    )


def validate_local_hard_checks_repair_guide_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=local_repair_guide_schema_path(),
        label="local-hard-checks repair-guide",
        fallback_validator=validate_local_repair_guide_without_jsonschema,
    )


def validate_local_hard_checks_latest_index_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=local_latest_index_schema_path(),
        label="local-hard-checks latest-index",
        fallback_validator=validate_local_latest_index_without_jsonschema,
    )
