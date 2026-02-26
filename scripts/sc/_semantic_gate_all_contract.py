#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from collections.abc import Callable
from typing import Any


SUMMARY_SCHEMA_VERSION = "semantic-gate-all.v1"


def evaluate_semantic_gate_exit(
    *,
    needs_fix_count: int,
    unknown_count: int,
    max_needs_fix: int,
    max_unknown: int,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if int(needs_fix_count) > int(max_needs_fix):
        reasons.append(f"needs_fix_exceeds_limit:{needs_fix_count}>{max_needs_fix}")
    if int(unknown_count) > int(max_unknown):
        reasons.append(f"unknown_exceeds_limit:{unknown_count}>{max_unknown}")
    return bool(reasons), reasons


def validate_semantic_gate_summary(summary: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    errors: list[str] = []
    obj = dict(summary or {})
    obj["schema_version"] = SUMMARY_SCHEMA_VERSION

    required_top = {
        "cmd": str,
        "date": str,
        "batches": int,
        "batch_size": int,
        "total_tasks": int,
        "needs_fix": list,
        "unknown": list,
        "findings": list,
        "counts": dict,
        "status": str,
        "max_needs_fix": int,
        "max_unknown": int,
        "fail_reasons": list,
    }
    for key, typ in required_top.items():
        if key not in obj:
            errors.append(f"missing:{key}")
            continue
        if not isinstance(obj[key], typ):
            errors.append(f"type:{key}")

    counts = obj.get("counts")
    if isinstance(counts, dict):
        for k in ("ok", "needs_fix", "unknown"):
            if k not in counts:
                errors.append(f"counts_missing:{k}")
            elif not isinstance(counts[k], int):
                errors.append(f"counts_type:{k}")
    else:
        errors.append("counts_not_object")

    findings = obj.get("findings")
    if isinstance(findings, list):
        for i, row in enumerate(findings, start=1):
            if not isinstance(row, dict):
                errors.append(f"finding_not_object:{i}")
                continue
            if not isinstance(row.get("task_id"), int):
                errors.append(f"finding_task_id_type:{i}")
            if str(row.get("verdict") or "") not in {"OK", "Needs Fix", "Unknown"}:
                errors.append(f"finding_verdict_invalid:{i}")
            if not isinstance(row.get("reason"), str):
                errors.append(f"finding_reason_type:{i}")
    else:
        errors.append("findings_not_list")

    return not errors, errors, obj


def run_semantic_gate_all_self_check(
    *,
    parse_tsv_output: Callable[[str], list[Any]],
) -> tuple[bool, dict[str, Any], str]:
    checks: list[dict[str, Any]] = []

    parsed = parse_tsv_output("T1\tOK\tgood\nT2\\tNeeds Fix\\tmissing")
    parse_ok = (
        len(parsed) == 2
        and getattr(parsed[0], "task_id", None) == 1
        and getattr(parsed[0], "verdict", "") == "OK"
        and getattr(parsed[1], "task_id", None) == 2
        and getattr(parsed[1], "verdict", "") == "Needs Fix"
    )
    checks.append({"name": "parse_tsv", "ok": bool(parse_ok)})

    sample_summary = {
        "cmd": "sc-semantic-gate-all",
        "date": "2026-02-24",
        "batches": 1,
        "batch_size": 8,
        "total_tasks": 2,
        "counts": {"ok": 1, "needs_fix": 1, "unknown": 0},
        "needs_fix": [2],
        "unknown": [],
        "findings": [
            {"task_id": 1, "verdict": "OK", "reason": "ok"},
            {"task_id": 2, "verdict": "Needs Fix", "reason": "missing"},
        ],
        "status": "fail",
        "max_needs_fix": 0,
        "max_unknown": 0,
        "fail_reasons": ["needs_fix_exceeds_limit:1>0"],
    }
    summary_ok, summary_errors, checked = validate_semantic_gate_summary(sample_summary)
    checks.append({"name": "summary_contract", "ok": bool(summary_ok), "errors": summary_errors})

    exit_fail, _ = evaluate_semantic_gate_exit(needs_fix_count=1, unknown_count=0, max_needs_fix=0, max_unknown=0)
    checks.append({"name": "exit_policy", "ok": bool(exit_fail)})

    ok = all(bool(c.get("ok")) for c in checks)
    payload = {
        "cmd": "sc-semantic-gate-all-self-check",
        "status": "ok" if ok else "fail",
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "checks": checks,
        "summary_schema_version": checked.get("schema_version"),
    }
    lines = [
        "# sc-semantic-gate-all self-check",
        "",
        f"- status: {payload['status']}",
        f"- schema_version: {payload['schema_version']}",
        "",
        "## Checks",
    ]
    for item in checks:
        lines.append(f"- {item.get('name')}: {'ok' if item.get('ok') else 'fail'}")
    return ok, payload, "\n".join(lines) + "\n"

