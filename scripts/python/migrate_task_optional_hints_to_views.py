#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_task_optional_hints_to_views

Goal:
  Reduce semantic drift ("done not real") by removing non-core / non-portable
  optional hints from `.taskmaster/tasks/tasks.json` (master `details` /
  `testStrategy`) and migrating them into view task files:
    - `.taskmaster/tasks/tasks_back.json`
    - `.taskmaster/tasks/tasks_gameplay.json`

Deterministic policy (blacklist, conservative):
  A line is treated as an optional hint if it matches one of:
    - Explicit optional/hint prefixes:
        "Optional:" / "可选:" / "建议:" / "加固:" / "演示:" / "示例:" / "参考:"
        (CJK prefixes are matched via unicode escapes to avoid encoding issues)
    - Local demo references/paths (including absolute Windows paths)
    - Extra add-ons: "Supplement:" / "Add-on:" / "Extra:"

Where it goes:
  - View `test_strategy` list, normalized to a single "Optional: ..." prefix.

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

_CN_OPT = r"\u53ef\u9009"  # 可选
_CN_SUG = r"\u5efa\u8bae"  # 建议
_CN_HARD = r"\u52a0\u56fa"  # 加固
_CN_DEMO = r"\u6f14\u793a"  # 演示
_CN_EXAMPLE = r"\u793a\u4f8b"  # 示例
_CN_REF = r"\u53c2\u8003"  # 参考
_CN_COLON = r"[:\uFF1A]"  # : or ：

OPTIONAL_PREFIX_RE = re.compile(
    rf"^\s*(?:[-*]\s*)?(?:Optional\s*:|{_CN_OPT}\s*{_CN_COLON}|{_CN_SUG}\s*{_CN_COLON}|{_CN_HARD}\s*{_CN_COLON}|{_CN_DEMO}\s*{_CN_COLON}|{_CN_EXAMPLE}\s*{_CN_COLON}|{_CN_REF}\s*{_CN_COLON})",
    flags=re.IGNORECASE,
)
OPTIONAL_PAREN_PREFIX_RE = re.compile(
    rf"^\s*(?:[-*]\s*)?[\(\[]?(?:{_CN_OPT}|{_CN_SUG}|{_CN_HARD})[\)\]]",
    flags=re.IGNORECASE,
)
LOCAL_DEMO_RE = re.compile(r"\b(local demo|demo references|demo paths)\b", flags=re.IGNORECASE)
SUPPLEMENT_PREFIX_RE = re.compile(
    rf"^\s*(?:[-*]\s*)?(?:supplement|add-?on|extra)\s*{_CN_COLON}",
    flags=re.IGNORECASE,
)
OPTIONAL_CONTEXT_RE = re.compile(
    rf"(?:\boptional(?:\s+hint)?\s*{_CN_COLON}|\bhint(?:\s+path)?\s*{_CN_COLON}|\bdemo(?:\s+path|s)?\s*{_CN_COLON}|{_CN_OPT}\s*{_CN_COLON}|{_CN_SUG}\s*{_CN_COLON}|{_CN_HARD}\s*{_CN_COLON}|{_CN_DEMO}\s*{_CN_COLON}|{_CN_EXAMPLE}\s*{_CN_COLON}|{_CN_REF}\s*{_CN_COLON}|\b(?:supplement|add-?on|extra)\b\s*{_CN_COLON}|\b(local demo|demo references|demo paths)\b)",
    flags=re.IGNORECASE,
)


