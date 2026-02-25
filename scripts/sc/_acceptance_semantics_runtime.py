#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any

from _util import write_text

from _acceptance_semantics_align import (
    MasterTaskInput,
    ViewInput,
    apply_acceptance,
    apply_description,
    build_prompt,
    find_view_entry,
    normalize_acceptance_lines,
    render_task_context,
    run_codex_exec,
    safe_parse_json,
    validate_output,
)


_TRANSIENT_TRACE_MARKERS = (
    "timeout",
    "timed out",
    "temporarily unavailable",
    "rate limit",
    "connection reset",
    "connection aborted",
    "transport error",
    "econnreset",
    "502",
    "503",
    "504",
)


def _should_retry_exec(rc: int, trace: str) -> bool:
    if int(rc) == 124:
        return True
    lower = str(trace or "").lower()
    return any(marker in lower for marker in _TRANSIENT_TRACE_MARKERS)


def _run_model_with_retry(*, prompt: str, task_out: Path, timeout_sec: int) -> tuple[str, dict[str, Any] | None, int]:
    max_attempts = 2
    last_msg_path = task_out / "output.json"
    for attempt in range(1, max_attempts + 1):
        rc, trace = run_codex_exec(prompt=prompt, out_last_message=last_msg_path, timeout_sec=int(timeout_sec))
        write_text(task_out / f"trace-attempt-{attempt}.log", trace)
        if attempt == 1:
            write_text(task_out / "trace.log", trace)
        if rc != 0:
            if attempt < max_attempts and _should_retry_exec(rc, trace):
                continue
            return f"codex_rc:{rc}", None, attempt
        out_text = last_msg_path.read_text(encoding="utf-8", errors="ignore") if last_msg_path.exists() else ""
        out_obj = safe_parse_json(out_text)
        if out_obj:
            return "ok", out_obj, attempt
        if attempt < max_attempts:
            continue
        return "invalid_json", None, attempt
    return "unexpected_retry_state", None, max_attempts


def _resolve_mode(*, status: str, append_only_for_done: bool, structural_for_not_done: bool) -> str:
    if str(status).lower() == "done":
        return "append-only" if bool(append_only_for_done) else "rewrite-only"
    return "append-only" if bool(structural_for_not_done) else "rewrite-only"


def _collect_view_inputs(*, tid: int, back: list[dict[str, Any]], gameplay: list[dict[str, Any]]) -> tuple[list[ViewInput], dict[str, Any] | None, dict[str, Any] | None]:
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
    return view_inputs, back_entry, gameplay_entry


def _apply_output(
    *,
    out_obj: dict[str, Any],
    back_entry: dict[str, Any] | None,
    gameplay_entry: dict[str, Any] | None,
    align_view_descriptions_to_master: bool,
) -> tuple[bool, bool, bool]:
    task_changed = False
    back_file_changed = False
    gameplay_file_changed = False
    if back_entry is not None and isinstance(out_obj.get("back"), dict):
        if bool(align_view_descriptions_to_master):
            new_desc_raw = out_obj["back"].get("description")
            if new_desc_raw is not None:
                old_desc = str(back_entry.get("description") or "").strip()
                new_desc = str(new_desc_raw).strip()
                if new_desc != old_desc:
                    apply_description(back_entry, new_desc_raw)
                    task_changed = True
                    back_file_changed = True
        new_acc = out_obj["back"].get("acceptance") or []
        if isinstance(new_acc, list):
            old_acc = normalize_acceptance_lines(back_entry.get("acceptance") or [])
            new_acc_norm = normalize_acceptance_lines(new_acc)
            if new_acc_norm != old_acc:
                apply_acceptance(back_entry, new_acc)
                task_changed = True
                back_file_changed = True
    if gameplay_entry is not None and isinstance(out_obj.get("gameplay"), dict):
        if bool(align_view_descriptions_to_master):
            new_desc_raw = out_obj["gameplay"].get("description")
            if new_desc_raw is not None:
                old_desc = str(gameplay_entry.get("description") or "").strip()
                new_desc = str(new_desc_raw).strip()
                if new_desc != old_desc:
                    apply_description(gameplay_entry, new_desc_raw)
                    task_changed = True
                    gameplay_file_changed = True
        new_acc = out_obj["gameplay"].get("acceptance") or []
        if isinstance(new_acc, list):
            old_acc = normalize_acceptance_lines(gameplay_entry.get("acceptance") or [])
            new_acc_norm = normalize_acceptance_lines(new_acc)
            if new_acc_norm != old_acc:
                apply_acceptance(gameplay_entry, new_acc)
                task_changed = True
                gameplay_file_changed = True
    return task_changed, back_file_changed, gameplay_file_changed


