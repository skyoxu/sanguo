#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_task_optional_hints_to_views

Goal:
  Reduce "done not real" semantic drift by removing non-deliverable hints from
  `.taskmaster/tasks/tasks.json` (master `details` / `testStrategy`) and moving them
  into view task files:
    - `.taskmaster/tasks/tasks_back.json`
    - `.taskmaster/tasks/tasks_gameplay.json`

What gets migrated:
  - Optional hardening suggestions (e.g. lines starting with "可选"/"可选加固")
  - Local demo references/paths (including absolute paths)
  - "加固建议" style test add-ons (e.g. "加入 xUnit 用例：...")

Where it goes:
  - View `test_strategy` (list of strings), prefixed with "Optional: ".

Important:
  - This script does NOT touch view `acceptance` items.
  - It does NOT create/update `Refs:` inside acceptance.
  - It is deterministic: no LLM calls.

Outputs (audit trail):
  logs/ci/<YYYY-MM-DD>/migrate-task-optional-hints/
    - summary.json
    - report.md

Usage (Windows, PowerShell):
  py -3 scripts/python/migrate_task_optional_hints_to_views.py
  py -3 scripts/python/migrate_task_optional_hints_to_views.py --write
  py -3 scripts/python/migrate_task_optional_hints_to_views.py --task-ids 6,12 --write
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def ci_out_dir(name: str) -> Path:
    out = repo_root() / "logs" / "ci" / today_str() / name
    out.mkdir(parents=True, exist_ok=True)
    return out


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(str(text).replace("\r\n", "\n"), encoding="utf-8", newline="\n")


ABS_PATH_RE = re.compile(r"\b[A-Za-z]:\\")
REFS_CLAUSE_RE = re.compile(r"\bRefs\s*:\s*.+$", flags=re.IGNORECASE)


