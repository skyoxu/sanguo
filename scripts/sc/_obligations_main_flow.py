#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def fail_with_checked_artifacts(
    *,
    out_dir: Path,
    summary: dict[str, Any],
    verdict: dict[str, Any],
    reason: str,
    validate_verdict_schema_fn: Callable[[dict[str, Any]], tuple[bool, list[str], dict[str, Any]]],
    write_checked_and_sync_artifacts_fn: Callable[..., bool],
    report_text: str,
) -> int:
    if not write_checked_and_sync_artifacts_fn(
        out_dir=out_dir,
        summary_obj=summary,
        verdict_obj=verdict,
        validate_verdict_schema=validate_verdict_schema_fn,
        report_text=report_text,
    ):
        print(f"SC_LLM_OBLIGATIONS status=fail reason=output_schema_invalid out={out_dir}")
        return 1
    print(f"SC_LLM_OBLIGATIONS status=fail reason={reason} out={out_dir}")
    return 1


def try_reuse_last_ok(
    *,
    task_id: str,
    input_hash: str,
    prompt_version: str,
    security_profile: str,
    runtime_code_fingerprint: str,
    logs_root: Path,
    current_out_dir: Path,
    summary: dict[str, Any],
    subtasks: list[dict[str, Any]],
    min_obligations: int,
    source_blocks: list[str],
    find_reusable_ok_result_with_stats_fn: Callable[..., tuple[Any, dict[str, Any]]],
    apply_reuse_stats_fn: Callable[[dict[str, Any], dict[str, Any]], None],
    explain_reuse_miss_fn: Callable[..., dict[str, Any]],
    write_json_fn: Callable[[Path, object], None],
    apply_deterministic_guards_fn: Callable[..., tuple[dict[str, Any], list[str], list[str], list[str]]],
    normalize_model_status_fn: Callable[[Any], str],
    write_checked_and_sync_artifacts_fn: Callable[..., bool],
    validate_verdict_schema_fn: Callable[[dict[str, Any]], tuple[bool, list[str], dict[str, Any]]],
    render_obligations_report_fn: Callable[[dict[str, Any]], str],
    remember_reusable_ok_result_with_stats_fn: Callable[..., dict[str, Any]],
    write_checked_summary_only_and_sync_fn: Callable[..., bool],
    explain_reuse_miss: bool,
) -> tuple[bool, int | None]:
    reused, reuse_lookup_stats = find_reusable_ok_result_with_stats_fn(
        task_id=task_id,
        input_hash=input_hash,
        prompt_version=prompt_version,
        security_profile=security_profile,
        logs_root=logs_root,
        current_out_dir=current_out_dir,
    )
    apply_reuse_stats_fn(summary, reuse_lookup_stats)
    if reused is None:
        if explain_reuse_miss:
            explain = explain_reuse_miss_fn(
                logs_root=logs_root,
                task_id=task_id,
                input_hash=input_hash,
                prompt_version=prompt_version,
                security_profile=security_profile,
                runtime_code_fingerprint=runtime_code_fingerprint,
            )
            summary["reuse_miss_explain"] = explain
            write_json_fn(current_out_dir / "reuse-miss-explain.json", explain)
        return False, None

    verdict_path, reused_summary, reused_obj = reused
    reused_obj["task_id"] = task_id
    reused_obj["status"] = "ok"
    reused_obj, det_issues, hard_uncovered, advisory_uncovered = apply_deterministic_guards_fn(
        obj=reused_obj,
        subtasks=subtasks,
        min_obligations=min_obligations,
        source_text_blocks=source_blocks,
        security_profile=security_profile,
    )
    if normalize_model_status_fn(reused_obj.get("status")) != "ok":
        return False, None

    det_stats = {
        "excerpt_prefix_stripped_matches": int(reused_obj.get("source_excerpt_prefix_stripped_matches") or 0),
    }
    summary["status"] = "ok"
    summary["rc"] = 0
    summary["reuse_hit"] = True
    summary["reused_from"] = str(verdict_path).replace("\\", "/")
    summary["reused_summary_source"] = str(reused_summary.get("out_dir") or "").strip()
    summary["deterministic_issues"] = det_issues
    summary["deterministic_stats"] = det_stats
    summary["excerpt_prefix_stripped_matches"] = int(det_stats.get("excerpt_prefix_stripped_matches") or 0)
    summary["hard_uncovered_count"] = len(hard_uncovered)
    summary["advisory_uncovered_count"] = len(advisory_uncovered)
    trace_text = (
        "reuse_last_ok=true\n"
        f"reused_from={str(verdict_path).replace('\\', '/')}\n"
        f"input_hash={input_hash}\n"
        f"prompt_version={prompt_version}\n"
    )
    if not write_checked_and_sync_artifacts_fn(
        out_dir=current_out_dir,
        summary_obj=summary,
        verdict_obj=reused_obj,
        validate_verdict_schema=validate_verdict_schema_fn,
        report_text=render_obligations_report_fn(reused_obj),
        trace_text=trace_text,
        output_last_message=reused_obj,
    ):
        print(f"SC_LLM_OBLIGATIONS status=fail reason=output_schema_invalid out={current_out_dir}")
        return True, 1

    reuse_write_stats = remember_reusable_ok_result_with_stats_fn(
        task_id=task_id,
        input_hash=input_hash,
        prompt_version=prompt_version,
        security_profile=security_profile,
        logs_root=logs_root,
        summary_path=current_out_dir / "summary.json",
        verdict_path=current_out_dir / "verdict.json",
    )
    apply_reuse_stats_fn(summary, reuse_write_stats)
    if not write_checked_summary_only_and_sync_fn(out_dir=current_out_dir, summary_obj=summary):
        print(f"SC_LLM_OBLIGATIONS status=fail reason=output_schema_invalid out={current_out_dir}")
        return True, 1
    print(f"SC_LLM_OBLIGATIONS status=ok reason=reuse_last_ok out={current_out_dir}")
    return True, 0


