#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


def validate_subtasks_coverage_schema(raw_obj: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    errors: list[str] = []
    obj = dict(raw_obj or {})

    task_id = str(obj.get("task_id") or "").strip()
    if not task_id:
        errors.append("task_id_missing")
    else:
        obj["task_id"] = task_id

    status = str(obj.get("status") or "").strip().lower()
    if status not in {"ok", "fail"}:
        errors.append("status_invalid")
    else:
        obj["status"] = status

    subtasks = obj.get("subtasks")
    if not isinstance(subtasks, list):
        errors.append("subtasks_not_list")
        subtasks = []
    normalized_subtasks: list[dict[str, Any]] = []
    for idx, item in enumerate(subtasks, start=1):
        if not isinstance(item, dict):
            errors.append(f"subtask_not_object:{idx}")
            continue
        sid = str(item.get("id") or "").strip()
        title = str(item.get("title") or "").strip()
        covered = item.get("covered")
        if not sid:
            errors.append(f"subtask_id_missing:{idx}")
        if not title:
            errors.append(f"subtask_title_missing:{idx}")
        if not isinstance(covered, bool):
            errors.append(f"subtask_covered_not_bool:{idx}")

        matches = item.get("matches", [])
        if not isinstance(matches, list):
            errors.append(f"subtask_matches_not_list:{idx}")
            matches = []
        if isinstance(covered, bool) and covered and len(matches) < 1:
            errors.append(f"subtask_matches_required_when_covered:{idx}")
        for midx, match in enumerate(matches, start=1):
            if not isinstance(match, dict):
                errors.append(f"match_not_object:{idx}.{midx}")
                continue
            view = str(match.get("view") or "").strip()
            if view not in {"back", "gameplay"}:
                errors.append(f"match_view_invalid:{idx}.{midx}")
            acceptance_index = match.get("acceptance_index")
            if not isinstance(acceptance_index, int) or acceptance_index < 1:
                errors.append(f"match_acceptance_index_invalid:{idx}.{midx}")
            acceptance_excerpt = str(match.get("acceptance_excerpt") or "").strip()
            if not acceptance_excerpt:
                errors.append(f"match_acceptance_excerpt_missing:{idx}.{midx}")

        reason = item.get("reason", "")
        if not isinstance(reason, str):
            errors.append(f"subtask_reason_not_string:{idx}")
        normalized_subtasks.append(item)
    obj["subtasks"] = normalized_subtasks

    uncovered = obj.get("uncovered_subtask_ids", [])
    if uncovered is None:
        uncovered = []
    if not isinstance(uncovered, list) or any(not str(x or "").strip() for x in uncovered):
        errors.append("uncovered_subtask_ids_invalid")
    else:
        obj["uncovered_subtask_ids"] = [str(x).strip() for x in uncovered]

    notes = obj.get("notes", [])
    if notes is None:
        notes = []
    if not isinstance(notes, list) or any(not isinstance(x, str) for x in notes):
        errors.append("notes_invalid")
    else:
        obj["notes"] = notes

    return not errors, errors, obj


def run_subtasks_coverage_self_check() -> tuple[bool, dict[str, Any]]:
    issues: list[str] = []
    checks: list[dict[str, Any]] = []
    good = {
        "task_id": "1",
        "status": "ok",
        "subtasks": [
            {
                "id": "1.1",
                "title": "Seed init",
                "covered": True,
                "matches": [{"view": "back", "acceptance_index": 1, "acceptance_excerpt": "seed init"}],
                "reason": "covered",
            }
        ],
        "uncovered_subtask_ids": [],
        "notes": [],
    }
    ok_good, err_good, _ = validate_subtasks_coverage_schema(good)
    checks.append({"name": "valid_payload", "ok": ok_good, "errors": err_good})
    if not ok_good:
        issues.append("valid_payload_should_pass")

    bad = {
        "task_id": "1",
        "status": "ok",
        "subtasks": [{"id": "1.1", "title": "Seed init", "covered": "true", "matches": [], "reason": "bad"}],
        "uncovered_subtask_ids": [],
        "notes": [],
    }
    ok_bad, err_bad, _ = validate_subtasks_coverage_schema(bad)
    checks.append({"name": "invalid_payload", "ok": (not ok_bad), "errors": err_bad})
    if ok_bad or not any("subtask_covered_not_bool" in e for e in err_bad):
        issues.append("invalid_payload_should_fail_with_covered_bool_error")

    ok = len(issues) == 0
    return ok, {"status": "ok" if ok else "fail", "issues": issues, "checks": checks}


def collect_uncovered_subtasks(obj: dict[str, Any], *, subtasks: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    uncovered: list[str] = []
    for it in obj.get("subtasks") or []:
        if not isinstance(it, dict):
            continue
        covered = bool(it.get("covered"))
        sid = str(it.get("id") or "").strip()
        if sid and not covered:
            uncovered.append(sid)

    model_ids = {str((it or {}).get("id") or "").strip() for it in (obj.get("subtasks") or []) if isinstance(it, dict)}
    input_ids = [str(s.get("id") or "").strip() for s in subtasks]
    missing_reported = [sid for sid in input_ids if sid and sid not in model_ids]
    if missing_reported:
        obj["status"] = "fail"
        for sid in missing_reported:
            if sid not in uncovered:
                uncovered.append(sid)
        notes = obj.get("notes") or []
        if not isinstance(notes, list):
            notes = []
        obj["notes"] = notes + [f"deterministic_hard_gate: missing_subtask_report:{sid}" for sid in missing_reported]

    return uncovered, obj


def render_subtasks_coverage_report(*, task_id: str, verdict_status: str, obj: dict[str, Any], uncovered: list[str]) -> str:
    report_lines = [f"# T{task_id} subtasks coverage", "", f"Status: {verdict_status}", ""]
    report_lines.append("## Subtasks")
    for it in obj.get("subtasks") or []:
        if not isinstance(it, dict):
            continue
        sid = str(it.get("id") or "").strip()
        st = str(it.get("title") or "").strip()
        covered = bool(it.get("covered"))
        reason = str(it.get("reason") or "").strip()
        report_lines.append(f"- {sid}: {st} :: covered={covered}")
        if reason:
            report_lines.append(f"  - reason: {reason}")
        matches = it.get("matches") or []
        if isinstance(matches, list) and matches:
            report_lines.append("  - matches:")
            for m in matches:
                if not isinstance(m, dict):
                    continue
                view = str(m.get("view") or "").strip()
                aidx = m.get("acceptance_index")
                excerpt = str(m.get("acceptance_excerpt") or "").strip()
                report_lines.append(f"    - {view}:{aidx}: {excerpt}")
    report_lines.append("")
    if uncovered:
        report_lines.append("## Uncovered")
        for sid in uncovered:
            report_lines.append(f"- {sid}")
        report_lines.append("")
    notes = obj.get("notes") or []
    if isinstance(notes, list) and notes:
        report_lines.append("## Notes")
        for n in notes:
            report_lines.append(f"- {str(n)}")
        report_lines.append("")
    report_lines.append("See also: verdict.json, prompt.md, trace.log, output-last-message.txt")
    return "\n".join(report_lines) + "\n"
