#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sc-llm-check-subtasks-coverage
Semantic pre-flight: check whether tasks.json subtasks are covered by
tasks_back/tasks_gameplay acceptance criteria. No file mutation beyond artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def _bootstrap_imports() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))


_bootstrap_imports()

from _delivery_profile import build_delivery_profile_context, profile_llm_semantic_gate_all_defaults, resolve_delivery_profile  # noqa: E402
from _subtasks_coverage_llm import build_prompt, extract_json_object, format_acceptance, normalize_model_status, run_codex_exec  # noqa: E402
from _taskmaster import resolve_triplet  # noqa: E402
from _util import ci_dir, repo_root, write_json, write_text  # noqa: E402
from _obligations_extract_helpers import (  # noqa: E402
    bucket_schema_errors,
    build_self_check_report,
    extract_schema_error_codes,
    is_view_present,
    limit_schema_errors,
    normalize_subtasks,
    truncate,
)
from _subtasks_coverage_schema import (  # noqa: E402
    collect_uncovered_subtasks,
    render_subtasks_coverage_report,
    run_subtasks_coverage_self_check,
    validate_subtasks_coverage_schema,
)
from _subtasks_coverage_garbled import run_subtasks_coverage_garbled_precheck  # noqa: E402


def apply_delivery_profile_defaults(args: argparse.Namespace) -> argparse.Namespace:
    delivery_profile = resolve_delivery_profile(getattr(args, "delivery_profile", None))
    defaults = profile_llm_semantic_gate_all_defaults(delivery_profile)
    args.delivery_profile = delivery_profile
    if args.timeout_sec is None:
        args.timeout_sec = int(defaults.get("timeout_sec", 300) or 300)
    if args.max_prompt_chars is None:
        args.max_prompt_chars = int(defaults.get("max_prompt_chars", 60_000) or 60_000)
    if args.consensus_runs is None:
        args.consensus_runs = int(defaults.get("consensus_runs", 1) or 1)
    if not str(args.garbled_gate or "").strip():
        args.garbled_gate = str(defaults.get("garbled_gate") or "on")
    return args


