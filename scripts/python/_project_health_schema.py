from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

try:
    import jsonschema  # type: ignore
except ImportError:  # pragma: no cover
    jsonschema = None


class ProjectHealthSchemaError(RuntimeError):
    pass


def _schemas_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts" / "sc" / "schemas"


def _dashboard_schema_path() -> Path:
    return _schemas_dir() / "sc-project-health-dashboard.schema.json"


def _report_catalog_schema_path() -> Path:
    return _schemas_dir() / "sc-project-health-report-catalog.schema.json"


def _server_schema_path() -> Path:
    return _schemas_dir() / "sc-project-health-server.schema.json"


def _record_schema_path() -> Path:
    return _schemas_dir() / "sc-project-health-record.schema.json"


def _scan_schema_path() -> Path:
    return _schemas_dir() / "sc-project-health-scan.schema.json"


def _load_schema(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise ProjectHealthSchemaError(f"{label} schema not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectHealthSchemaError(f"invalid {label} schema JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProjectHealthSchemaError(f"{label} schema must be an object: {path}")
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


def _build_error(label: str, errors: list[str]) -> ProjectHealthSchemaError:
    joined = "\n".join(f"- {item}" for item in errors[:20])
    if len(errors) > 20:
        joined = f"{joined}\n- ... ({len(errors) - 20} more)"
    return ProjectHealthSchemaError(f"{label} schema validation failed:\n{joined}")


def _require_string(payload: dict[str, Any], key: str, errors: list[str], *, allow_empty: bool = False) -> None:
    value = payload.get(key)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        errors.append(f"$.{key}: expected {'string' if allow_empty else 'non-empty string'}")


def _require_non_negative_int(payload: dict[str, Any], key: str, errors: list[str]) -> None:
    value = payload.get(key)
    if not isinstance(value, int) or value < 0:
        errors.append(f"$.{key}: expected integer >= 0")


def _validate_project_health_dashboard_fallback(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require_string(payload, "kind", errors)
    _require_string(payload, "status", errors)
    _require_string(payload, "generated_at", errors)
    if str(payload.get("kind") or "").strip() != "project-health-dashboard":
        errors.append("$.kind: expected 'project-health-dashboard'")
    if str(payload.get("status") or "").strip() not in {"ok", "warn", "fail"}:
        errors.append("$.status: expected 'ok', 'warn', or 'fail'")
    records = payload.get("records")
    if not isinstance(records, list):
        errors.append("$.records: expected array")
    else:
        for idx, item in enumerate(records):
            if not isinstance(item, dict):
                errors.append(f"$.records[{idx}]: expected object")
                continue
            for key in ("kind", "status", "latest_json", "history_json"):
                _require_string(item, key, errors)
            for key in ("summary", "stage"):
                _require_string(item, key, errors, allow_empty=True)
    report_catalog_summary = payload.get("report_catalog_summary")
    if not isinstance(report_catalog_summary, dict):
        errors.append("$.report_catalog_summary: expected object")
    else:
        _require_non_negative_int(report_catalog_summary, "total_json", errors)
        _require_non_negative_int(report_catalog_summary, "invalid_json", errors)
        _require_string(report_catalog_summary, "catalog_json", errors)
    active_task_summary = payload.get("active_task_summary")
    if not isinstance(active_task_summary, dict):
        errors.append("$.active_task_summary: expected object")
    else:
        _require_non_negative_int(active_task_summary, "total", errors)
        _require_non_negative_int(active_task_summary, "clean", errors)
        top_records = active_task_summary.get("top_records")
        if not isinstance(top_records, list):
            errors.append("$.active_task_summary.top_records: expected array")
        else:
            for idx, item in enumerate(top_records):
                if not isinstance(item, dict):
                    errors.append(f"$.active_task_summary.top_records[{idx}]: expected object")
                    continue
                for key in ("task_id", "status", "recommended_action"):
                    _require_string(item, key, errors)
    return errors


def _validate_project_health_report_catalog_fallback(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require_non_negative_int(payload, "total_json", errors)
    _require_non_negative_int(payload, "invalid_json", errors)
    entries = payload.get("entries")
    if not isinstance(entries, list):
        errors.append("$.entries: expected array")
        return errors
    for idx, item in enumerate(entries):
        if not isinstance(item, dict):
            errors.append(f"$.entries[{idx}]: expected object")
            continue
        for key in ("path", "kind"):
            _require_string(item, key, errors)
        for key in ("status", "generated_at", "summary", "modified_at", "parse_error"):
            _require_string(item, key, errors, allow_empty=True)
        size_bytes = item.get("size_bytes")
        if not isinstance(size_bytes, int) or size_bytes < 0:
            errors.append(f"$.entries[{idx}].size_bytes: expected integer >= 0")
        if not isinstance(item.get("highlights"), dict):
            errors.append(f"$.entries[{idx}].highlights: expected object")
    return errors


def _validate_project_health_server_fallback(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require_string(payload, "status", errors)
    if str(payload.get("status") or "").strip() != "ok":
        errors.append("$.status: expected 'ok'")
    if not isinstance(payload.get("reused"), bool):
        errors.append("$.reused: expected boolean")
    _require_string(payload, "host", errors)
    port = payload.get("port")
    if not isinstance(port, int) or port <= 0:
        errors.append("$.port: expected integer > 0")
    pid = payload.get("pid")
    if not isinstance(pid, int) or pid < 0:
        errors.append("$.pid: expected integer >= 0")
    for key in ("url", "repo_root", "served_dir", "started_at"):
        _require_string(payload, key, errors)
    return errors


def _validate_project_health_record_fallback(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    kind = str(payload.get("kind") or "").strip()
    _require_string(payload, "kind", errors)
    _require_string(payload, "status", errors)
    _require_string(payload, "summary", errors, allow_empty=True)
    _require_string(payload, "generated_at", errors)
    _require_string(payload, "history_json", errors)
    _require_string(payload, "latest_json", errors)
    exit_code = payload.get("exit_code")
    if not isinstance(exit_code, int) or exit_code < 0:
        errors.append("$.exit_code: expected integer >= 0")

    if kind == "detect-project-stage":
        _require_string(payload, "stage", errors)
        signals = payload.get("signals")
        if not isinstance(signals, dict):
            errors.append("$.signals: expected object")
        else:
            for key in ("project_godot", "readme", "agents", "real_task_triplet", "example_task_triplet"):
                if not isinstance(signals.get(key), bool):
                    errors.append(f"$.signals.{key}: expected boolean")
            for key in ("overlay_indexes", "contract_files", "unit_test_files"):
                value = signals.get(key)
                if not isinstance(value, int) or value < 0:
                    errors.append(f"$.signals.{key}: expected integer >= 0")
            counts = signals.get("task_status_counts")
            if counts is not None:
                if not isinstance(counts, dict):
                    errors.append("$.signals.task_status_counts: expected object")
                else:
                    for key in ("in_progress", "done", "other"):
                        value = counts.get(key)
                        if not isinstance(value, int) or value < 0:
                            errors.append(f"$.signals.task_status_counts.{key}: expected integer >= 0")
        paths = payload.get("paths")
        if not isinstance(paths, dict):
            errors.append("$.paths: expected object")
        else:
            for section in ("real_task_triplet", "example_task_triplet"):
                triplet = paths.get(section)
                if not isinstance(triplet, dict):
                    errors.append(f"$.paths.{section}: expected object")
                    continue
                for key in ("tasks.json", "tasks_back.json", "tasks_gameplay.json"):
                    _require_string(triplet, key, errors)
        return errors

    if kind == "doctor-project":
        counts = payload.get("counts")
        if not isinstance(counts, dict):
            errors.append("$.counts: expected object")
        else:
            for key in ("fail", "warn", "ok"):
                value = counts.get(key)
                if not isinstance(value, int) or value < 0:
                    errors.append(f"$.counts.{key}: expected integer >= 0")
        checks = payload.get("checks")
        if not isinstance(checks, list):
            errors.append("$.checks: expected array")
        else:
            for idx, item in enumerate(checks):
                if not isinstance(item, dict):
                    errors.append(f"$.checks[{idx}]: expected object")
                    continue
                for key in ("id", "status", "path", "summary", "recommendation"):
                    _require_string(item, key, errors, allow_empty=(key == "summary"))
        return errors

    if kind == "check-directory-boundaries":
        rules_checked = payload.get("rules_checked")
        if not isinstance(rules_checked, list):
            errors.append("$.rules_checked: expected array")
        else:
            for idx, item in enumerate(rules_checked):
                if not isinstance(item, str) or not item.strip():
                    errors.append(f"$.rules_checked[{idx}]: expected non-empty string")
        for group_name in ("violations", "warnings"):
            group = payload.get(group_name)
            if not isinstance(group, list):
                errors.append(f"$.{group_name}: expected array")
                continue
            for idx, item in enumerate(group):
                if not isinstance(item, dict):
                    errors.append(f"$.{group_name}[{idx}]: expected object")
                    continue
                for key in ("rule_id", "path", "summary"):
                    _require_string(item, key, errors, allow_empty=(key == "summary"))
        return errors

    errors.append("$.kind: expected 'detect-project-stage', 'doctor-project', or 'check-directory-boundaries'")
    return errors


def _validate_project_health_scan_fallback(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require_string(payload, "kind", errors)
    _require_string(payload, "status", errors)
    if str(payload.get("kind") or "").strip() != "project-health-scan":
        errors.append("$.kind: expected 'project-health-scan'")
    if str(payload.get("status") or "").strip() not in {"ok", "warn", "fail"}:
        errors.append("$.status: expected 'ok', 'warn', or 'fail'")
    exit_code = payload.get("exit_code")
    if not isinstance(exit_code, int) or exit_code < 0:
        errors.append("$.exit_code: expected integer >= 0")
    results = payload.get("results")
    if not isinstance(results, list):
        errors.append("$.results: expected array")
        return errors
    for idx, item in enumerate(results):
        if not isinstance(item, dict):
            errors.append(f"$.results[{idx}]: expected object")
            continue
        kind = str(item.get("kind") or "").strip()
        if kind == "detect-project-stage":
            for key in ("status", "stage"):
                if not isinstance(item.get(key), str) or not str(item.get(key)).strip():
                    errors.append(f"$.results[{idx}].{key}: expected non-empty string")
            if not isinstance(item.get("exit_code"), int) or int(item.get("exit_code")) < 0:
                errors.append(f"$.results[{idx}].exit_code: expected integer >= 0")
            if not isinstance(item.get("signals"), dict):
                errors.append(f"$.results[{idx}].signals: expected object")
            if not isinstance(item.get("paths"), dict):
                errors.append(f"$.results[{idx}].paths: expected object")
            continue
        if kind == "doctor-project":
            if not isinstance(item.get("status"), str) or not str(item.get("status")).strip():
                errors.append(f"$.results[{idx}].status: expected non-empty string")
            if not isinstance(item.get("exit_code"), int) or int(item.get("exit_code")) < 0:
                errors.append(f"$.results[{idx}].exit_code: expected integer >= 0")
            if not isinstance(item.get("counts"), dict):
                errors.append(f"$.results[{idx}].counts: expected object")
            if not isinstance(item.get("checks"), list):
                errors.append(f"$.results[{idx}].checks: expected array")
            continue
        if kind == "check-directory-boundaries":
            if not isinstance(item.get("status"), str) or not str(item.get("status")).strip():
                errors.append(f"$.results[{idx}].status: expected non-empty string")
            if not isinstance(item.get("exit_code"), int) or int(item.get("exit_code")) < 0:
                errors.append(f"$.results[{idx}].exit_code: expected integer >= 0")
            if not isinstance(item.get("violations"), list):
                errors.append(f"$.results[{idx}].violations: expected array")
            if not isinstance(item.get("warnings"), list):
                errors.append(f"$.results[{idx}].warnings: expected array")
            if not isinstance(item.get("rules_checked"), list):
                errors.append(f"$.results[{idx}].rules_checked: expected array")
            continue
        errors.append(f"$.results[{idx}].kind: expected supported project-health result kind")
    return errors


def _validate_payload(*, payload: dict[str, Any], schema_path: Path, label: str, fallback_validator: Callable[[dict[str, Any]], list[str]]) -> None:
    schema = _load_schema(schema_path, label)
    errors = _validate_with_jsonschema(payload, schema) if jsonschema is not None else fallback_validator(payload)
    if errors:
        raise _build_error(label, errors)


def validate_project_health_dashboard_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=_dashboard_schema_path(),
        label="sc-project-health-dashboard",
        fallback_validator=_validate_project_health_dashboard_fallback,
    )


def validate_project_health_report_catalog_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=_report_catalog_schema_path(),
        label="sc-project-health-report-catalog",
        fallback_validator=_validate_project_health_report_catalog_fallback,
    )


def validate_project_health_server_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=_server_schema_path(),
        label="sc-project-health-server",
        fallback_validator=_validate_project_health_server_fallback,
    )


def validate_project_health_record_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=_record_schema_path(),
        label="sc-project-health-record",
        fallback_validator=_validate_project_health_record_fallback,
    )


def validate_project_health_scan_payload(payload: dict[str, Any]) -> None:
    _validate_payload(
        payload=payload,
        schema_path=_scan_schema_path(),
        label="sc-project-health-scan",
        fallback_validator=_validate_project_health_scan_fallback,
    )
