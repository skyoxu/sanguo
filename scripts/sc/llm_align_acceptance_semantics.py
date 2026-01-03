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
from pathlib import Path
from typing import Any

from _taskmaster import default_paths, load_json  # type: ignore
from _util import ci_dir, today_str, write_json, write_text  # type: ignore

from _acceptance_semantics_align import (  # noqa: E402
    MasterTaskInput,
    ViewInput,
    apply_acceptance,
    apply_description,
    build_prompt,
    find_view_entry,
    load_master_index,
    load_semantic_hints,
    normalize_acceptance_lines,
    render_task_context,
    run_codex_exec,
    safe_parse_json,
    validate_output,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Align acceptance semantics (acceptance-only phase).")
    ap.add_argument("--scope", default="all", choices=["all", "done", "not-done"])
    ap.add_argument("--task-ids", default="", help="Optional CSV task ids override.")
    ap.add_argument("--apply", action="store_true", help="Write changes into tasks_back.json/tasks_gameplay.json.")
    ap.add_argument("--structural-for-not-done", action="store_true", help="Use append-only for not-done tasks.")
    ap.add_argument(
        "--append-only-for-done",
        action="store_true",
        help="Allow append-only mode for done tasks (append at end only; preserves existing anchors/Refs).",
    )
    ap.add_argument("--align-view-descriptions-to-master", action="store_true")
    ap.add_argument("--semantic-findings-json", default="", help="Optional sc-semantic-gate-all/summary.json for hints.")
    ap.add_argument("--timeout-sec", type=int, default=240)
    args = ap.parse_args()

    tasks_json_path, tasks_back_path, tasks_gameplay_path = default_paths()
    tasks_json = load_json(tasks_json_path)
    back = load_json(tasks_back_path)
    gameplay = load_json(tasks_gameplay_path)
    if not isinstance(back, list) or not isinstance(gameplay, list):
        print("SC_ALIGN_ACCEPTANCE status=fail reason=views_not_arrays")
        return 2

    master_index = load_master_index(str(args.scope))
    semantic_hints = load_semantic_hints(str(args.semantic_findings_json).strip() or None)

    if str(args.task_ids).strip():
        task_ids: list[int] = []
        for token in str(args.task_ids).split(","):
            t = token.strip()
            if t.isdigit():
                task_ids.append(int(t))
        task_ids = sorted(set(task_ids))
    else:
        task_ids = sorted(master_index.keys())

    out_dir = ci_dir("sc-llm-align-acceptance-semantics")
    results: list[dict[str, Any]] = []
    changed = 0
    skipped = 0
    failed = 0

    for tid in task_ids:
        master = master_index.get(tid)
        if not master:
            skipped += 1
            results.append({"task_id": tid, "status": "skipped", "reason": "missing_master"})
            continue

        back_entry = find_view_entry(back, tid)
        gameplay_entry = find_view_entry(gameplay, tid)
        view_inputs: list[ViewInput] = []
        if back_entry is not None:
            view_inputs.append(
                ViewInput(
                    view="back",
                    taskmaster_id=tid,
                    title=str(back_entry.get("title") or ""),
                    description=str(back_entry.get("description") or ""),
                    acceptance=normalize_acceptance_lines(back_entry.get("acceptance") or []),
                )
            )
        if gameplay_entry is not None:
            view_inputs.append(
                ViewInput(
                    view="gameplay",
                    taskmaster_id=tid,
                    title=str(gameplay_entry.get("title") or ""),
                    description=str(gameplay_entry.get("description") or ""),
                    acceptance=normalize_acceptance_lines(gameplay_entry.get("acceptance") or []),
                )
            )
        if not view_inputs:
            skipped += 1
            results.append({"task_id": tid, "status": "skipped", "reason": "missing_both_views"})
            continue

        # Per-task mode:
        # - done => rewrite-only
        # - not-done => rewrite-only by default, optionally append-only
        if str(master.status).lower() == "done":
            mode = "append-only" if bool(args.append_only_for_done) else "rewrite-only"
        elif bool(args.structural_for_not_done):
            mode = "append-only"
        else:
            mode = "rewrite-only"

        task_out = out_dir / f"task-{tid}"
        task_out.mkdir(parents=True, exist_ok=True)

        task_context = render_task_context(
            master=master,
            view_inputs=view_inputs,
            mode=mode,
            align_view_descriptions=bool(args.align_view_descriptions_to_master),
            semantic_hint=semantic_hints.get(tid),
        )
        prompt = build_prompt(task_context)
        write_text(task_out / "prompt.md", prompt)

        last_msg_path = task_out / "output.json"
        rc, trace = run_codex_exec(prompt=prompt, out_last_message=last_msg_path, timeout_sec=int(args.timeout_sec))
        write_text(task_out / "trace.log", trace)
        if rc != 0:
            failed += 1
            results.append({"task_id": tid, "status": "fail", "reason": f"codex_rc:{rc}", "dir": str(task_out)})
            continue

        out_text = last_msg_path.read_text(encoding="utf-8", errors="ignore") if last_msg_path.exists() else ""
        out_obj = safe_parse_json(out_text)
        if not out_obj:
            failed += 1
            results.append({"task_id": tid, "status": "fail", "reason": "invalid_json", "dir": str(task_out)})
            continue

        ok, reason = validate_output(
            task_id=tid,
            mode=mode,
            view_inputs=view_inputs,
            out_obj=out_obj,
            align_view_descriptions=bool(args.align_view_descriptions_to_master),
        )
        if not ok:
            failed += 1
            results.append({"task_id": tid, "status": "fail", "reason": reason, "dir": str(task_out)})
            continue

        if args.apply:
            if back_entry is not None and isinstance(out_obj.get("back"), dict):
                if bool(args.align_view_descriptions_to_master):
                    apply_description(back_entry, out_obj["back"].get("description"))
                new_acc = out_obj["back"].get("acceptance") or []
                if isinstance(new_acc, list):
                    apply_acceptance(back_entry, new_acc)
            if gameplay_entry is not None and isinstance(out_obj.get("gameplay"), dict):
                if bool(args.align_view_descriptions_to_master):
                    apply_description(gameplay_entry, out_obj["gameplay"].get("description"))
                new_acc = out_obj["gameplay"].get("acceptance") or []
                if isinstance(new_acc, list):
                    apply_acceptance(gameplay_entry, new_acc)
            changed += 1

        results.append({"task_id": tid, "status": "ok", "dir": str(task_out), "applied": bool(args.apply), "mode": mode})

    if args.apply:
        write_json(tasks_back_path, back)
        write_json(tasks_gameplay_path, gameplay)

    write_json(
        out_dir / "summary.json",
        {
            "date": today_str(),
            "apply": bool(args.apply),
            "scope": str(args.scope),
            "structural_for_not_done": bool(args.structural_for_not_done),
            "append_only_for_done": bool(args.append_only_for_done),
            "align_view_descriptions_to_master": bool(args.align_view_descriptions_to_master),
            "results": results,
        },
    )

    status = "ok" if failed == 0 else "warn"
    print(
        f"SC_ALIGN_ACCEPTANCE status={status} apply={bool(args.apply)} scope={args.scope} "
        f"structural_for_not_done={bool(args.structural_for_not_done)} append_only_for_done={bool(args.append_only_for_done)} "
        f"align_view_descriptions_to_master={bool(args.align_view_descriptions_to_master)} "
        f"tasks={len(task_ids)} changed={changed} skipped={skipped} failed={failed} out={out_dir}"
    )
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())

