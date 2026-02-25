#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sc-llm-align-acceptance-semantics

Phase A (acceptance-only):
  Align acceptance text with the task description/details at the semantic level.

Hard rules (stop-loss):
  - Preserve existing "Refs:" suffix tokens verbatim for existing items.
  - Do NOT add new "Refs:" tokens in this step.
  - Default for done tasks: rewrite-only (keep acceptance item count/order per view).
  - Optional for not-done tasks: append-only (can only append new acceptance items).

This script intentionally does NOT create tests and does NOT fill refs.
"""

from __future__ import annotations

import argparse

from _taskmaster import default_paths, load_json  # type: ignore
from _util import ci_dir, repo_root, run_cmd, today_str, write_json, write_text  # type: ignore
from _garbled_gate import render_top_hits, scan_task_text_integrity  # type: ignore

from _acceptance_semantics_align import (  # noqa: E402
    load_master_index,
    load_semantic_hints,
)
from _acceptance_semantics_runtime import run_alignment_tasks  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Align acceptance semantics (acceptance-only phase).")
    ap.add_argument("--scope", default="all", choices=["all", "done", "not-done"])
    ap.add_argument("--task-ids", default="", help="Optional CSV task ids override.")
    ap.add_argument(
        "--fail-on-missing-task-ids",
        action="store_true",
        help="Fail when any requested --task-ids is missing from current scope master index.",
    )
    ap.add_argument(
        "--fail-on-missing-views",
        action="store_true",
        help="Fail when any requested --task-ids has no matching entry in both tasks_back and tasks_gameplay.",
    )
    ap.add_argument(
        "--strict-task-selection",
        action="store_true",
        help="Enable strict selection checks: fail on missing task ids and missing view entries.",
    )
    ap.add_argument("--apply", action="store_true", help="Write changes into tasks_back.json/tasks_gameplay.json.")
    ap.add_argument(
        "--preflight-migrate-optional-hints",
        action="store_true",
        help="Preflight: migrate optional/demo/hardening hints out of tasks.json into view test_strategy before alignment. "
        "Runs deterministically via scripts/python/migrate_task_optional_hints_to_views.py.",
    )
    ap.add_argument(
        "--skip-preflight-migrate-optional-hints",
        action="store_true",
        help="Disable the optional-hints preflight (default is enabled when --apply is set).",
    )
    ap.add_argument("--structural-for-not-done", action="store_true", help="Use append-only for not-done tasks.")
    ap.add_argument(
        "--append-only-for-done",
        action="store_true",
        help="Allow append-only mode for done tasks (append at end only; preserves existing anchors/Refs).",
    )
    ap.add_argument("--align-view-descriptions-to-master", action="store_true")
    ap.add_argument("--semantic-findings-json", default="", help="Optional sc-semantic-gate-all/summary.json for hints.")
    ap.add_argument("--timeout-sec", type=int, default=240)
    ap.add_argument("--max-failures", type=int, default=0, help="Stop early when failures reach threshold (0 = unlimited).")
    ap.add_argument(
        "--garbled-gate",
        default="on",
        choices=["on", "off"],
        help="Hard gate for garbled task/acceptance text before and after apply (default: on).",
    )
    ap.add_argument("--self-check", action="store_true", help="Run deterministic local self-check only (no LLM calls).")
    args = ap.parse_args()
    max_failures = max(0, int(args.max_failures))

    def _parse_task_ids_strict(raw: str) -> tuple[list[int], list[str]]:
        ids: list[int] = []
        bad_tokens: list[str] = []
        for token in str(raw or "").split(","):
            t = token.strip()
            if not t:
                continue
            try:
                value = int(t)
            except ValueError:
                bad_tokens.append(t)
                continue
            if value <= 0:
                bad_tokens.append(t)
                continue
            ids.append(value)
        return sorted(set(ids)), bad_tokens

    def _has_view_entry(view_items: list[object], task_id: int) -> bool:
        for item in view_items:
            if isinstance(item, dict) and item.get("taskmaster_id") == task_id:
                return True
        return False

    _, tasks_back_path, tasks_gameplay_path = default_paths()
    back = load_json(tasks_back_path)
    gameplay = load_json(tasks_gameplay_path)
    if not isinstance(back, list) or not isinstance(gameplay, list):
        print("SC_ALIGN_ACCEPTANCE status=fail reason=views_not_arrays")
        return 2

    master_index = load_master_index(str(args.scope))
    semantic_hints = load_semantic_hints(str(args.semantic_findings_json).strip() or None)

    strict_task_selection = bool(args.strict_task_selection)
    fail_on_missing_task_ids = bool(args.fail_on_missing_task_ids) or strict_task_selection
    fail_on_missing_views = bool(args.fail_on_missing_views) or strict_task_selection

    if str(args.task_ids).strip():
        task_ids, bad_tokens = _parse_task_ids_strict(str(args.task_ids))
        if bad_tokens:
            print(f"SC_ALIGN_ACCEPTANCE status=fail reason=invalid_task_ids bad_tokens={','.join(bad_tokens)}")
            return 2
        if not task_ids:
            print("SC_ALIGN_ACCEPTANCE status=fail reason=empty_task_ids")
            return 2
        if fail_on_missing_task_ids:
            missing = [tid for tid in task_ids if tid not in master_index]
            if missing:
                print(f"SC_ALIGN_ACCEPTANCE status=fail reason=missing_task_ids_in_scope ids={','.join([str(x) for x in missing])}")
                return 2
        if fail_on_missing_views:
            missing_views = [tid for tid in task_ids if not (_has_view_entry(back, tid) or _has_view_entry(gameplay, tid))]
            if missing_views:
                print(f"SC_ALIGN_ACCEPTANCE status=fail reason=missing_view_entries ids={','.join([str(x) for x in missing_views])}")
                return 2
    else:
        task_ids = sorted(master_index.keys())

    if bool(args.self_check):
        out_dir = ci_dir("sc-llm-align-acceptance-semantics-self-check")
        write_json(out_dir / "summary.json", {"date": today_str(), "status": "ok", "scope": str(args.scope), "apply": bool(args.apply), "max_failures": max_failures, "task_ids": task_ids, "task_count": len(task_ids), "changed": 0, "skipped": 0, "failed": 0, "stopped_early": False, "views_ok": True})
        print(f"SC_ALIGN_ACCEPTANCE_SELF_CHECK status=ok scope={args.scope} tasks={len(task_ids)} out={out_dir}")
        return 0

    out_dir = ci_dir("sc-llm-align-acceptance-semantics")

    garbled_gate_on = str(args.garbled_gate).strip().lower() != "off"
    gate_task_ids = set(task_ids) if task_ids else set()

    if garbled_gate_on:
        pre_report = scan_task_text_integrity(task_ids=gate_task_ids or None)
        write_json(out_dir / "garbled-precheck.json", pre_report)
        pre_summary = pre_report.get("summary") or {}
        pre_fail = (
            int(pre_summary.get("decode_errors") or 0) > 0
            or int(pre_summary.get("parse_errors") or 0) > 0
            or int(pre_summary.get("suspicious_hits") or 0) > 0
        )
        if pre_fail:
            top_hits = render_top_hits(pre_report, limit=8)
            print(
                "SC_ALIGN_ACCEPTANCE status=fail reason=garbled_precheck "
                f"hits={int(pre_summary.get('suspicious_hits') or 0)} out={out_dir}"
            )
            if top_hits:
                print("SC_ALIGN_ACCEPTANCE garbled_top_hits:")
                for line in top_hits:
                    print(f" - {line}")
            return 2

    # Step A (upstream governance): remove non-core / non-portable optional hints
    # from master tasks so they don't pollute acceptance semantics alignment.
    preflight_ran = False
    preflight_rc: int | None = None
    # Default: enabled when --apply is set (can be disabled via --skip-preflight-migrate-optional-hints).
    preflight_enabled = bool(args.apply) and not bool(args.skip_preflight_migrate_optional_hints)
    # If not applying, allow a dry-run preflight report only when explicitly requested.
    preflight_dry_run = (not bool(args.apply)) and bool(args.preflight_migrate_optional_hints) and not bool(args.skip_preflight_migrate_optional_hints)

    if (bool(args.apply) and preflight_enabled) or preflight_dry_run:
        cmd = ["py", "-3", "scripts/python/migrate_task_optional_hints_to_views.py"]
        if task_ids:
            cmd += ["--task-ids", ",".join([str(x) for x in task_ids])]
        if bool(args.apply):
            cmd.append("--write")
        preflight_rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=300)
        write_text(out_dir / "preflight-migrate-optional-hints.log", out)
        preflight_ran = True
        if bool(args.apply) and int(preflight_rc or 0) != 0:
            write_json(
                out_dir / "summary.json",
                {
                    "date": today_str(),
                    "apply": bool(args.apply),
                    "scope": str(args.scope),
                    "preflight": {
                        "migrate_optional_hints": bool(preflight_enabled),
                        "dry_run": bool(preflight_dry_run),
                        "ran": preflight_ran,
                        "rc": preflight_rc,
                        "log": str((out_dir / "preflight-migrate-optional-hints.log").relative_to(repo_root())).replace("\\", "/"),
                    },
                    "results": [],
                    "error": "preflight_migrate_optional_hints_failed",
                },
            )
            print(f"SC_ALIGN_ACCEPTANCE status=fail reason=preflight_migrate_optional_hints_failed rc={preflight_rc} out={out_dir}")
            return 2

    run_result = run_alignment_tasks(
        task_ids=task_ids,
        master_index=master_index,
        semantic_hints=semantic_hints,
        back=back,
        gameplay=gameplay,
        out_dir=out_dir,
        apply=bool(args.apply),
        timeout_sec=int(args.timeout_sec),
        max_failures=max_failures,
        structural_for_not_done=bool(args.structural_for_not_done),
        append_only_for_done=bool(args.append_only_for_done),
        align_view_descriptions_to_master=bool(args.align_view_descriptions_to_master),
    )
    results = run_result.get("results") or []
    changed = int(run_result.get("changed") or 0)
    skipped = int(run_result.get("skipped") or 0)
    failed = int(run_result.get("failed") or 0)
    stopped_early = bool(run_result.get("stopped_early"))
    back_file_changed = bool(run_result.get("back_file_changed"))
    gameplay_file_changed = bool(run_result.get("gameplay_file_changed"))

    if args.apply:
        if back_file_changed:
            write_json(tasks_back_path, back)
        if gameplay_file_changed:
            write_json(tasks_gameplay_path, gameplay)

        if garbled_gate_on:
            post_report = scan_task_text_integrity(task_ids=gate_task_ids or None)
            write_json(out_dir / "garbled-postcheck.json", post_report)
            post_summary = post_report.get("summary") or {}
            post_fail = (
                int(post_summary.get("decode_errors") or 0) > 0
                or int(post_summary.get("parse_errors") or 0) > 0
                or int(post_summary.get("suspicious_hits") or 0) > 0
            )
            if post_fail:
                top_hits = render_top_hits(post_report, limit=8)
                print(
                    "SC_ALIGN_ACCEPTANCE status=fail reason=garbled_postcheck "
                    f"hits={int(post_summary.get('suspicious_hits') or 0)} out={out_dir}"
                )
                if top_hits:
                    print("SC_ALIGN_ACCEPTANCE garbled_top_hits:")
                    for line in top_hits:
                        print(f" - {line}")
                return 2

    write_json(
        out_dir / "summary.json",
        {
            "date": today_str(),
            "apply": bool(args.apply),
            "scope": str(args.scope),
            "preflight": {
                "migrate_optional_hints": bool(preflight_enabled),
                "dry_run": bool(preflight_dry_run),
                "ran": preflight_ran,
                "rc": preflight_rc,
                "log": str((out_dir / "preflight-migrate-optional-hints.log").relative_to(repo_root())).replace("\\", "/")
                if preflight_ran
                else None,
            },
            "structural_for_not_done": bool(args.structural_for_not_done),
            "append_only_for_done": bool(args.append_only_for_done),
            "align_view_descriptions_to_master": bool(args.align_view_descriptions_to_master),
            "max_failures": max_failures,
            "stopped_early": bool(stopped_early),
            "results": results,
        },
    )

    status = "ok" if failed == 0 else "warn"
    print(
        f"SC_ALIGN_ACCEPTANCE status={status} apply={bool(args.apply)} scope={args.scope} "
        f"structural_for_not_done={bool(args.structural_for_not_done)} append_only_for_done={bool(args.append_only_for_done)} "
        f"align_view_descriptions_to_master={bool(args.align_view_descriptions_to_master)} "
        f"tasks={len(task_ids)} changed={changed} skipped={skipped} failed={failed} stopped_early={bool(stopped_early)} out={out_dir}"
    )
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())

