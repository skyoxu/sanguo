#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _bootstrap_imports() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))


_bootstrap_imports()

from _acceptance_refs_contract import (  # noqa: E402
    run_fill_acceptance_refs_self_check,
    validate_fill_acceptance_summary,
)
from _acceptance_refs_helpers import (  # noqa: E402
    ItemKey,
    REFS_RE,
    apply_paths_to_view_entry,
    collect_missing_for_entry,
    default_ref_for,
    extract_json_object,
    extract_prd_excerpt,
    is_a11y_task,
    is_allowed_test_path,
    list_existing_tests,
    parse_model_items_to_paths,
    pick_existing_candidates,
    read_text,
    run_codex_exec,
)
from _acceptance_refs_prompt import build_prompt  # noqa: E402
from _taskmaster import default_paths, iter_master_tasks, load_json  # noqa: E402
from _util import ci_dir, repo_root, today_str, write_json, write_text  # noqa: E402


def _parse_task_ids_arg(*, raw_task_id: str | None, run_all: bool, back_by_id: dict[int, dict[str, Any]], gameplay_by_id: dict[int, dict[str, Any]]) -> tuple[int, list[int]]:
    if raw_task_id:
        s = str(raw_task_id).split(".", 1)[0].strip()
        try:
            return 0, [int(s)]
        except ValueError:
            return 2, []
    if not run_all:
        return 2, []
    return 0, sorted(set(back_by_id.keys()) | set(gameplay_by_id.keys()))


def _collect_missing_for_task(
    *,
    task_id: int,
    master: dict[str, Any] | None,
    back_task: dict[str, Any] | None,
    gameplay_task: dict[str, Any] | None,
    overwrite_existing: bool,
    rewrite_placeholders: bool,
) -> tuple[dict[ItemKey, str], dict[str, set[int]], bool]:
    missing: dict[ItemKey, str] = {}
    overwrite_indices: dict[str, set[int]] = {"back": set(), "gameplay": set()}

    b_missing, b_overwrite = collect_missing_for_entry(
        view="back",
        entry=back_task,
        task_id=task_id,
        master=master,
        overwrite_existing=overwrite_existing,
        rewrite_placeholders=rewrite_placeholders,
    )
    g_missing, g_overwrite = collect_missing_for_entry(
        view="gameplay",
        entry=gameplay_task,
        task_id=task_id,
        master=master,
        overwrite_existing=overwrite_existing,
        rewrite_placeholders=rewrite_placeholders,
    )
    missing.update(b_missing)
    missing.update(g_missing)
    overwrite_indices["back"] = b_overwrite
    overwrite_indices["gameplay"] = g_overwrite

    prefer_gd = False
    if isinstance(back_task, dict) and str(back_task.get("layer") or "").strip().lower() == "ui":
        prefer_gd = True
    if isinstance(gameplay_task, dict) and str(gameplay_task.get("layer") or "").strip().lower() == "ui":
        prefer_gd = True
    return missing, overwrite_indices, prefer_gd


def _run_consensus_for_task(
    *,
    root: Path,
    out_dir: Path,
    task_id: int,
    prompt: str,
    timeout_sec: int,
    max_refs_per_item: int,
    consensus_runs: int,
) -> tuple[bool, dict[str, dict[int, list[str]]], list[dict[str, Any]], list[str]]:
    run_results: list[dict[str, Any]] = []
    cmd_ref: list[str] = []
    for run_index in range(1, max(1, consensus_runs) + 1):
        suffix = f"-run-{run_index:02d}" if consensus_runs > 1 else ""
        last_msg_path = out_dir / f"codex-last-{task_id}{suffix}.txt"
        trace_path = out_dir / f"codex-trace-{task_id}{suffix}.log"
        rc, trace_out, cmd = run_codex_exec(root=root, prompt=prompt, out_last_message=last_msg_path, timeout_sec=timeout_sec)
        write_text(trace_path, trace_out)
        if not cmd_ref:
            cmd_ref = cmd
        last_msg = read_text(last_msg_path) if last_msg_path.exists() else ""
        one = {"run": run_index, "rc": rc, "status": "fail", "error": "", "direct_mapped": 0}
        if rc != 0 or not last_msg.strip():
            one["error"] = "codex_exec_failed_or_empty"
            run_results.append(one)
            continue
        try:
            obj = extract_json_object(last_msg)
            mapping = parse_model_items_to_paths(items=obj.get("items"), max_refs_per_item=max_refs_per_item)
            one["status"] = "ok"
            one["mapping"] = mapping
            one["direct_mapped"] = int(sum(len(v) for v in mapping.values()))
        except Exception as exc:  # noqa: BLE001
            one["error"] = str(exc)
        run_results.append(one)

    ok_runs = [r for r in run_results if str(r.get("status")) == "ok"]
    ok_votes = len(ok_runs)
    fail_votes = len(run_results) - ok_votes
    if ok_votes <= fail_votes or not ok_runs:
        return False, {"back": {}, "gameplay": {}}, run_results, cmd_ref
    chosen = sorted(ok_runs, key=lambda r: (-int(r.get("direct_mapped") or 0), int(r.get("run") or 0)))[0]
    chosen_mapping = chosen.get("mapping")
    if not isinstance(chosen_mapping, dict):
        chosen_mapping = {"back": {}, "gameplay": {}}
    return True, chosen_mapping, run_results, cmd_ref