def run_alignment_tasks(
    *,
    task_ids: list[int],
    master_index: dict[int, MasterTaskInput],
    semantic_hints: dict[int, str],
    back: list[dict[str, Any]],
    gameplay: list[dict[str, Any]],
    out_dir: Path,
    apply: bool,
    timeout_sec: int,
    max_failures: int,
    structural_for_not_done: bool,
    append_only_for_done: bool,
    align_view_descriptions_to_master: bool,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    changed = 0
    skipped = 0
    failed = 0
    stopped_early = False
    back_file_changed = False
    gameplay_file_changed = False

    for tid in task_ids:
        master = master_index.get(tid)
        if not master:
            skipped += 1
            results.append({"task_id": tid, "status": "skipped", "reason": "missing_master"})
            continue

        view_inputs, back_entry, gameplay_entry = _collect_view_inputs(tid=tid, back=back, gameplay=gameplay)
        if not view_inputs:
            skipped += 1
            results.append({"task_id": tid, "status": "skipped", "reason": "missing_both_views"})
            continue

        mode = _resolve_mode(
            status=str(master.status),
            append_only_for_done=bool(append_only_for_done),
            structural_for_not_done=bool(structural_for_not_done),
        )
        task_out = out_dir / f"task-{tid}"
        task_out.mkdir(parents=True, exist_ok=True)
        task_context = render_task_context(
            master=master,
            view_inputs=view_inputs,
            mode=mode,
            align_view_descriptions=bool(align_view_descriptions_to_master),
            semantic_hint=semantic_hints.get(tid),
        )
        prompt = build_prompt(task_context)
        write_text(task_out / "prompt.md", prompt)

        reason, out_obj, attempts = _run_model_with_retry(
            prompt=prompt,
            task_out=task_out,
            timeout_sec=int(timeout_sec),
        )
        if reason != "ok" or not out_obj:
            failed += 1
            results.append({"task_id": tid, "status": "fail", "reason": reason, "dir": str(task_out), "attempts": attempts})
            if max_failures > 0 and failed >= max_failures:
                stopped_early = True
                break
            continue

        ok, validate_reason = validate_output(
            task_id=tid,
            mode=mode,
            view_inputs=view_inputs,
            out_obj=out_obj,
            align_view_descriptions=bool(align_view_descriptions_to_master),
        )
        if not ok:
            failed += 1
            results.append({"task_id": tid, "status": "fail", "reason": validate_reason, "dir": str(task_out), "attempts": attempts})
            if max_failures > 0 and failed >= max_failures:
                stopped_early = True
                break
            continue

        task_changed = False
        if bool(apply):
            task_changed, back_changed, gameplay_changed = _apply_output(
                out_obj=out_obj,
                back_entry=back_entry,
                gameplay_entry=gameplay_entry,
                align_view_descriptions_to_master=bool(align_view_descriptions_to_master),
            )
            back_file_changed = back_file_changed or back_changed
            gameplay_file_changed = gameplay_file_changed or gameplay_changed
            if task_changed:
                changed += 1

        results.append({"task_id": tid, "status": "ok", "dir": str(task_out), "applied": bool(apply), "mode": mode, "changed": task_changed, "attempts": attempts})

    return {
        "results": results,
        "changed": changed,
        "skipped": skipped,
        "failed": failed,
        "stopped_early": bool(stopped_early),
        "back_file_changed": bool(back_file_changed),
        "gameplay_file_changed": bool(gameplay_file_changed),
    }