def _norm_space(text: str) -> str:
    s = str(text or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _is_optional_hint_line(line: str) -> bool:
    s = _norm_space(line)
    if not s:
        return False

    # Keep this conservative: only migrate "clearly optional" or "clearly local demo" lines.
    if s.lower().startswith("optional:"):
        return True
    if s.startswith("可选") or "可选加固" in s:
        return True
    if s.lower().startswith("local demo"):
        return True
    if "demo paths" in s.lower() or "demo references" in s.lower():
        return True
    if ABS_PATH_RE.search(s):
        return True
    if s.startswith("加入 xUnit 用例：") or s.startswith("加入 xUnit 用例:"):
        return True
    if s.startswith("补充：") or s.startswith("补充:"):
        # Treat "supplement" as non-core test add-on to avoid obligation pollution.
        return True
    return False


def _should_migrate_to_views(line: str) -> bool:
    """
    Some optional lines are safe to delete from tasks.json but not worth copying
    into view files (to avoid duplication/noise).
    """
    s = _norm_space(line)
    if not s:
        return False
    # "补充：" lines tend to be paraphrased elsewhere in view test_strategy already.
    # Keep the migration deterministic and low-noise by not re-copying them.
    if s.startswith("补充：") or s.startswith("补充:"):
        return False
    return True


def _to_optional_prefix_item(text: str) -> str:
    s = str(text or "").strip()
    if not s:
        return s

    # Strip legacy markers.
    s = re.sub(r"^\[MIGRATED_FROM_ACCEPTANCE:[^\]]+\]\s*", "", s)

    # Normalize common optional prefixes into a single "Optional:" marker.
    s = re.sub(r"^(可选加固[-：:]?|可选[-：:]?)\s*", "", s)
    s = re.sub(r"^(Optional:)\s*", "", s, flags=re.IGNORECASE)

    s = s.strip()
    return f"Optional: {s}"


def _dedup_key(text: str) -> str:
    """
    Compare optional/test-hint items ignoring:
      - leading Optional/可选 markers
      - migrated tags
      - trailing Refs: ... suffixes (view test_strategy may contain them)
    """
    s = str(text or "").strip()
    if not s:
        return ""
    s = re.sub(r"^\[MIGRATED_FROM_ACCEPTANCE:[^\]]+\]\s*", "", s)
    s = re.sub(r"^(Optional:)\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^(可选加固[-：:]?|可选[-：:]?)\s*", "", s)
    s = REFS_CLAUSE_RE.sub("", s).strip()
    # Normalize local demo markers to avoid minor wording variations.
    if s.lower().startswith("local demo") and ":" in s:
        s = s.split(":", 1)[1].strip()
    return _norm_space(s)


def _split_keep_lines(text: str) -> list[str]:
    if text is None:
        return []
    return str(text).splitlines()


def _rejoin_lines(lines: list[str]) -> str:
    # Remove trailing whitespace lines while preserving paragraph breaks.
    out = list(lines)
    while out and not out[-1].strip():
        out.pop()
    # Collapse 3+ consecutive blank lines to 2.
    collapsed: list[str] = []
    blank_run = 0
    for ln in out:
        if ln.strip():
            blank_run = 0
            collapsed.append(ln.rstrip())
            continue
        blank_run += 1
        if blank_run <= 2:
            collapsed.append("")
    return "\n".join(collapsed).strip() + ("\n" if collapsed else "")


@dataclass
class TaskChange:
    task_id: str
    moved_from_details: list[str]
    moved_from_test_strategy: list[str]
    master_details_changed: bool
    master_test_strategy_changed: bool
    views_updated: list[str]  # back/gameplay
    view_items_added: dict[str, int]
    view_items_normalized: dict[str, int]
    missing_views: list[str]


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate optional/demo/hardening hints out of tasks.json into view test_strategy.")
    ap.add_argument("--task-ids", default="", help="Comma-separated master task ids (e.g. 6,12). Default: all.")
    ap.add_argument("--write", action="store_true", help="Write changes to disk.")
    args = ap.parse_args()

    root = repo_root()
    out_dir = ci_out_dir("migrate-task-optional-hints")

    master_p = root / ".taskmaster" / "tasks" / "tasks.json"
    back_p = root / ".taskmaster" / "tasks" / "tasks_back.json"
    gameplay_p = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"

    master = read_json(master_p)
    back = read_json(back_p)
    gameplay = read_json(gameplay_p)

    master_tasks = (master.get("master") or {}).get("tasks") or []
    if not isinstance(master_tasks, list):
        raise SystemExit("Invalid tasks.json: master.tasks is not a list.")

    back_items = back if isinstance(back, list) else back.get("tasks") or back.get("master", {}).get("tasks") or []
    gameplay_items = gameplay if isinstance(gameplay, list) else gameplay.get("tasks") or gameplay.get("master", {}).get("tasks") or []
    if not isinstance(back_items, list) or not isinstance(gameplay_items, list):
        raise SystemExit("Invalid view task files: expected list or {tasks: [...]} structure.")

    back_by_id: dict[int, dict[str, Any]] = {int(t.get("taskmaster_id")): t for t in back_items if isinstance(t, dict) and str(t.get("taskmaster_id") or "").isdigit()}
    gameplay_by_id: dict[int, dict[str, Any]] = {int(t.get("taskmaster_id")): t for t in gameplay_items if isinstance(t, dict) and str(t.get("taskmaster_id") or "").isdigit()}

    selected_ids: set[str] = set()
    if str(args.task_ids or "").strip():
        for raw in str(args.task_ids).split(","):
            s = str(raw or "").strip()
            if s:
                selected_ids.add(s)

    changes: list[TaskChange] = []
    total_removed = 0
    total_added = 0
    total_normalized = 0
    skipped_no_changes = 0

    for t in master_tasks:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "").strip()
        if not tid:
            continue
        if selected_ids and tid not in selected_ids:
            continue

        moved_details: list[str] = []
        moved_test_strategy: list[str] = []

        details_before = str(t.get("details") or "")
        details_lines = _split_keep_lines(details_before)
        kept_details: list[str] = []
        for ln in details_lines:
            if _is_optional_hint_line(ln):
                moved_details.append(ln)
            else:
                kept_details.append(ln)
        details_after = _rejoin_lines(kept_details) if details_lines else details_before

        ts_before = str(t.get("testStrategy") or "")
        ts_lines = _split_keep_lines(ts_before)
        kept_ts: list[str] = []
        for ln in ts_lines:
            if _is_optional_hint_line(ln):
                moved_test_strategy.append(ln)
            else:
                kept_ts.append(ln)
        ts_after = _rejoin_lines(kept_ts) if ts_lines else ts_before

        master_details_changed = details_after != details_before
        master_ts_changed = ts_after != ts_before

        # If there is nothing to move and no normalization needed, skip.
        # (Normalization of view test_strategy is done only when we touch the task.)
        if not moved_details and not moved_test_strategy and not master_details_changed and not master_ts_changed:
            skipped_no_changes += 1
            continue

        # Update master task.
        if master_details_changed:
            t["details"] = details_after.rstrip("\n")
        if master_ts_changed:
            t["testStrategy"] = ts_after.rstrip("\n")

        # Update views: prefer both when present; allow missing one side.
        moved_all = [x for x in moved_details + moved_test_strategy if _norm_space(x)]
        moved_for_views = [x for x in moved_all if _should_migrate_to_views(x)]
        moved_optional = [_to_optional_prefix_item(x) for x in moved_for_views if _norm_space(x)]

        views_updated: list[str] = []
        missing_views: list[str] = []
        view_items_added: dict[str, int] = {"back": 0, "gameplay": 0}
        view_items_normalized: dict[str, int] = {"back": 0, "gameplay": 0}

        for view_name, view_map in [("back", back_by_id), ("gameplay", gameplay_by_id)]:
            view_entry = view_map.get(int(tid)) if tid.isdigit() else None
            if not isinstance(view_entry, dict):
                missing_views.append(view_name)
                continue

            # Ensure test_strategy is a list.
            raw_ts = view_entry.get("test_strategy")
            if raw_ts is None:
                view_entry["test_strategy"] = []
                raw_ts = view_entry["test_strategy"]
            if not isinstance(raw_ts, list):
                # Do not silently rewrite unexpected types.
                missing_views.append(view_name)
                continue

            # Normalize existing optional-like items in view test_strategy.
            existing = list(raw_ts)
            normalized: list[str] = []
            ncount = 0
            for it in existing:
                s = str(it or "").strip()
                if not s:
                    normalized.append(s)
                    continue
                if _is_optional_hint_line(s) or s.startswith("[MIGRATED_FROM_ACCEPTANCE:"):
                    pref = _to_optional_prefix_item(s)
                    if pref != s:
                        ncount += 1
                    normalized.append(pref)
                else:
                    normalized.append(s)

            # Append newly moved optional hints (dedup by normalized text).
            existing_set = { _dedup_key(x) for x in normalized if _dedup_key(x) }
            add_count = 0
            for item in moved_optional:
                k = _dedup_key(item)
                if not k or k in existing_set:
                    continue
                normalized.append(item)
                existing_set.add(k)
                add_count += 1

            if add_count or ncount:
                view_entry["test_strategy"] = normalized
                views_updated.append(view_name)
                view_items_added[view_name] = add_count
                view_items_normalized[view_name] = ncount
                total_added += add_count
                total_normalized += ncount

        total_removed += len(moved_details) + len(moved_test_strategy)

        changes.append(
            TaskChange(
                task_id=tid,
                moved_from_details=moved_details,
                moved_from_test_strategy=moved_test_strategy,
                master_details_changed=master_details_changed,
                master_test_strategy_changed=master_ts_changed,
                views_updated=views_updated,
                view_items_added=view_items_added,
                view_items_normalized=view_items_normalized,
                missing_views=missing_views,
            )
        )

    summary = {
        "cmd": "migrate_task_optional_hints_to_views",
        "date": today_str(),
        "write": bool(args.write),
        "tasks_selected": sorted(selected_ids) if selected_ids else "all",
        "tasks_total_in_master": len(master_tasks),
        "tasks_changed": len(changes),
        "tasks_skipped_no_changes": skipped_no_changes,
        "removed_lines_from_master": total_removed,
        "added_optional_items_to_views": total_added,
        "normalized_optional_items_in_views": total_normalized,
        "out_dir": str(out_dir.relative_to(root)).replace("\\", "/"),
    }

    report_lines: list[str] = []
    report_lines.append("# Migrate optional hints from tasks.json to view test_strategy\n")
    report_lines.append(f"- date: {today_str()}")
    report_lines.append(f"- write: {bool(args.write)}")
    report_lines.append(f"- tasks_changed: {len(changes)}")
    report_lines.append(f"- removed_lines_from_master: {total_removed}")
    report_lines.append(f"- added_optional_items_to_views: {total_added}")
    report_lines.append(f"- normalized_optional_items_in_views: {total_normalized}")
    report_lines.append("")

    for ch in changes[:200]:
        report_lines.append(f"## Task {ch.task_id}")
        report_lines.append(f"- master.details changed: {ch.master_details_changed}")
        report_lines.append(f"- master.testStrategy changed: {ch.master_test_strategy_changed}")
        report_lines.append(f"- views_updated: {', '.join(ch.views_updated) if ch.views_updated else '(none)'}")
        if ch.missing_views:
            report_lines.append(f"- missing_views: {', '.join(ch.missing_views)}")
        if ch.moved_from_details:
            report_lines.append("- moved_from_details:")
            for x in ch.moved_from_details[:20]:
                report_lines.append(f"  - {x}")
        if ch.moved_from_test_strategy:
            report_lines.append("- moved_from_testStrategy:")
            for x in ch.moved_from_test_strategy[:20]:
                report_lines.append(f"  - {x}")
        report_lines.append(f"- view_items_added: back={ch.view_items_added.get('back', 0)} gameplay={ch.view_items_added.get('gameplay', 0)}")
        report_lines.append(f"- view_items_normalized: back={ch.view_items_normalized.get('back', 0)} gameplay={ch.view_items_normalized.get('gameplay', 0)}")
        report_lines.append("")

    write_json(out_dir / "summary.json", summary)
    write_text(out_dir / "report.md", "\n".join(report_lines).strip() + "\n")

    if args.write:
        write_json(master_p, master)
        write_json(back_p, back)
        write_json(gameplay_p, gameplay)

    print(f"MIGRATE_OPTIONAL_HINTS status=ok write={bool(args.write)} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
