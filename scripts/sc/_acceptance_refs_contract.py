#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


SUMMARY_SCHEMA_VERSION = "acceptance-refs.v1"


def validate_fill_acceptance_summary(summary: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    errors: list[str] = []
    obj = dict(summary or {})
    obj["schema_version"] = SUMMARY_SCHEMA_VERSION

    required = {
        "cmd": str,
        "date": str,
        "write": bool,
        "overwrite_existing": bool,
        "rewrite_placeholders": bool,
        "tasks": int,
        "any_updates": int,
        "results": list,
        "missing_after_write": int,
        "out_dir": str,
        "status": str,
        "consensus_runs": int,
        "prd_source": str,
    }
    for key, typ in required.items():
        if key not in obj:
            errors.append(f"missing:{key}")
            continue
        if not isinstance(obj.get(key), typ):
            errors.append(f"type:{key}")

    status = str(obj.get("status") or "").strip()
    if status not in {"ok", "fail"}:
        errors.append("status_invalid")

    results = obj.get("results")
    if isinstance(results, list):
        for idx, item in enumerate(results, start=1):
            if not isinstance(item, dict):
                errors.append(f"result_not_object:{idx}")
                continue
            if not isinstance(item.get("task_id"), int):
                errors.append(f"result_task_id_type:{idx}")
            item_status = str(item.get("status") or "").strip()
            if item_status not in {"ok", "fail", "skipped"}:
                errors.append(f"result_status_invalid:{idx}")
    else:
        errors.append("results_not_list")
    return not errors, errors, obj


def run_fill_acceptance_refs_self_check(
    *,
    is_allowed_test_path,
    parse_model_items_to_paths,
    validate_summary=validate_fill_acceptance_summary,
) -> tuple[bool, dict[str, Any], str]:
    checks: list[dict[str, Any]] = []

    checks.append({"name": "allowed_path_cs", "ok": bool(is_allowed_test_path("Game.Core.Tests/Domain/FooTests.cs"))})
    checks.append({"name": "reject_docs_path", "ok": not bool(is_allowed_test_path("docs/spec.md"))})

    parsed = parse_model_items_to_paths(
        items=[{"view": "back", "index": 0, "paths": ["Game.Core.Tests/Domain/FooTests.cs"]}],
        max_refs_per_item=2,
    )
    checks.append({"name": "parse_model_items", "ok": bool(parsed.get("back", {}).get(0))})

    summary = {
        "cmd": "sc-llm-fill-acceptance-refs",
        "date": "2026-02-24",
        "write": False,
        "overwrite_existing": False,
        "rewrite_placeholders": False,
        "tasks": 1,
        "any_updates": 0,
        "results": [{"task_id": 1, "status": "ok"}],
        "missing_after_write": 0,
        "out_dir": "logs/ci/2026-02-24/sc-llm-acceptance-refs",
        "status": "ok",
        "consensus_runs": 1,
        "prd_source": ".taskmaster/docs/prd.txt",
    }
    summary_ok, summary_errors, checked = validate_summary(summary)
    checks.append({"name": "summary_contract", "ok": bool(summary_ok), "errors": summary_errors})

    ok = all(bool(item.get("ok")) for item in checks)
    payload = {
        "cmd": "sc-llm-fill-acceptance-refs-self-check",
        "status": "ok" if ok else "fail",
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "checks": checks,
        "summary_schema_version": checked.get("schema_version"),
    }
    report_lines = [
        "# sc-llm-fill-acceptance-refs self-check",
        "",
        f"- status: {payload['status']}",
        f"- schema_version: {payload['schema_version']}",
        "",
        "## Checks",
    ]
    report_lines.extend([f"- {item.get('name')}: {'ok' if item.get('ok') else 'fail'}" for item in checks])
    return ok, payload, "\n".join(report_lines) + "\n"

