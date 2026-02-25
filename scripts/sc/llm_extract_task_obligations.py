#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from typing import Any
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _garbled_gate import parse_task_ids_csv, render_top_hits, scan_task_text_integrity  # noqa: E402
from _obligations_guard import (  # noqa: E402
    apply_deterministic_guards,
    build_obligation_prompt,
    normalize_model_status,
    pick_consensus_verdict,
    render_obligations_report,
    safe_prompt_truncate,
)
from _obligations_extract_helpers import (  # noqa: E402
    bucket_schema_errors,
    build_input_hash,
    build_self_check_report,
    build_source_text_blocks,
    extract_schema_error_codes,
    is_view_present,
    limit_schema_errors,
    normalize_subtasks,
    validate_verdict_schema,
)
from _obligations_input_fingerprint import build_obligations_input_fingerprint  # noqa: E402
from _obligations_artifacts import build_garbled_fail_report, write_checked_and_sync_artifacts, write_checked_summary_only_and_sync  # noqa: E402
from _obligations_code_fingerprint import build_runtime_code_fingerprint  # noqa: E402
from _obligations_prompt_acceptance import compute_acceptance_dedup_stats  # noqa: E402
from _obligations_reuse_index import (  # noqa: E402
    apply_reuse_stats,
    build_reuse_lookup_key,
    find_reusable_ok_result_with_stats,
    remember_reusable_ok_result_with_stats,
)
from _obligations_reuse_explain import explain_reuse_miss  # noqa: E402
from _obligations_runtime_helpers import (  # noqa: E402
    build_summary_base,
    run_consensus_rounds,
)
from _obligations_self_check import run_self_check  # noqa: E402
from _security_profile import build_security_profile_context, resolve_security_profile  # noqa: E402
from _taskmaster import resolve_triplet  # noqa: E402
from _util import ci_dir, repo_root, write_json, write_text  # noqa: E402
PROMPT_VERSION = "obligations-v3"
def main() -> int:
    parser = argparse.ArgumentParser(description="sc-llm-extract-task-obligations (obligations vs acceptance coverage)")
    parser.add_argument("--task-id", default=None, help="Taskmaster id (e.g. 17). Default: first status=in-progress task.")
    parser.add_argument("--timeout-sec", type=int, default=360, help="codex exec timeout in seconds (default: 360).")
    parser.add_argument("--max-prompt-chars", type=int, default=80_000, help="Max prompt size (default: 80000).")
    parser.add_argument("--consensus-runs", type=int, default=1, help="Run N baseline rounds and use majority status (default: 1).")
    parser.add_argument("--min-obligations", type=int, default=0, help="Deterministic hard gate: minimum obligations count (default: 0).")
    parser.add_argument("--round-id", default="", help="Optional run id suffix for output directory isolation.")
    parser.add_argument("--security-profile", default=None, choices=["strict", "host-safe"], help="Security review profile (default: env SECURITY_PROFILE or host-safe).")
    parser.add_argument("--garbled-gate", default="on", choices=["on", "off"], help="Run garbled-text precheck before LLM (default: on).")
    parser.add_argument("--auto-escalate", default="on", choices=["on", "off"], help="Auto escalate failed/unstable runs to --escalate-max-runs (default: on).")
    parser.add_argument("--escalate-max-runs", type=int, default=3, help="Max runs when auto escalation is triggered (default: 3).")
    parser.add_argument("--escalate-task-ids", default="", help="CSV task ids to force escalation to max runs (e.g. 2,12).")
    parser.add_argument("--max-schema-errors", type=int, default=5, help="Max schema errors captured per run/final report (default: 5).")
    parser.add_argument("--reuse-last-ok", action="store_true", help="Reuse latest matching ok verdict by input hash before invoking LLM.")
    parser.add_argument("--explain-reuse-miss", action="store_true", help="When reuse-last-ok misses, emit mismatch dimensions for reuse key fields.")
    parser.add_argument("--dry-run-fingerprint", action="store_true", help="Print runtime fingerprint/input hash/reuse key and exit without LLM.")
    parser.add_argument("--self-check", action="store_true", help="Run local deterministic self-check only (no LLM/task resolution).")
    args = parser.parse_args()
    max_schema_errors = max(1, int(args.max_schema_errors))
    if bool(args.self_check):
        out_dir = ci_dir("sc-llm-obligations-self-check")
        ok, payload = run_self_check(
            build_source_text_blocks=build_source_text_blocks,
            build_obligation_prompt=build_obligation_prompt,
        )
        write_json(out_dir / "summary.json", payload)
        write_json(out_dir / "verdict.json", payload)
        write_text(out_dir / "report.md", build_self_check_report(ok, payload))
        print(f"SC_LLM_OBLIGATIONS_SELF_CHECK status={'ok' if ok else 'fail'} out={out_dir}")
        return 0 if ok else 1
    if str(os.getenv("CI") or "").strip() and not str(args.task_id or "").strip():
        print("SC_LLM_OBLIGATIONS status=fail error=task_id_required_in_ci")
        return 2
    try:
        triplet = resolve_triplet(task_id=str(args.task_id) if args.task_id else None)
    except Exception as exc:  # noqa: BLE001
        print(f"SC_LLM_OBLIGATIONS status=fail error=resolve_triplet_failed exc={exc}")
        return 2
    out_dir_name = f"sc-llm-obligations-task-{triplet.task_id}"
    if str(args.round_id or "").strip():
        out_dir_name += f"-round-{str(args.round_id).strip()}"
    out_dir = ci_dir(out_dir_name)
    logs_root = repo_root() / "logs" / "ci"

    title = str(triplet.master.get("title") or "").strip()
    details = str(triplet.master.get("details") or "").strip()
    test_strategy = str(triplet.master.get("testStrategy") or "").strip()
    subtasks = normalize_subtasks(triplet.master.get("subtasks"))

    acceptance_by_view: dict[str, list[Any]] = {}
    if is_view_present(triplet.back):
        acceptance_by_view["back"] = list((triplet.back or {}).get("acceptance") or [])
    if is_view_present(triplet.gameplay):
        acceptance_by_view["gameplay"] = list((triplet.gameplay or {}).get("acceptance") or [])
    acceptance_counts = compute_acceptance_dedup_stats(acceptance_by_view)

    security_profile = resolve_security_profile(args.security_profile)
    security_profile_context = build_security_profile_context(security_profile)
    summary: dict[str, Any] = build_summary_base(task_id=str(triplet.task_id), title=title, prompt_version=PROMPT_VERSION, out_dir_rel=str(out_dir.relative_to(repo_root())).replace("\\", "/"), subtasks_total=len(subtasks), views_present=sorted(acceptance_by_view.keys()), acceptance_counts=acceptance_counts, security_profile=security_profile, garbled_gate=str(args.garbled_gate), auto_escalate=str(args.auto_escalate), reuse_last_ok=bool(args.reuse_last_ok), max_schema_errors=max_schema_errors)
    runtime_code_fingerprint, runtime_code_fingerprint_parts = build_runtime_code_fingerprint({"build_obligation_prompt": build_obligation_prompt, "apply_deterministic_guards": apply_deterministic_guards, "validate_verdict_schema": validate_verdict_schema})
    summary["runtime_code_fingerprint"] = runtime_code_fingerprint
    summary["runtime_code_fingerprint_parts"] = runtime_code_fingerprint_parts
    input_fingerprint = build_obligations_input_fingerprint(prompt_version=PROMPT_VERSION, runtime_code_fingerprint=runtime_code_fingerprint, task_id=str(triplet.task_id), title=title, details=details, test_strategy=test_strategy, subtasks=subtasks, acceptance_by_view=acceptance_by_view, security_profile=security_profile)
    input_hash = build_input_hash(input_fingerprint)
    summary["input_hash"] = input_hash
    reuse_lookup_key = build_reuse_lookup_key(task_id=str(triplet.task_id), input_hash=input_hash, prompt_version=PROMPT_VERSION, security_profile=security_profile)
    summary["reuse_lookup_key"] = reuse_lookup_key

    if str(args.garbled_gate).strip().lower() != "off":
        task_filter: set[int] = set()
        try:
            task_filter.add(int(triplet.task_id))
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
            fail_verdict = {"task_id": str(triplet.task_id), "status": "fail", "obligations": []}
            if not write_checked_and_sync_artifacts(
                out_dir=out_dir,
                summary_obj=summary,
                verdict_obj=fail_verdict,
                validate_verdict_schema=validate_verdict_schema,
                report_text=build_garbled_fail_report(
                    task_id=str(triplet.task_id),
                    hits=hits,
                    decode_errors=decode_errors,
                    parse_errors=parse_errors,
                    top_hits=top_hits,
                ),
            ):
                print(f"SC_LLM_OBLIGATIONS status=fail reason=output_schema_invalid out={out_dir}")
                return 1
            print(f"SC_LLM_OBLIGATIONS status=fail reason=garbled_precheck_failed out={out_dir}")
            return 1

    if not acceptance_by_view:
        summary["status"] = "fail"
        summary["error"] = "no_views_present"
        fail_verdict = {"task_id": str(triplet.task_id), "status": "fail", "obligations": []}
        if not write_checked_and_sync_artifacts(
            out_dir=out_dir,
            summary_obj=summary,
            verdict_obj=fail_verdict,
            validate_verdict_schema=validate_verdict_schema,
            report_text="# sc-llm-extract-task-obligations report\n\n- status: fail\n- reason: no_views_present\n",
        ):
            print(f"SC_LLM_OBLIGATIONS status=fail reason=output_schema_invalid out={out_dir}")
            return 1
        print(f"SC_LLM_OBLIGATIONS status=fail reason=no_views_present out={out_dir}")
        return 1

    try:
        source_blocks = build_source_text_blocks(
            title=title,
            details=details,
            test_strategy=test_strategy,
            subtasks=subtasks,
        )
    except ValueError as exc:
        summary["status"] = "fail"
        summary["error"] = "source_blocks_missing_title"
        summary["deterministic_issues"] = [f"DET_SOURCE_BLOCKS:{exc}"]
        fail_verdict = {"task_id": str(triplet.task_id), "status": "fail", "obligations": []}
        if not write_checked_and_sync_artifacts(
            out_dir=out_dir,
            summary_obj=summary,
            verdict_obj=fail_verdict,
            validate_verdict_schema=validate_verdict_schema,
            report_text="# sc-llm-extract-task-obligations report\n\n- status: fail\n- reason: source_blocks_missing_title\n",
        ):
            print(f"SC_LLM_OBLIGATIONS status=fail reason=output_schema_invalid out={out_dir}")
            return 1
        print(f"SC_LLM_OBLIGATIONS status=fail reason=source_blocks_missing_title out={out_dir}")
        return 1

    if bool(args.dry_run_fingerprint):
        write_json(out_dir / "fingerprint.json", {"task_id": str(triplet.task_id), "prompt_version": PROMPT_VERSION, "security_profile": security_profile, "runtime_code_fingerprint": runtime_code_fingerprint, "input_hash": input_hash, "reuse_lookup_key": reuse_lookup_key})
        print(f"SC_LLM_OBLIGATIONS_FINGERPRINT status=ok runtime_code_fingerprint={runtime_code_fingerprint} input_hash={input_hash} reuse_lookup_key={reuse_lookup_key} out={str((out_dir / 'fingerprint.json')).replace('\\', '/')}")
        return 0

    if bool(args.reuse_last_ok):
        reused, reuse_lookup_stats = find_reusable_ok_result_with_stats(
            task_id=str(triplet.task_id),
            input_hash=input_hash,
            prompt_version=PROMPT_VERSION,
            security_profile=security_profile,
            logs_root=logs_root,
            current_out_dir=out_dir,
        )
        apply_reuse_stats(summary, reuse_lookup_stats)
        if reused is None and bool(args.explain_reuse_miss):
            explain = explain_reuse_miss(logs_root=logs_root, task_id=str(triplet.task_id), input_hash=input_hash, prompt_version=PROMPT_VERSION, security_profile=security_profile, runtime_code_fingerprint=runtime_code_fingerprint)
            summary["reuse_miss_explain"] = explain
            write_json(out_dir / "reuse-miss-explain.json", explain)
        if reused is not None:
            verdict_path, reused_summary, reused_obj = reused
            reused_obj["task_id"] = str(triplet.task_id)
            reused_obj["status"] = "ok"
            reused_obj, det_issues, hard_uncovered, advisory_uncovered = apply_deterministic_guards(
                obj=reused_obj,
                subtasks=subtasks,
                min_obligations=int(args.min_obligations),
                source_text_blocks=source_blocks,
                security_profile=security_profile,
            )
            reused_status = normalize_model_status(reused_obj.get("status"))
            if reused_status == "ok":
                summary["status"] = "ok"
                summary["rc"] = 0
                summary["reuse_hit"] = True
                summary["reused_from"] = str(verdict_path).replace("\\", "/")
                summary["reused_summary_source"] = str(reused_summary.get("out_dir") or "").strip()
                summary["deterministic_issues"] = det_issues
                summary["hard_uncovered_count"] = len(hard_uncovered)
                summary["advisory_uncovered_count"] = len(advisory_uncovered)
                trace_text = (
                    "reuse_last_ok=true\n"
                    f"reused_from={str(verdict_path).replace('\\', '/')}\n"
                    f"input_hash={input_hash}\n"
                    f"prompt_version={PROMPT_VERSION}\n"
                )
                if not write_checked_and_sync_artifacts(
                    out_dir=out_dir,
                    summary_obj=summary,
                    verdict_obj=reused_obj,
                    validate_verdict_schema=validate_verdict_schema,
                    report_text=render_obligations_report(reused_obj),
                    trace_text=trace_text,
                    output_last_message=reused_obj,
                ):
                    print(f"SC_LLM_OBLIGATIONS status=fail reason=output_schema_invalid out={out_dir}")
                    return 1
                reuse_write_stats = remember_reusable_ok_result_with_stats(
                    task_id=str(triplet.task_id), input_hash=input_hash, prompt_version=PROMPT_VERSION, security_profile=security_profile, logs_root=logs_root, summary_path=out_dir / "summary.json", verdict_path=out_dir / "verdict.json"
                )
                apply_reuse_stats(summary, reuse_write_stats)
                if not write_checked_summary_only_and_sync(out_dir=out_dir, summary_obj=summary):
                    print(f"SC_LLM_OBLIGATIONS status=fail reason=output_schema_invalid out={out_dir}")
                    return 1
                print(f"SC_LLM_OBLIGATIONS status=ok reason=reuse_last_ok out={out_dir}")
                return 0

    prompt = build_obligation_prompt(
        task_id=str(triplet.task_id),
        title=title,
        master_details=details,
        master_test_strategy=test_strategy,
        subtasks=subtasks,
        acceptance_by_view=acceptance_by_view,
        security_profile=security_profile,
        security_profile_context=security_profile_context,
    )
    prompt = safe_prompt_truncate(prompt, max_chars=int(args.max_prompt_chars))
    write_text(out_dir / "prompt.md", prompt)

    configured_runs = max(1, int(args.consensus_runs))
    max_runs = max(configured_runs, int(args.escalate_max_runs))
    auto_escalate_enabled = str(args.auto_escalate).strip().lower() != "off"
    force_ids = parse_task_ids_csv(args.escalate_task_ids)
    force_for_task = False
    try:
        force_for_task = int(triplet.task_id) in force_ids
    except (TypeError, ValueError):
        force_for_task = False
    run_results, run_verdicts, cmd_ref, auto_escalate_triggered, auto_escalate_reasons = run_consensus_rounds(
        prompt=prompt,
        out_dir=out_dir,
        timeout_sec=int(args.timeout_sec),
        repo_root_path=repo_root(),
        configured_runs=configured_runs,
        max_runs=max_runs,
        auto_escalate_enabled=auto_escalate_enabled,
        force_for_task=force_for_task,
        max_schema_errors=max_schema_errors,
        normalize_status=normalize_model_status,
    )

    ok_votes = sum(1 for item in run_results if item["status"] == "ok")
    fail_votes = len(run_results) - ok_votes
    all_run_schema_errors: list[str] = []
    for item in run_results:
        all_run_schema_errors.extend([str(x or "").strip() for x in (item.get("schema_errors") or []) if str(x or "").strip()])
    summary["schema_error_buckets"] = bucket_schema_errors(all_run_schema_errors)
    summary["schema_error_codes"] = extract_schema_error_codes(all_run_schema_errors)
    summary["schema_error_count"] = len(all_run_schema_errors)
    status = "ok" if ok_votes > fail_votes else "fail"
    selected = pick_consensus_verdict(run_verdicts, target_status=status)
    obj: dict[str, Any] = dict((selected or {}).get("obj") or {"task_id": str(triplet.task_id), "status": "fail", "obligations": []})
    obj["task_id"] = str(triplet.task_id)
    obj["status"] = status

    final_schema_ok, final_schema_errors, obj = validate_verdict_schema(obj)
    if not final_schema_ok:
        final_schema_errors = limit_schema_errors(final_schema_errors, max_count=max_schema_errors)
        final_combined_errors = all_run_schema_errors + final_schema_errors
        summary["status"] = "fail"
        summary["error"] = "final_schema_invalid"
        summary["schema_errors"] = final_schema_errors
        summary["schema_error_buckets"] = bucket_schema_errors(final_combined_errors)
        summary["schema_error_codes"] = extract_schema_error_codes(final_combined_errors)
        summary["schema_error_count"] = len(final_combined_errors)
        if not write_checked_and_sync_artifacts(
            out_dir=out_dir,
            summary_obj=summary,
            verdict_obj=obj,
            validate_verdict_schema=validate_verdict_schema,
            report_text="# sc-llm-extract-task-obligations report\n\n- status: fail\n- reason: final_schema_invalid\n",
        ):
            print(f"SC_LLM_OBLIGATIONS status=fail reason=output_schema_invalid out={out_dir}")
            return 1
        print(f"SC_LLM_OBLIGATIONS status=fail reason=final_schema_invalid out={out_dir}")
        return 1

    obj, det_issues, hard_uncovered, advisory_uncovered = apply_deterministic_guards(
        obj=obj,
        subtasks=subtasks,
        min_obligations=int(args.min_obligations),
        source_text_blocks=source_blocks,
        security_profile=security_profile,
    )
    status = normalize_model_status(obj.get("status"))

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
    if not write_checked_and_sync_artifacts(
        out_dir=out_dir,
        summary_obj=summary,
        verdict_obj=obj,
        validate_verdict_schema=validate_verdict_schema,
        report_text=render_obligations_report(obj),
        trace_text=trace_text,
        output_last_message=obj,
    ):
        print(f"SC_LLM_OBLIGATIONS status=fail reason=output_schema_invalid out={out_dir}")
        return 1
    if status == "ok":
        reuse_write_stats = remember_reusable_ok_result_with_stats(
            task_id=str(triplet.task_id), input_hash=input_hash, prompt_version=PROMPT_VERSION, security_profile=security_profile, logs_root=logs_root, summary_path=out_dir / "summary.json", verdict_path=out_dir / "verdict.json"
        )
        apply_reuse_stats(summary, reuse_write_stats)
        if not write_checked_summary_only_and_sync(out_dir=out_dir, summary_obj=summary):
            print(f"SC_LLM_OBLIGATIONS status=fail reason=output_schema_invalid out={out_dir}")
            return 1
    ok = status == "ok"
    print(f"SC_LLM_OBLIGATIONS status={'ok' if ok else 'fail'} out={out_dir}")
    return 0 if ok else 1
if __name__ == "__main__":
    raise SystemExit(main())
