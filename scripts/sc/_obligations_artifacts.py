#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from _obligations_output_contract import SUMMARY_SCHEMA_VERSION, validate_summary_payload, write_checked_outputs


def _normalize_output_last_message(value: Any) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value if value is not None else {}, ensure_ascii=False, indent=2)
    return text.rstrip() + "\n"


def write_obligations_artifacts(
    *,
    out_dir: Path,
    summary: dict[str, Any],
    verdict: dict[str, Any],
    validate_verdict_schema: Callable[[dict[str, Any]], tuple[bool, list[str], dict[str, Any]]],
    report_text: str | None = None,
    trace_text: str | None = None,
    output_last_message: Any = None,
) -> tuple[bool, list[str], dict[str, Any], dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ok_write, out_errors, checked_summary, checked_verdict = write_checked_outputs(
        summary_path=out_dir / "summary.json",
        verdict_path=out_dir / "verdict.json",
        summary=summary,
        verdict=verdict,
        validate_verdict_schema=validate_verdict_schema,
        error_path=out_dir / "output-schema-errors.txt",
    )

    if report_text is not None:
        (out_dir / "report.md").write_text(str(report_text), encoding="utf-8")
    if trace_text is not None:
        (out_dir / "trace.log").write_text(str(trace_text), encoding="utf-8")
    if output_last_message is not None:
        (out_dir / "output-last-message.txt").write_text(_normalize_output_last_message(output_last_message), encoding="utf-8")

    return ok_write, out_errors, checked_summary, checked_verdict


def write_checked_and_sync_artifacts(
    *,
    out_dir: Path,
    summary_obj: dict[str, Any],
    verdict_obj: dict[str, Any],
    validate_verdict_schema: Callable[[dict[str, Any]], tuple[bool, list[str], dict[str, Any]]],
    report_text: str | None = None,
    trace_text: str | None = None,
    output_last_message: Any = None,
) -> bool:
    ok_write, _, checked_summary, checked_verdict = write_obligations_artifacts(
        out_dir=out_dir,
        summary=summary_obj,
        verdict=verdict_obj,
        validate_verdict_schema=validate_verdict_schema,
        report_text=report_text,
        trace_text=trace_text,
        output_last_message=output_last_message,
    )
    summary_obj.clear()
    summary_obj.update(checked_summary)
    verdict_obj.clear()
    verdict_obj.update(checked_verdict)
    return bool(ok_write)


def write_checked_summary_only_and_sync(*, out_dir: Path, summary_obj: dict[str, Any], error_file_name: str = "output-schema-errors.txt") -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    checked_summary = dict(summary_obj or {})
    checked_summary["schema_version"] = SUMMARY_SCHEMA_VERSION
    ok, errors, checked_summary = validate_summary_payload(checked_summary)
    if not ok:
        checked_summary["status"] = "fail"
        checked_summary["error"] = "output_schema_invalid"
        checked_summary["output_schema_errors"] = [f"summary:{x}" for x in errors]
        (out_dir / error_file_name).write_text("\n".join(checked_summary["output_schema_errors"]).strip() + "\n", encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(checked_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_obj.clear()
    summary_obj.update(checked_summary)
    return bool(ok)


def build_garbled_fail_report(*, task_id: str, hits: int, decode_errors: int, parse_errors: int, top_hits: list[str]) -> str:
    lines = [
        "# sc-llm-extract-task-obligations report",
        "",
        f"- task_id: {task_id}",
        "- status: fail",
        "- reason: garbled_precheck_failed",
        f"- suspicious_hits: {hits}",
        f"- decode_errors: {decode_errors}",
        f"- parse_errors: {parse_errors}",
        "",
        "## Top Hits",
        "",
    ]
    lines.extend([f"- {line}" for line in top_hits] or ["- (none)"])
    return "\n".join(lines).strip() + "\n"