def finalize_consensus_run(
    *,
    task_id: str,
    security_profile: str,
    prompt_version: str,
    out_dir: Path,
    logs_root: Path,
    summary: dict[str, Any],
    subtasks: list[dict[str, Any]],
    min_obligations: int,
    source_blocks: list[str],
    input_hash: str,
    run_results: list[dict[str, Any]],
    run_verdicts: list[dict[str, Any]],
    cmd_ref: list[str] | None,
    auto_escalate_enabled: bool,
    auto_escalate_triggered: bool,
    auto_escalate_reasons: list[str],
    configured_runs: int,
    max_runs: int,
    force_for_task: bool,
    validate_verdict_schema_fn: Callable[[dict[str, Any]], tuple[bool, list[str], dict[str, Any]]],
    limit_schema_errors_fn: Callable[[list[str], int], list[str]],
    bucket_schema_errors_fn: Callable[[list[str]], dict[str, int]],
    extract_schema_error_codes_fn: Callable[[list[str]], list[str]],
    pick_consensus_verdict_fn: Callable[..., dict[str, Any] | None],
    apply_deterministic_guards_fn: Callable[..., tuple[dict[str, Any], list[str], list[str], list[str]]],
    normalize_model_status_fn: Callable[[Any], str],
    write_checked_and_sync_artifacts_fn: Callable[..., bool],
    render_obligations_report_fn: Callable[[dict[str, Any]], str],
    remember_reusable_ok_result_with_stats_fn: Callable[..., dict[str, Any]],
    apply_reuse_stats_fn: Callable[[dict[str, Any], dict[str, Any]], None],
    write_checked_summary_only_and_sync_fn: Callable[..., bool],
) -> int:
    ok_votes = sum(1 for item in run_results if item["status"] == "ok")
    fail_votes = len(run_results) - ok_votes
    all_run_schema_errors = [str(x or "").strip() for item in run_results for x in (item.get("schema_errors") or []) if str(x or "").strip()]
    summary["schema_error_buckets"] = bucket_schema_errors_fn(all_run_schema_errors)
    summary["schema_error_codes"] = extract_schema_error_codes_fn(all_run_schema_errors)
    summary["schema_error_count"] = len(all_run_schema_errors)

    status = "ok" if ok_votes > fail_votes else "fail"
    selected = pick_consensus_verdict_fn(run_verdicts, target_status=status)
    obj: dict[str, Any] = dict((selected or {}).get("obj") or {"task_id": task_id, "status": "fail", "obligations": []})
    obj["task_id"] = task_id
    obj["status"] = status

    final_schema_ok, final_schema_errors, obj = validate_verdict_schema_fn(obj)
    if not final_schema_ok:
        final_schema_errors = limit_schema_errors_fn(final_schema_errors, max_count=int(summary.get("max_schema_errors") or 5))
        final_combined_errors = all_run_schema_errors + final_schema_errors
        summary["status"] = "fail"
        summary["error"] = "final_schema_invalid"
        summary["schema_errors"] = final_schema_errors
        summary["schema_error_buckets"] = bucket_schema_errors_fn(final_combined_errors)
        summary["schema_error_codes"] = extract_schema_error_codes_fn(final_combined_errors)
        summary["schema_error_count"] = len(final_combined_errors)
        if not write_checked_and_sync_artifacts_fn(
            out_dir=out_dir,
            summary_obj=summary,
            verdict_obj=obj,
            validate_verdict_schema=validate_verdict_schema_fn,
            report_text="# sc-llm-extract-task-obligations report\n\n- status: fail\n- reason: final_schema_invalid\n",
        ):
            print(f"SC_LLM_OBLIGATIONS status=fail reason=output_schema_invalid out={out_dir}")
            return 1
        print(f"SC_LLM_OBLIGATIONS status=fail reason=final_schema_invalid out={out_dir}")
        return 1

    obj, det_issues, hard_uncovered, advisory_uncovered = apply_deterministic_guards_fn(
        obj=obj,
        subtasks=subtasks,
        min_obligations=min_obligations,
        source_text_blocks=source_blocks,
        security_profile=security_profile,
    )
    det_stats = {
        "excerpt_prefix_stripped_matches": int(obj.get("source_excerpt_prefix_stripped_matches") or 0),
    }
    status = normalize_model_status_fn(obj.get("status"))
    summary["rc"] = 0 if run_verdicts else 1
    summary["cmdline"] = cmd_ref or []
    summary["consensus_runs"] = len(run_results)
    summary["consensus_runs_configured"] = configured_runs
    summary["consensus_votes"] = {"ok": ok_votes, "fail": fail_votes}
    summary["run_results"] = run_results
    summary["auto_escalate"] = {
        "enabled": auto_escalate_enabled,
        "triggered": auto_escalate_triggered,
        "max_runs": max_runs,
        "force_for_task": force_for_task,
        "reasons": auto_escalate_reasons,
    }
    summary["selected_run"] = int((selected or {}).get("run") or 0)
    summary["deterministic_issues"] = det_issues
    summary["deterministic_stats"] = det_stats
    summary["excerpt_prefix_stripped_matches"] = int(det_stats.get("excerpt_prefix_stripped_matches") or 0)
    summary["hard_uncovered_count"] = len(hard_uncovered)
    summary["advisory_uncovered_count"] = len(advisory_uncovered)
    summary["status"] = status
    if not run_verdicts:
        summary["error"] = "all_runs_failed_or_invalid"

    trace_text = (
        f"consensus_runs={len(run_results)}\n"
        f"consensus_runs_configured={configured_runs}\n"
        f"ok_votes={ok_votes}\n"
        f"fail_votes={fail_votes}\n"
        f"selected_run={summary['selected_run']}\n"
        f"security_profile={security_profile}\n"
        f"auto_escalate_enabled={auto_escalate_enabled}\n"
        f"auto_escalate_triggered={auto_escalate_triggered}\n"
        f"auto_escalate_reasons={','.join(auto_escalate_reasons)}\n"
    )
    if not write_checked_and_sync_artifacts_fn(
        out_dir=out_dir,
        summary_obj=summary,
        verdict_obj=obj,
        validate_verdict_schema=validate_verdict_schema_fn,
        report_text=render_obligations_report_fn(obj),
        trace_text=trace_text,
        output_last_message=obj,
    ):
        print(f"SC_LLM_OBLIGATIONS status=fail reason=output_schema_invalid out={out_dir}")
        return 1

    if status == "ok":
        reuse_write_stats = remember_reusable_ok_result_with_stats_fn(
            task_id=task_id,
            input_hash=input_hash,
            prompt_version=prompt_version,
            security_profile=security_profile,
            logs_root=logs_root,
            summary_path=out_dir / "summary.json",
            verdict_path=out_dir / "verdict.json",
        )
        apply_reuse_stats_fn(summary, reuse_write_stats)
        if not write_checked_summary_only_and_sync_fn(out_dir=out_dir, summary_obj=summary):
            print(f"SC_LLM_OBLIGATIONS status=fail reason=output_schema_invalid out={out_dir}")
            return 1

    ok = status == "ok"
    print(f"SC_LLM_OBLIGATIONS status={'ok' if ok else 'fail'} out={out_dir}")
    return 0 if ok else 1