def _norm_space(text: str) -> str:
    s = str(text or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _is_optional_hint_line(line: str) -> bool:
    s = _norm_space(line)
    if not s:
        return False
    if OPTIONAL_PREFIX_RE.match(s) or OPTIONAL_PAREN_PREFIX_RE.match(s):
        return True
    if LOCAL_DEMO_RE.search(s):
        return True
    if ABS_PATH_RE.search(s):
        # Absolute path alone is not enough; require optional/hint context.
        return bool(OPTIONAL_CONTEXT_RE.search(s))
    if SUPPLEMENT_PREFIX_RE.match(s):
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
    if SUPPLEMENT_PREFIX_RE.match(s):
        return False
    return True


def _to_optional_prefix_item(text: str) -> str:
    s = str(text or "").strip()
    if not s:
        return ""
    # Strip legacy markers.
    s = re.sub(r"^\[MIGRATED_FROM_ACCEPTANCE:[^\]]+\]\s*", "", s)
    # Strip leading bullet.
    s = re.sub(r"^\s*[-*]\s*", "", s)
    # Normalize into a single "Optional:" marker.
    s = OPTIONAL_PREFIX_RE.sub("", s)
    s = OPTIONAL_PAREN_PREFIX_RE.sub("", s)
    s = SUPPLEMENT_PREFIX_RE.sub("", s)
    s = re.sub(r"^(Optional:)\s*", "", s, flags=re.IGNORECASE)
    s = s.strip()
    return f"Optional: {s}" if s else ""


def _dedup_key(text: str) -> str:
    s = str(text or "").strip()
    if not s:
        return ""
    s = re.sub(r"^\[MIGRATED_FROM_ACCEPTANCE:[^\]]+\]\s*", "", s)
    s = re.sub(r"^\s*[-*]\s*", "", s)
    s = re.sub(r"^(Optional:)\s*", "", s, flags=re.IGNORECASE)
    s = OPTIONAL_PREFIX_RE.sub("", s)
    s = OPTIONAL_PAREN_PREFIX_RE.sub("", s)
    s = SUPPLEMENT_PREFIX_RE.sub("", s)
    s = REFS_CLAUSE_RE.sub("", s).strip()
    if s.lower().startswith("local demo") and ":" in s:
        s = s.split(":", 1)[1].strip()
    return _norm_space(s)


def _split_keep_lines(text: str) -> list[str]:
    if text is None:
        return []
    return str(text).splitlines()


def _rejoin_lines(lines: list[str]) -> str:
    out = list(lines)
    while out and not out[-1].strip():
        out.pop()
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


def _view_items_as_list(view_obj: Any) -> list[dict[str, Any]]:
    if isinstance(view_obj, list):
        return [x for x in view_obj if isinstance(x, dict)]
    if isinstance(view_obj, dict):
        items = view_obj.get("tasks") or view_obj.get("master", {}).get("tasks") or []
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
    return []


def _canonical_task_id(value: Any) -> str:
    s = str(value or "").strip()
    if not s:
        return ""
    if s.isdigit():
        return str(int(s))
    return s


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate optional hints out of tasks.json into view test_strategy.")
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

    back_items = _view_items_as_list(back)
    gameplay_items = _view_items_as_list(gameplay)
    if not back_items or not gameplay_items:
        # Views may legitimately be empty in early stages; keep failure explicit to avoid silent no-op.
        raise SystemExit("Invalid view task files: expected a non-empty list or {tasks:[...]} structure.")

    back_by_id: dict[str, dict[str, Any]] = {
        key: t for t in back_items if (key := _canonical_task_id(t.get("taskmaster_id")))
    }
    gameplay_by_id: dict[str, dict[str, Any]] = {
        key: t for t in gameplay_items if (key := _canonical_task_id(t.get("taskmaster_id")))
    }

    selected_ids: set[str] = set()
    if str(args.task_ids or "").strip():
        for raw in str(args.task_ids).split(","):
            s = str(raw or "").strip()
            if s:
                selected_ids.add(_canonical_task_id(s))

    changes: list[TaskChange] = []
    total_removed = 0
    total_added = 0
    total_normalized = 0
    skipped_no_changes = 0
    master_dirty = False
    back_dirty = False
    gameplay_dirty = False

    for t in master_tasks:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "").strip()
        tid_key = _canonical_task_id(tid)
        if not tid:
            continue
        if selected_ids and tid_key not in selected_ids:
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
        details_after = _rejoin_lines(kept_details) if moved_details else details_before
        master_details_changed = details_after != details_before
        if master_details_changed:
            t["details"] = details_after
            master_dirty = True

        master_ts_before = str(t.get("testStrategy") or "")
        master_ts_lines = _split_keep_lines(master_ts_before)
        kept_ts: list[str] = []
        for ln in master_ts_lines:
            if _is_optional_hint_line(ln):
                moved_test_strategy.append(ln)
            else:
                kept_ts.append(ln)
        master_ts_after = _rejoin_lines(kept_ts) if moved_test_strategy else master_ts_before
        master_ts_changed = master_ts_after != master_ts_before
        if master_ts_changed:
            t["testStrategy"] = master_ts_after
            master_dirty = True

        moved_optional_raw = [*moved_details, *moved_test_strategy]
        moved_optional = [_to_optional_prefix_item(x) for x in moved_optional_raw if _should_migrate_to_views(x)]
        moved_optional = [x for x in moved_optional if x.strip()]

        views_updated: list[str] = []
        view_items_added: dict[str, int] = {}
        view_items_normalized: dict[str, int] = {}
        missing_views: list[str] = []

        if not tid_key:
            skipped_no_changes += 1
            continue

        for view_name, view_map in (("back", back_by_id), ("gameplay", gameplay_by_id)):
            view_entry = view_map.get(tid_key)
            if not view_entry:
                missing_views.append(view_name)
                continue

            raw_ts = view_entry.get("test_strategy")
            if raw_ts is None:
                raw_ts = []
            if not isinstance(raw_ts, list):
                missing_views.append(view_name)
                continue

            existing = [str(x or "").strip() for x in raw_ts]
            normalized: list[str] = []
            ncount = 0
            for it in existing:
                if not it:
                    continue
                if _is_optional_hint_line(it) or it.startswith("[MIGRATED_FROM_ACCEPTANCE:"):
                    pref = _to_optional_prefix_item(it)
                    if pref and pref != it:
                        ncount += 1
                    if pref:
                        normalized.append(pref)
                    continue
                normalized.append(it)

            existing_set = {_dedup_key(x) for x in normalized if _dedup_key(x)}
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
                if view_name == "back":
                    back_dirty = True
                elif view_name == "gameplay":
                    gameplay_dirty = True

        total_removed += len(moved_details) + len(moved_test_strategy)

        if not (master_details_changed or master_ts_changed or views_updated):
            skipped_no_changes += 1
            continue

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
        "files_dirty": {
            "tasks_json": master_dirty,
            "tasks_back_json": back_dirty,
            "tasks_gameplay_json": gameplay_dirty,
        },
        "out_dir": str(out_dir.relative_to(root)).replace("\\", "/"),
    }

    report_lines: list[str] = []
    report_lines.append("# Migrate optional hints from tasks.json to view test_strategy")
    report_lines.append("")
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
        report_lines.append(
            f"- view_items_added: back={ch.view_items_added.get('back', 0)} gameplay={ch.view_items_added.get('gameplay', 0)}"
        )
        report_lines.append(
            f"- view_items_normalized: back={ch.view_items_normalized.get('back', 0)} gameplay={ch.view_items_normalized.get('gameplay', 0)}"
        )
        report_lines.append("")

    write_json(out_dir / "summary.json", summary)
    write_text(out_dir / "report.md", "\n".join(report_lines).strip() + "\n")

    if args.write:
        if master_dirty:
            write_json(master_p, master)
        if back_dirty:
            write_json(back_p, back)
        if gameplay_dirty:
            write_json(gameplay_p, gameplay)

    print(f"MIGRATE_OPTIONAL_HINTS status=ok write={bool(args.write)} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

