from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from _summary_schema_fallback import (
    validate_local_hard_checks_without_jsonschema,
    validate_pipeline_without_jsonschema,
    validate_sc_acceptance_without_jsonschema,
    validate_sc_test_without_jsonschema,
)
from _util import repo_root

try:
    import jsonschema  # type: ignore
except ImportError:  # pragma: no cover
    jsonschema = None


class SummarySchemaError(RuntimeError):
    pass


def _schemas_dir() -> Path:
    return repo_root() / "scripts" / "sc" / "schemas"


def pipeline_summary_schema_path() -> Path:
    return _schemas_dir() / "sc-review-pipeline-summary.schema.json"


def sc_test_summary_schema_path() -> Path:
    return _schemas_dir() / "sc-test-summary.schema.json"


def sc_acceptance_summary_schema_path() -> Path:
    return _schemas_dir() / "sc-acceptance-check-summary.schema.json"


def local_hard_checks_summary_schema_path() -> Path:
    return _schemas_dir() / "sc-local-hard-checks-summary.schema.json"


def _load_schema(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise SummarySchemaError(f"{label} schema not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SummarySchemaError(f"invalid {label} schema JSON: {path}: {exc}") from exc


def _format_path(path: list[Any]) -> str:
    if not path:
        return "$"
    parts = ["$"]
    for node in path:
        if isinstance(node, int):
            parts.append(f"[{node}]")
        else:
            parts.append(f".{node}")
    return "".join(parts)


def _validate_with_jsonschema(payload: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    assert jsonschema is not None
    validator = jsonschema.Draft202012Validator(schema)
    errors: list[str] = []
    for err in sorted(validator.iter_errors(payload), key=lambda x: (_format_path(list(x.path)), x.message)):
        errors.append(f"{_format_path(list(err.path))}: {err.message}")
    return errors


def _build_error(label: str, errors: list[str]) -> SummarySchemaError:
    joined = "\n".join(f"- {line}" for line in errors[:20])
    if len(errors) > 20:
        joined = f"{joined}\n- ... ({len(errors) - 20} more)"
    return SummarySchemaError(f"{label} schema validation failed:\n{joined}")


def _validate_summary(
    *,
    payload: dict[str, Any],
    schema_path: Path,
    label: str,
    fallback_validator: Callable[[dict[str, Any]], list[str]],
) -> None:
    schema = _load_schema(schema_path, label)
    if jsonschema is not None:
        errors = _validate_with_jsonschema(payload, schema)
    else:
        errors = fallback_validator(payload)
    if errors:
        raise _build_error(label, errors)


def validate_pipeline_summary(payload: dict[str, Any]) -> None:
    _validate_summary(
        payload=payload,
        schema_path=pipeline_summary_schema_path(),
        label="sc-review-pipeline summary",
        fallback_validator=validate_pipeline_without_jsonschema,
    )


def validate_sc_test_summary(payload: dict[str, Any]) -> None:
    _validate_summary(
        payload=payload,
        schema_path=sc_test_summary_schema_path(),
        label="sc-test summary",
        fallback_validator=validate_sc_test_without_jsonschema,
    )


def validate_sc_acceptance_summary(payload: dict[str, Any]) -> None:
    _validate_summary(
        payload=payload,
        schema_path=sc_acceptance_summary_schema_path(),
        label="sc-acceptance-check summary",
        fallback_validator=validate_sc_acceptance_without_jsonschema,
    )


def validate_local_hard_checks_summary(payload: dict[str, Any]) -> None:
    _validate_summary(
        payload=payload,
        schema_path=local_hard_checks_summary_schema_path(),
        label="local-hard-checks summary",
        fallback_validator=validate_local_hard_checks_without_jsonschema,
    )