def main() -> int:
    ap = argparse.ArgumentParser(description="Fill acceptance Refs: using Codex CLI (LLM).")
    ap.add_argument("--all", action="store_true", help="Process all tasks in tasks_back/tasks_gameplay.")
    ap.add_argument("--task-id", default=None, help="Process a single task id (master id).")
    ap.add_argument("--write", action="store_true", help="Write JSON files in-place. Without this flag, dry-run.")
    ap.add_argument("--overwrite-existing", action="store_true", help="Overwrite existing Refs: in acceptance items.")
    ap.add_argument("--rewrite-placeholders", action="store_true", help="Rewrite existing placeholder-like Refs.")
    ap.add_argument("--timeout-sec", type=int, default=300, help="codex exec timeout per task (default: 300).")
    ap.add_argument("--max-refs-per-item", type=int, default=2, help="Max refs per acceptance item (default: 2).")
    ap.add_argument("--candidate-limit", type=int, default=30, help="Max existing candidate tests to provide to model.")
    ap.add_argument("--max-tasks", type=int, default=0, help="Optional cap; 0 means no limit.")
    ap.add_argument("--consensus-runs", type=int, default=1, help="Run per-task LLM proposal N times and take majority-success (default: 1).")
    ap.add_argument("--self-check", action="store_true", help="Run deterministic local self-check only.")
    args = ap.parse_args()

    if bool(args.self_check):
        out_dir = ci_dir("sc-llm-acceptance-refs-self-check")
        ok, payload, report = run_fill_acceptance_refs_self_check(
            is_allowed_test_path=is_allowed_test_path,
            parse_model_items_to_paths=parse_model_items_to_paths,
        )
        write_json(out_dir / "summary.json", payload)
        write_json(out_dir / "verdict.json", payload)
        write_text(out_dir / "report.md", report)
        print(f"SC_LLM_ACCEPTANCE_REFS_SELF_CHECK status={'ok' if ok else 'fail'} out={out_dir}")
        return 0 if ok else 1

    root = repo_root()
    out_dir = ci_dir("sc-llm-acceptance-refs")
    tasks_json_p, back_p, gameplay_p = default_paths()
    tasks_json = load_json(tasks_json_p)
    master_by_id = {str(t.get("id")): t for t in iter_master_tasks(tasks_json)}
    back = load_json(back_p)
    gameplay = load_json(gameplay_p)
    if not isinstance(back, list) or not isinstance(gameplay, list):
        print("SC_LLM_ACCEPTANCE_REFS ERROR: tasks_back/tasks_gameplay must be JSON arrays.")
        return 2

    back_by_id = {int(t.get("taskmaster_id")): t for t in back if isinstance(t, dict) and isinstance(t.get("taskmaster_id"), int)}
    gameplay_by_id = {int(t.get("taskmaster_id")): t for t in gameplay if isinstance(t, dict) and isinstance(t.get("taskmaster_id"), int)}
    code, task_ids = _parse_task_ids_arg(raw_task_id=args.task_id, run_all=bool(args.all), back_by_id=back_by_id, gameplay_by_id=gameplay_by_id)
    if code != 0:
        print("SC_LLM_ACCEPTANCE_REFS ERROR: specify --task-id <n> or --all")
        return code
    if int(args.max_tasks) > 0:
        task_ids = task_ids[: int(args.max_tasks)]

    all_tests = list_existing_tests(root=root)
    prd_excerpt, prd_source = extract_prd_excerpt(root=root)
    any_updates = 0
    hard_fail = False
    results: list[dict[str, Any]] = []
    consensus_runs = max(1, int(args.consensus_runs))

    for tid in task_ids:
        master = master_by_id.get(str(tid))
        back_task = back_by_id.get(tid)
        gameplay_task = gameplay_by_id.get(tid)
        missing, overwrite_indices, prefer_gd = _collect_missing_for_task(
            task_id=tid,
            master=master,
            back_task=back_task,
            gameplay_task=gameplay_task,
            overwrite_existing=bool(args.overwrite_existing),
            rewrite_placeholders=bool(args.rewrite_placeholders),
        )
        if not missing:
            results.append({"task_id": tid, "status": "skipped", "reason": "no_missing_refs"})
            continue

        existing_candidates = pick_existing_candidates(all_tests=all_tests, task_id=tid, title=str((master or {}).get("title") or ""), limit=int(args.candidate_limit))
        prompt = build_prompt(
            root=root,
            prd_excerpt=prd_excerpt,
            task_id=tid,
            master=master,
            back=back_task,
            gameplay=gameplay_task,
            missing_items=missing,
            existing_candidates=existing_candidates,
            max_refs_per_item=int(args.max_refs_per_item),
        )
        prompt_path = out_dir / f"prompt-{tid}.txt"
        write_text(prompt_path, prompt)

        ok, mapping, run_results, cmd_ref = _run_consensus_for_task(
            root=root,
            out_dir=out_dir,
            task_id=tid,
            prompt=prompt,
            timeout_sec=int(args.timeout_sec),
            max_refs_per_item=int(args.max_refs_per_item),
            consensus_runs=consensus_runs,
        )

        task_result: dict[str, Any] = {
            "task_id": tid,
            "status": "ok",
            "missing_items": len(missing),
            "runs": run_results,
            "cmd": cmd_ref,
            "prompt": str(prompt_path.relative_to(root)).replace("\\", "/"),
        }
        if not ok:
            task_result["status"] = "fail"
            task_result["error"] = "consensus_no_majority_success"
            results.append(task_result)
            hard_fail = True
            continue

        for key in missing:
            if key.view not in mapping:
                mapping[key.view] = {}
            if key.index not in mapping[key.view]:
                mapping[key.view][key.index] = [default_ref_for(task_id=tid, prefer_gd=prefer_gd)]

        if args.write:
            a11y_task = is_a11y_task(master=master)
            if isinstance(back_task, dict):
                any_updates += apply_paths_to_view_entry(
                    root=root,
                    entry=back_task,
                    task_id=tid,
                    a11y_task=a11y_task,
                    overwrite_existing=bool(args.overwrite_existing),
                    overwrite_indices=overwrite_indices["back"],
                    paths_by_index=mapping["back"],
                    prefer_gd=prefer_gd,
                )
            if isinstance(gameplay_task, dict):
                any_updates += apply_paths_to_view_entry(
                    root=root,
                    entry=gameplay_task,
                    task_id=tid,
                    a11y_task=a11y_task,
                    overwrite_existing=bool(args.overwrite_existing),
                    overwrite_indices=overwrite_indices["gameplay"],
                    paths_by_index=mapping["gameplay"],
                    prefer_gd=prefer_gd,
                )
        task_result["mapped_items"] = int(sum(len(v) for v in mapping.values()))
        results.append(task_result)

    if args.write and any_updates > 0:
        back_p.write_text(json.dumps(back, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        gameplay_p.write_text(json.dumps(gameplay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    missing_after = 0
    if args.write and any_updates > 0:
        for tid in task_ids:
            for entry in [back_by_id.get(tid), gameplay_by_id.get(tid)]:
                if not isinstance(entry, dict):
                    continue
                for a in (entry.get("acceptance") or []):
                    s = str(a or "").strip()
                    if s and not REFS_RE.search(s):
                        missing_after += 1

    status = "fail" if hard_fail or (args.write and missing_after) else "ok"
    summary = {
        "cmd": "sc-llm-fill-acceptance-refs",
        "date": today_str(),
        "write": bool(args.write),
        "overwrite_existing": bool(args.overwrite_existing),
        "rewrite_placeholders": bool(args.rewrite_placeholders),
        "tasks": len(task_ids),
        "any_updates": any_updates,
        "results": results,
        "missing_after_write": missing_after,
        "out_dir": str(out_dir),
        "status": status,
        "consensus_runs": consensus_runs,
        "prd_source": prd_source,
    }
    schema_ok, schema_errors, checked_summary = validate_fill_acceptance_summary(summary)
    if not schema_ok:
        checked_summary["status"] = "fail"
        checked_summary["summary_errors"] = schema_errors
        write_json(out_dir / "summary.json", checked_summary)
        print(f"SC_LLM_ACCEPTANCE_REFS status=fail reason=summary_schema_invalid tasks={len(task_ids)} out={out_dir}")
        return 1

    write_json(out_dir / "summary.json", checked_summary)
    print(f"SC_LLM_ACCEPTANCE_REFS status={status} tasks={len(task_ids)} out={out_dir}")
    return 1 if status == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
