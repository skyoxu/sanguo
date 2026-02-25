#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from _obligations_extract_helpers import (
    collect_auto_escalation_reasons,
    extract_json_object,
    extract_schema_error_codes,
    limit_schema_errors,
    run_codex_exec,
    validate_verdict_schema,
)


def build_summary_base(
    *,
    task_id: str,
    title: str,
    prompt_version: str,
    out_dir_rel: str,
    subtasks_total: int,
    views_present: list[str],
    acceptance_counts: dict[str, Any],
    security_profile: str,
    garbled_gate: str,
    auto_escalate: str,
    reuse_last_ok: bool,
    max_schema_errors: int,
) -> dict[str, Any]:
    return {
        "cmd": "sc-llm-extract-task-obligations",
        "task_id": str(task_id or "").strip(),
        "title": str(title or "").strip(),
        "prompt_version": str(prompt_version or "").strip(),
        "status": None,
        "error": None,
        "rc": 1,
        "out_dir": str(out_dir_rel or "").strip(),
        "subtasks_total": int(subtasks_total),
        "views_present": sorted([str(x or "").strip() for x in views_present if str(x or "").strip()]),
        "acceptance_counts": dict(acceptance_counts or {}),
        "security_profile": str(security_profile or "").strip(),
        "garbled_gate": str(garbled_gate or "").strip(),
        "reuse_last_ok": bool(reuse_last_ok),
        "reuse_hit": False,
        "reuse_index_hit": False,
        "reuse_index_fallback_scan": False,
        "reuse_index_pruned_count": 0,
        "reuse_index_lock_wait_ms": 0,
        "reused_from": None,
        "reused_summary_source": None,
        "max_schema_errors": max(1, int(max_schema_errors)),
        "input_hash": None,
        "runtime_code_fingerprint": "",
        "runtime_code_fingerprint_parts": {},
        "reuse_lookup_key": "",
        "schema_errors": [],
        "schema_error_buckets": {},
        "schema_error_codes": [],
        "schema_error_count": 0,
        "deterministic_issues": [],
        "hard_uncovered_count": 0,
        "advisory_uncovered_count": 0,
        "consensus_runs": 0,
        "consensus_runs_configured": 0,
        "consensus_votes": {"ok": 0, "fail": 0},
        "run_results": [],
        "auto_escalate": {
            "enabled": str(auto_escalate or "").strip().lower() != "off",
            "triggered": False,
            "max_runs": 0,
            "force_for_task": False,
            "reasons": [],
        },
        "selected_run": 0,
        "garbled_precheck": {},
        "garbled_top_hits": [],
    }


def run_consensus_rounds(
    *,
    prompt: str,
    out_dir: Path,
    timeout_sec: int,
    repo_root_path: Path,
    configured_runs: int,
    max_runs: int,
    auto_escalate_enabled: bool,
    force_for_task: bool,
    max_schema_errors: int,
    normalize_status: Callable[[Any], str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str] | None, bool, list[str]]:
    run_results: list[dict[str, Any]] = []
    run_verdicts: list[dict[str, Any]] = []
    cmd_ref: list[str] | None = None
    target_runs = max(1, int(configured_runs))
    auto_escalate_triggered = False
    auto_escalate_reasons: list[str] = []

    run = 1
    while run <= target_runs:
        run_last = out_dir / f"output-last-message-run-{run:02d}.txt"
        run_trace = out_dir / f"trace-run-{run:02d}.log"
        rc, trace, cmd = run_codex_exec(
            prompt=prompt,
            out_last_message=run_last,
            timeout_sec=int(timeout_sec),
            repo_root_path=repo_root_path,
        )
        run_trace.write_text(trace, encoding="utf-8")
        if cmd_ref is None:
            cmd_ref = cmd

        last_message = run_last.read_text(encoding="utf-8", errors="ignore") if run_last.exists() else ""
        parsed: dict[str, Any] | None = None
        err: str | None = None
        schema_errors_for_run: list[str] = []
        if rc != 0 or not last_message.strip():
            err = "codex_exec_failed_or_empty"
        else:
            try:
                parsed_raw = extract_json_object(last_message)
                schema_ok, schema_errors, parsed_obj = validate_verdict_schema(parsed_raw)
                if not schema_ok:
                    schema_errors_for_run = limit_schema_errors(schema_errors, max_count=max_schema_errors)
                    err = f"invalid_schema_codes:{'|'.join(extract_schema_error_codes(schema_errors_for_run))}"
                else:
                    parsed = parsed_obj
            except Exception as exc:
                err = f"invalid_json:{exc}"
        run_status = normalize_status((parsed or {}).get("status")) if parsed else "fail"
        run_results.append(
            {
                "run": run,
                "rc": rc,
                "status": run_status,
                "error": err,
                "schema_errors": schema_errors_for_run,
                "schema_error_codes": extract_schema_error_codes(schema_errors_for_run),
            }
        )
        if parsed:
            run_verdicts.append({"run": run, "status": run_status, "obj": parsed})
            (out_dir / f"verdict-run-{run:02d}.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run += 1

        if run > target_runs and auto_escalate_enabled and target_runs < max_runs:
            reasons = collect_auto_escalation_reasons(run_results, force_task=force_for_task)
            if reasons:
                target_runs = max_runs
                auto_escalate_triggered = True
                auto_escalate_reasons = reasons

    return run_results, run_verdicts, cmd_ref, auto_escalate_triggered, auto_escalate_reasons