def main() -> int:
    ap = argparse.ArgumentParser(description="sc-llm-check-subtasks-coverage (semantic subtasks vs acceptance check)")
    ap.add_argument("--task-id", default=None, help="Taskmaster id (e.g. 17). Default: first status=in-progress task.")
    ap.add_argument(
        "--delivery-profile",
        default=None,
        choices=["playable-ea", "fast-ship", "standard"],
        help="Delivery profile (default: env DELIVERY_PROFILE or fast-ship).",
    )
    ap.add_argument("--timeout-sec", type=int, default=None, help="codex exec timeout in seconds (default: profile).")
    ap.add_argument("--max-prompt-chars", type=int, default=None, help="Max prompt size (default: profile).")
    ap.add_argument("--consensus-runs", type=int, default=None, help="Run N rounds and use majority status (default: profile).")
    ap.add_argument(
        "--strict-view-selection",
        action="store_true",
        help="When --task-id is provided, fail early if both task views are missing acceptance entries.",
    )
    ap.add_argument(
        "--garbled-gate",
        default=None,
        choices=["on", "off"],
        help="Run garbled-text precheck before LLM (default: profile).",
    )
    ap.add_argument("--max-schema-errors", type=int, default=5, help="Max schema errors captured per run/final report (default: 5).")
    ap.add_argument("--round-id", default="", help="Optional run id suffix for output directory isolation.")
    ap.add_argument("--self-check", action="store_true", help="Run deterministic local self-check only (no LLM/task resolution).")
    args = apply_delivery_profile_defaults(ap.parse_args())
    max_schema_errors = max(1, int(args.max_schema_errors))
    selection_policy = "strict" if bool(args.strict_view_selection) else "default"
    garbled_gate = str(args.garbled_gate).strip().lower()
    os.environ["DELIVERY_PROFILE"] = str(args.delivery_profile)

    if bool(args.self_check):
        out_dir = ci_dir("sc-llm-subtasks-coverage-self-check")
        ok, payload = run_subtasks_coverage_self_check()
        write_json(out_dir / "summary.json", payload)
        write_json(out_dir / "verdict.json", payload)
        write_text(out_dir / "report.md", build_self_check_report(ok, payload))
        print(f"SC_LLM_SUBTASKS_COVERAGE_SELF_CHECK status={'ok' if ok else 'fail'} out={out_dir}")
        return 0 if ok else 1

    if bool(args.strict_view_selection) and not str(args.task_id or "").strip():
        print("SC_LLM_SUBTASKS_COVERAGE status=fail error=strict_view_selection_requires_task_id")
        return 2

    if str(os.getenv("CI") or "").strip() and not str(args.task_id or "").strip():
        print("SC_LLM_SUBTASKS_COVERAGE status=fail error=task_id_required_in_ci")
        return 2

    try:
        triplet = resolve_triplet(task_id=str(args.task_id) if args.task_id else None)
    except Exception as exc:  # noqa: BLE001
        print(f"SC_LLM_SUBTASKS_COVERAGE status=fail error=resolve_triplet_failed exc={exc}")
        return 2

    out_dir_name = f"sc-llm-subtasks-coverage-task-{triplet.task_id}"
    if str(args.round_id or "").strip():
        out_dir_name += f"-round-{str(args.round_id).strip()}"
    out_dir = ci_dir(out_dir_name)
    title = str(triplet.master.get("title") or "").strip()
    raw_subtasks = triplet.master.get("subtasks")
    subtasks = normalize_subtasks(raw_subtasks)

    acceptance_by_view: dict[str, list[Any]] = {}
    if is_view_present(triplet.back):
        acceptance_by_view["back"] = list((triplet.back or {}).get("acceptance") or [])
    if is_view_present(triplet.gameplay):
        acceptance_by_view["gameplay"] = list((triplet.gameplay or {}).get("acceptance") or [])

    summary: dict[str, Any] = {
        "cmd": "sc-llm-subtasks-coverage",
        "task_id": triplet.task_id,
        "title": title,
        "status": None,
        "subtasks_total": len(subtasks),
        "views_present": sorted(acceptance_by_view.keys()),
        "out_dir": str(out_dir.relative_to(repo_root())).replace("\\", "/"),
        "selection_policy": selection_policy,
        "garbled_gate": garbled_gate,
        "max_schema_errors": max_schema_errors,
        "error": None,
    }
    delivery_profile_context = build_delivery_profile_context(args.delivery_profile)

    if bool(args.strict_view_selection) and str(args.task_id or "").strip() and (not acceptance_by_view or not any(acceptance_by_view.values())):
        summary["status"] = "fail"
        summary["error"] = "strict_view_selection_missing_acceptance_views"
        write_json(out_dir / "summary.json", summary)
        write_text(
            out_dir / "report.md",
            f"# T{triplet.task_id} subtasks coverage\n\nStatus: fail\n\nError: strict_view_selection_missing_acceptance_views\n",
        )
        print(f"SC_LLM_SUBTASKS_COVERAGE status=fail reason=strict_view_selection_missing_acceptance_views out={out_dir}")
        return 1

    if garbled_gate != "off":
        ok_precheck, summary = run_subtasks_coverage_garbled_precheck(task_id=str(triplet.task_id), out_dir=out_dir, summary=summary)
        if not ok_precheck:
            print(f"SC_LLM_SUBTASKS_COVERAGE status=fail reason=garbled_precheck_failed out={out_dir}")
            return 1

    if not subtasks:
        summary["status"] = "ok"
        summary["reason"] = "no_subtasks"
        write_json(out_dir / "summary.json", summary)
        write_text(out_dir / "report.md", f"# T{triplet.task_id} subtasks coverage\n\nStatus: ok\n\nReason: no subtasks\n")
        print(f"SC_LLM_SUBTASKS_COVERAGE status=ok out={out_dir}")
        return 0

    if not acceptance_by_view or not any(acceptance_by_view.values()):
        summary["status"] = "fail"
        summary["error"] = "missing_acceptance_views"
        write_json(out_dir / "summary.json", summary)
        write_text(
            out_dir / "report.md",
            f"# T{triplet.task_id} subtasks coverage\n\nStatus: fail\n\nError: missing acceptance views (tasks_back/tasks_gameplay)\n",
        )
        print(f"SC_LLM_SUBTASKS_COVERAGE status=fail out={out_dir}")
        return 1

    prompt = build_prompt(
        task_id=triplet.task_id,
        title=title,
        subtasks=subtasks,
        acceptance_by_view=acceptance_by_view,
        delivery_profile_context=delivery_profile_context,
        format_acceptance_fn=lambda view_name, acceptance: format_acceptance(
            view_name,
            acceptance,
            truncate_fn=lambda text, max_chars: truncate(text, max_chars=max_chars),
        ),
    )
    prompt = truncate(prompt, max_chars=int(args.max_prompt_chars))
    prompt_path = out_dir / "prompt.md"
    write_text(prompt_path, prompt)

    runs = max(1, int(args.consensus_runs))
    run_results: list[dict[str, Any]] = []
    run_verdicts: list[dict[str, Any]] = []
    cmd_ref: list[str] | None = None
    for i in range(1, runs + 1):
        run_last = out_dir / f"output-last-message-run-{i:02d}.txt"
        run_trace = out_dir / f"trace-run-{i:02d}.log"
        rc, trace, cmd = run_codex_exec(
            prompt=prompt,
            out_last_message=run_last,
            timeout_sec=int(args.timeout_sec),
            repo_root_path=repo_root(),
        )
        write_text(run_trace, trace)
        if cmd_ref is None:
            cmd_ref = cmd
        parsed_obj: dict[str, Any] | None = None
        err: str | None = None
        schema_errors_for_run: list[str] = []
        if rc == 0:
            try:
                model_out = run_last.read_text(encoding="utf-8", errors="ignore")
                parsed_obj = extract_json_object(model_out)
                schema_ok, schema_errors, parsed_obj = validate_subtasks_coverage_schema(parsed_obj)
                if not schema_ok:
                    schema_errors_for_run = limit_schema_errors(schema_errors, max_count=max_schema_errors)
                    err = f"invalid_schema_codes:{'|'.join(extract_schema_error_codes(schema_errors_for_run))}"
                    parsed_obj = None
            except Exception as exc:  # noqa: BLE001
                err = f"invalid_model_output: {exc}"
        else:
            err = "codex_exec_failed"
        run_status = normalize_model_status((parsed_obj or {}).get("status")) if parsed_obj else "fail"
        run_results.append(
            {
                "run": i,
                "rc": rc,
                "status": run_status,
                "error": err,
                "schema_errors": schema_errors_for_run,
                "schema_error_codes": extract_schema_error_codes(schema_errors_for_run),
            }
        )
        if parsed_obj:
            run_verdicts.append({"run": i, "status": run_status, "obj": parsed_obj})
            write_json(out_dir / f"verdict-run-{i:02d}.json", parsed_obj)

    ok_votes = sum(1 for r in run_results if r["status"] == "ok")
    fail_votes = runs - ok_votes
    all_run_schema_errors: list[str] = []
    for item in run_results:
        all_run_schema_errors.extend([str(x or "").strip() for x in (item.get("schema_errors") or []) if str(x or "").strip()])
    verdict_status = "ok" if ok_votes > fail_votes else "fail"
    selected = next((v for v in run_verdicts if v["status"] == verdict_status), run_verdicts[0] if run_verdicts else None)
    obj: dict[str, Any] = dict((selected or {}).get("obj") or {"task_id": str(triplet.task_id), "status": "fail", "subtasks": []})
    obj["status"] = verdict_status

    summary["schema_error_buckets"] = bucket_schema_errors(all_run_schema_errors)
    summary["schema_error_codes"] = extract_schema_error_codes(all_run_schema_errors)
    summary["schema_error_count"] = len(all_run_schema_errors)

    final_schema_ok, final_schema_errors, obj = validate_subtasks_coverage_schema(obj)
    if not final_schema_ok:
        final_schema_errors = limit_schema_errors(final_schema_errors, max_count=max_schema_errors)
        combined_schema_errors = all_run_schema_errors + final_schema_errors
        summary["status"] = "fail"
        summary["error"] = "final_schema_invalid"
        summary["schema_errors"] = final_schema_errors
        summary["schema_error_buckets"] = bucket_schema_errors(combined_schema_errors)
        summary["schema_error_codes"] = extract_schema_error_codes(combined_schema_errors)
        summary["schema_error_count"] = len(combined_schema_errors)
        write_json(out_dir / "verdict.json", obj)
        write_json(out_dir / "summary.json", summary)
        write_text(out_dir / "report.md", f"# T{triplet.task_id} subtasks coverage\n\nStatus: fail\n\nError: final_schema_invalid\n")
        print(f"SC_LLM_SUBTASKS_COVERAGE status=fail reason=final_schema_invalid out={out_dir}")
        return 1

    uncovered, obj = collect_uncovered_subtasks(obj, subtasks=subtasks)
    verdict_status = normalize_model_status(obj.get("status"))

    summary["status"] = verdict_status
    summary["uncovered_subtask_ids"] = uncovered
    summary["verdict_path"] = str((out_dir / "verdict.json").relative_to(repo_root())).replace("\\", "/")
    summary["consensus_runs"] = runs
    summary["consensus_votes"] = {"ok": ok_votes, "fail": fail_votes}
    summary["run_results"] = run_results
    summary["codex"] = {"rc": 0 if run_verdicts else 1, "cmd": cmd_ref or []}
    if not run_verdicts:
        summary["error"] = "all_runs_failed_or_invalid"

    write_json(out_dir / "verdict.json", obj)
    write_json(out_dir / "summary.json", summary)
    write_text(out_dir / "output-last-message.txt", json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    write_text(out_dir / "trace.log", f"consensus_runs={runs}\nok_votes={ok_votes}\nfail_votes={fail_votes}\n")
    write_text(
        out_dir / "report.md",
        render_subtasks_coverage_report(task_id=str(triplet.task_id), verdict_status=verdict_status, obj=obj, uncovered=uncovered),
    )

    print(f"SC_LLM_SUBTASKS_COVERAGE status={verdict_status} out={out_dir}")
    return 0 if verdict_status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
