#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from typing import Any
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _delivery_profile import (  # noqa: E402
    build_delivery_profile_context,
    default_security_profile_for_delivery,
    profile_llm_obligations_defaults,
    resolve_delivery_profile,
)
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
from _obligations_main_flow import fail_with_checked_artifacts, finalize_consensus_run, try_reuse_last_ok  # noqa: E402
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


def apply_delivery_profile_defaults(args: argparse.Namespace) -> argparse.Namespace:
    delivery_profile = resolve_delivery_profile(getattr(args, "delivery_profile", None))
    defaults = profile_llm_obligations_defaults(delivery_profile)
    args.delivery_profile = delivery_profile
    if args.timeout_sec is None:
        args.timeout_sec = int(defaults.get("timeout_sec", 360) or 360)
    if args.max_prompt_chars is None:
        args.max_prompt_chars = int(defaults.get("max_prompt_chars", 80_000) or 80_000)
    if args.consensus_runs is None:
        args.consensus_runs = int(defaults.get("consensus_runs", 1) or 1)
    if not str(args.garbled_gate or "").strip():
        args.garbled_gate = str(defaults.get("garbled_gate") or "on")
    return args


def main() -> int:
    parser = argparse.ArgumentParser(description="sc-llm-extract-task-obligations (obligations vs acceptance coverage)")
    parser.add_argument("--task-id", default=None, help="Taskmaster id (e.g. 17). Default: first status=in-progress task.")
    parser.add_argument(
        "--delivery-profile",
        default=None,
        choices=["playable-ea", "fast-ship", "standard"],
        help="Delivery profile (default: env DELIVERY_PROFILE or fast-ship).",
    )
    parser.add_argument("--timeout-sec", type=int, default=None, help="codex exec timeout in seconds (default: profile).")
    parser.add_argument("--max-prompt-chars", type=int, default=None, help="Max prompt size (default: profile).")
    parser.add_argument("--consensus-runs", type=int, default=None, help="Run N baseline rounds and use majority status (default: profile).")
    parser.add_argument("--min-obligations", type=int, default=0, help="Deterministic hard gate: minimum obligations count (default: 0).")
    parser.add_argument("--round-id", default="", help="Optional run id suffix for output directory isolation.")
    parser.add_argument("--security-profile", default=None, choices=["strict", "host-safe"], help="Security review profile (default: env SECURITY_PROFILE or host-safe).")
    parser.add_argument("--garbled-gate", default=None, choices=["on", "off"], help="Run garbled-text precheck before LLM (default: profile).")
    parser.add_argument("--auto-escalate", default="on", choices=["on", "off"], help="Auto escalate failed/unstable runs to --escalate-max-runs (default: on).")
    parser.add_argument("--escalate-max-runs", type=int, default=3, help="Max runs when auto escalation is triggered (default: 3).")
    parser.add_argument("--escalate-task-ids", default="", help="CSV task ids to force escalation to max runs (e.g. 2,12).")
    parser.add_argument("--max-schema-errors", type=int, default=5, help="Max schema errors captured per run/final report (default: 5).")
    parser.add_argument("--reuse-last-ok", action="store_true", help="Reuse latest matching ok verdict by input hash before invoking LLM.")
    parser.add_argument("--explain-reuse-miss", action="store_true", help="When reuse-last-ok misses, emit mismatch dimensions for reuse key fields.")
    parser.add_argument("--dry-run-fingerprint", action="store_true", help="Print runtime fingerprint/input hash/reuse key and exit without LLM.")
    parser.add_argument("--self-check", action="store_true", help="Run local deterministic self-check only (no LLM/task resolution).")
    args = apply_delivery_profile_defaults(parser.parse_args())
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

    security_profile = resolve_security_profile(args.security_profile or default_security_profile_for_delivery(args.delivery_profile))
    os.environ["DELIVERY_PROFILE"] = str(args.delivery_profile)
    os.environ["SECURITY_PROFILE"] = str(security_profile)
    delivery_profile_context = build_delivery_profile_context(args.delivery_profile)
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
        return fail_with_checked_artifacts(
            out_dir=out_dir,
            summary=summary,
            verdict=fail_verdict,
            reason="no_views_present",
            validate_verdict_schema_fn=validate_verdict_schema,
            write_checked_and_sync_artifacts_fn=write_checked_and_sync_artifacts,
            report_text="# sc-llm-extract-task-obligations report\n\n- status: fail\n- reason: no_views_present\n",
        )

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
        return fail_with_checked_artifacts(
            out_dir=out_dir,
            summary=summary,
            verdict=fail_verdict,
            reason="source_blocks_missing_title",
            validate_verdict_schema_fn=validate_verdict_schema,
            write_checked_and_sync_artifacts_fn=write_checked_and_sync_artifacts,
            report_text="# sc-llm-extract-task-obligations report\n\n- status: fail\n- reason: source_blocks_missing_title\n",
        )

    if bool(args.dry_run_fingerprint):
        write_json(out_dir / "fingerprint.json", {"task_id": str(triplet.task_id), "prompt_version": PROMPT_VERSION, "security_profile": security_profile, "runtime_code_fingerprint": runtime_code_fingerprint, "input_hash": input_hash, "reuse_lookup_key": reuse_lookup_key})
        print(f"SC_LLM_OBLIGATIONS_FINGERPRINT status=ok runtime_code_fingerprint={runtime_code_fingerprint} input_hash={input_hash} reuse_lookup_key={reuse_lookup_key} out={str((out_dir / 'fingerprint.json')).replace('\\', '/')}")
        return 0

    if bool(args.reuse_last_ok):
        handled, exit_code = try_reuse_last_ok(
            task_id=str(triplet.task_id),
            input_hash=input_hash,
            prompt_version=PROMPT_VERSION,
            security_profile=security_profile,
            runtime_code_fingerprint=runtime_code_fingerprint,
            logs_root=logs_root,
            current_out_dir=out_dir,
            summary=summary,
            subtasks=subtasks,
            min_obligations=int(args.min_obligations),
            source_blocks=source_blocks,
            find_reusable_ok_result_with_stats_fn=find_reusable_ok_result_with_stats,
            apply_reuse_stats_fn=apply_reuse_stats,
            explain_reuse_miss_fn=explain_reuse_miss,
            write_json_fn=write_json,
            apply_deterministic_guards_fn=apply_deterministic_guards,
            normalize_model_status_fn=normalize_model_status,
            write_checked_and_sync_artifacts_fn=write_checked_and_sync_artifacts,
            validate_verdict_schema_fn=validate_verdict_schema,
            render_obligations_report_fn=render_obligations_report,
            remember_reusable_ok_result_with_stats_fn=remember_reusable_ok_result_with_stats,
            write_checked_summary_only_and_sync_fn=write_checked_summary_only_and_sync,
            explain_reuse_miss=bool(args.explain_reuse_miss),
        )
        if handled:
            return int(exit_code or 0)

    prompt = build_obligation_prompt(
        task_id=str(triplet.task_id),
        title=title,
        master_details=details,
        master_test_strategy=test_strategy,
        subtasks=subtasks,
        acceptance_by_view=acceptance_by_view,
        security_profile=security_profile,
        security_profile_context=security_profile_context,
        delivery_profile_context=delivery_profile_context,
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

    return finalize_consensus_run(
        task_id=str(triplet.task_id),
        security_profile=security_profile,
        prompt_version=PROMPT_VERSION,
        out_dir=out_dir,
        logs_root=logs_root,
        summary=summary,
        subtasks=subtasks,
        min_obligations=int(args.min_obligations),
        source_blocks=source_blocks,
        input_hash=input_hash,
        run_results=run_results,
        run_verdicts=run_verdicts,
        cmd_ref=cmd_ref,
        auto_escalate_enabled=auto_escalate_enabled,
        auto_escalate_triggered=auto_escalate_triggered,
        auto_escalate_reasons=auto_escalate_reasons,
        configured_runs=configured_runs,
        max_runs=max_runs,
        force_for_task=force_for_task,
        validate_verdict_schema_fn=validate_verdict_schema,
        limit_schema_errors_fn=limit_schema_errors,
        bucket_schema_errors_fn=bucket_schema_errors,
        extract_schema_error_codes_fn=extract_schema_error_codes,
        pick_consensus_verdict_fn=pick_consensus_verdict,
        apply_deterministic_guards_fn=apply_deterministic_guards,
        normalize_model_status_fn=normalize_model_status,
        write_checked_and_sync_artifacts_fn=write_checked_and_sync_artifacts,
        render_obligations_report_fn=render_obligations_report,
        remember_reusable_ok_result_with_stats_fn=remember_reusable_ok_result_with_stats,
        apply_reuse_stats_fn=apply_reuse_stats,
        write_checked_summary_only_and_sync_fn=write_checked_summary_only_and_sync,
    )
if __name__ == "__main__":
    raise SystemExit(main())
