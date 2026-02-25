#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

SUMMARY_SCHEMA_VERSION = "sc-llm-obligations-summary-v1"
VERDICT_SCHEMA_VERSION = "sc-llm-obligations-verdict-v1"


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def validate_summary_payload(summary: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    errors: list[str] = []
    obj = dict(summary or {})

    if str(obj.get("schema_version") or "").strip() != SUMMARY_SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if not str(obj.get("cmd") or "").strip():
        errors.append("cmd_missing")
    if not str(obj.get("task_id") or "").strip():
        errors.append("task_id_missing")
    if not str(obj.get("prompt_version") or "").strip():
        errors.append("prompt_version_missing")
    if not str(obj.get("runtime_code_fingerprint") or "").strip():
        errors.append("runtime_code_fingerprint_missing")
    if not str(obj.get("reuse_lookup_key") or "").strip():
        errors.append("reuse_lookup_key_missing")

    status = obj.get("status")
    if status not in {None, "ok", "fail"}:
        errors.append("status_invalid")

    error = obj.get("error")
    if error is not None and not isinstance(error, str):
        errors.append("error_invalid")

    if not isinstance(obj.get("run_results"), list):
        errors.append("run_results_not_list")
    if not isinstance(obj.get("acceptance_counts"), dict):
        errors.append("acceptance_counts_not_object")

    if not isinstance(obj.get("reuse_index_hit"), bool):
        errors.append("reuse_index_hit_invalid")
    if not isinstance(obj.get("reuse_index_fallback_scan"), bool):
        errors.append("reuse_index_fallback_scan_invalid")
    if not isinstance(obj.get("reuse_index_pruned_count"), int) or int(obj.get("reuse_index_pruned_count")) < 0:
        errors.append("reuse_index_pruned_count_invalid")
    if not isinstance(obj.get("reuse_index_lock_wait_ms"), int) or int(obj.get("reuse_index_lock_wait_ms")) < 0:
        errors.append("reuse_index_lock_wait_ms_invalid")

    schema_errors = obj.get("schema_errors")
    if not _is_string_list(schema_errors):
        errors.append("schema_errors_not_string_list")
    schema_error_codes = obj.get("schema_error_codes")
    if not _is_string_list(schema_error_codes):
        errors.append("schema_error_codes_not_string_list")

    schema_error_buckets = obj.get("schema_error_buckets")
    if not isinstance(schema_error_buckets, dict):
        errors.append("schema_error_buckets_not_object")
    else:
        for k, v in schema_error_buckets.items():
            if not str(k or "").strip() or not isinstance(v, int):
                errors.append("schema_error_buckets_invalid_item")
                break

    schema_error_count = obj.get("schema_error_count")
    if not isinstance(schema_error_count, int) or int(schema_error_count) < 0:
        errors.append("schema_error_count_invalid")

    rc = obj.get("rc")
    if not isinstance(rc, int):
        errors.append("rc_invalid")

    return not errors, errors, obj


def validate_verdict_payload(
    verdict: dict[str, Any],
    *,
    validate_verdict_schema: Callable[[dict[str, Any]], tuple[bool, list[str], dict[str, Any]]],
) -> tuple[bool, list[str], dict[str, Any]]:
    obj = dict(verdict or {})
    errors: list[str] = []
    if str(obj.get("schema_version") or "").strip() != VERDICT_SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    payload = dict(obj)
    payload.pop("schema_version", None)
    ok, schema_errors, normalized = validate_verdict_schema(payload)
    if not ok:
        errors.extend([f"verdict:{x}" for x in schema_errors])
    normalized["schema_version"] = VERDICT_SCHEMA_VERSION
    return not errors, errors, normalized


def prepare_checked_outputs(
    *,
    summary: dict[str, Any],
    verdict: dict[str, Any],
    validate_verdict_schema: Callable[[dict[str, Any]], tuple[bool, list[str], dict[str, Any]]],
) -> tuple[bool, list[str], dict[str, Any], dict[str, Any]]:
    summary_obj = dict(summary or {})
    summary_obj["schema_version"] = SUMMARY_SCHEMA_VERSION

    verdict_obj = dict(verdict or {})
    verdict_obj["schema_version"] = VERDICT_SCHEMA_VERSION

    ok_summary, summary_errors, summary_checked = validate_summary_payload(summary_obj)
    ok_verdict, verdict_errors, verdict_checked = validate_verdict_payload(verdict_obj, validate_verdict_schema=validate_verdict_schema)

    errors = [f"summary:{x}" for x in summary_errors] + [f"verdict:{x}" for x in verdict_errors]
    return (ok_summary and ok_verdict), errors, summary_checked, verdict_checked


def write_checked_outputs(
    *,
    summary_path: Path,
    verdict_path: Path,
    summary: dict[str, Any],
    verdict: dict[str, Any],
    validate_verdict_schema: Callable[[dict[str, Any]], tuple[bool, list[str], dict[str, Any]]],
    error_path: Path | None = None,
) -> tuple[bool, list[str], dict[str, Any], dict[str, Any]]:
    ok_out, out_errors, checked_summary, checked_verdict = prepare_checked_outputs(
        summary=summary,
        verdict=verdict,
        validate_verdict_schema=validate_verdict_schema,
    )
    if not ok_out:
        checked_summary["status"] = "fail"
        checked_summary["error"] = "output_schema_invalid"
        checked_summary["output_schema_errors"] = out_errors

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    verdict_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(checked_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verdict_path.write_text(json.dumps(checked_verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not ok_out and error_path is not None:
        error_path.parent.mkdir(parents=True, exist_ok=True)
        error_path.write_text("\n".join(out_errors).strip() + "\n", encoding="utf-8")

    return ok_out, out_errors, checked_summary, checked_verdict
