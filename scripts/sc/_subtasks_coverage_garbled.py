#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any

from _garbled_gate import render_top_hits, scan_task_text_integrity  # type: ignore
from _util import write_json, write_text  # type: ignore


def run_subtasks_coverage_garbled_precheck(
    *,
    task_id: str,
    out_dir: Path,
    summary: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    task_filter: set[int] = set()
    try:
        task_filter.add(int(task_id))
    except (TypeError, ValueError):
        pass
    precheck = scan_task_text_integrity(task_ids=(task_filter or None))
    write_json(out_dir / "garbled-precheck.json", precheck)
    pre_summary = precheck.get("summary") if isinstance(precheck, dict) else {}
    hits = int((pre_summary or {}).get("suspicious_hits") or 0)
    decode_errors = int((pre_summary or {}).get("decode_errors") or 0)
    parse_errors = int((pre_summary or {}).get("parse_errors") or 0)
    summary["garbled_precheck"] = pre_summary
    if decode_errors > 0 or parse_errors > 0 or hits > 0:
        top_hits = render_top_hits(precheck, limit=8) if isinstance(precheck, dict) else []
        summary["status"] = "fail"
        summary["error"] = "garbled_precheck_failed"
        summary["garbled_top_hits"] = top_hits
        write_json(out_dir / "summary.json", summary)
        write_text(
            out_dir / "report.md",
            f"# T{task_id} subtasks coverage\n\nStatus: fail\n\nError: garbled_precheck_failed\n\nHits: {hits}\n",
        )
        return False, summary
    return True, summary
