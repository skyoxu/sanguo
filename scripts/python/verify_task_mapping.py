#!/usr/bin/env python3
"""
Verify that Taskmaster master tasks are properly mapped
to tasks_back.json and tasks_gameplay.json views.

This script is intended as a human-readable report, not a hard CI gate.
All messages are ASCII-only to comply with repository guidelines.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_view_index(tasks: List[Dict[str, Any]], view_name: str) -> Dict[int, Dict[str, Any]]:
    """Index tasks by taskmaster_id for a given view (back/gameplay)."""
    index: Dict[int, Dict[str, Any]] = {}
    for task in tasks:
        tm_id = task.get("taskmaster_id")
        if tm_id is None:
            continue
        entry = index.setdefault(tm_id, {})
        entry[view_name] = {
            "id": task.get("id"),
            "has_adr_refs": bool(task.get("adr_refs")),
            "has_test_refs": bool(task.get("test_refs")),
            "has_acceptance": bool(task.get("acceptance")),
            "has_story_id": bool(task.get("story_id")),
        }
    return index


def status_flag(value: bool) -> str:
    return "[OK]" if value else "[MISS]"


def main() -> None:
    root = Path(".")
    tasks_json_path = root / ".taskmaster" / "tasks" / "tasks.json"
    back_path = root / ".taskmaster" / "tasks" / "tasks_back.json"
    gameplay_path = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"

    print("=" * 60)
    print("Task mapping verification report")
    print("=" * 60)

    tasks_data = load_json(tasks_json_path)
    if not tasks_data:
        print(f"[ERROR] Cannot load master tasks from {tasks_json_path}")
        return

    master_tasks: List[Dict[str, Any]] = tasks_data.get("master", {}).get("tasks", [])
    print(f"\nMaster tasks count: {len(master_tasks)}\n")

    back_tasks = load_json(back_path) or []
    gameplay_tasks = load_json(gameplay_path) or []

    back_index = build_view_index(back_tasks, "back")
    gameplay_index = build_view_index(gameplay_tasks, "gameplay")

    combined_index: Dict[int, Dict[str, Any]] = {}
    for tm_id, data in back_index.items():
        combined_index.setdefault(tm_id, {}).update(data)
    for tm_id, data in gameplay_index.items():
        combined_index.setdefault(tm_id, {}).update(data)

    full_ok = 0
    partial = 0
    missing = 0

    for task in master_tasks:
        tm_id = task.get("id")
        title = task.get("title", "")
        if isinstance(title, str) and len(title) > 40:
            title_display = title[:40] + "..."
        else:
            title_display = title

        print(f"Task #{tm_id}: {title_display}")

        mapping: Optional[Dict[str, Any]] = combined_index.get(tm_id)
        if mapping is None:
            print("  [MISS] No back/gameplay view found for this task.")
            missing += 1
            print()
            continue

        back_info = mapping.get("back")
        gameplay_info = mapping.get("gameplay")

        if back_info:
            print(
                f"  BACK  {back_info.get('id')}: "
                f"adr_refs={status_flag(back_info['has_adr_refs'])}, "
                f"test_refs={status_flag(back_info['has_test_refs'])}, "
                f"acceptance={status_flag(back_info['has_acceptance'])}, "
                f"story_id={status_flag(back_info['has_story_id'])}"
            )
        else:
            print("  BACK  [MISS] no mapping entry")

        if gameplay_info:
            print(
                f"  GAME  {gameplay_info.get('id')}: "
                f"adr_refs={status_flag(gameplay_info['has_adr_refs'])}, "
                f"test_refs={status_flag(gameplay_info['has_test_refs'])}, "
                f"acceptance={status_flag(gameplay_info['has_acceptance'])}, "
                f"story_id={status_flag(gameplay_info['has_story_id'])}"
            )
        else:
            print("  GAME  [MISS] no mapping entry")

        views = [v for v in (back_info, gameplay_info) if v is not None]
        if not views:
            missing += 1
        else:
            view_ok = any(
                v["has_adr_refs"] and v["has_acceptance"] and v["has_story_id"]
                for v in views
            )
            if view_ok:
                print("  SUMMARY: [OK] mapping has core metadata in at least one view.")
                full_ok += 1
            else:
                print("  SUMMARY: [WARN] mapping exists but metadata is incomplete.")
                partial += 1

        print()

    print("=" * 60)
    print("Summary")
    print("=" * 60)
    total = len(master_tasks)
    print(f"Tasks with complete mapping:   {full_ok}")
    print(f"Tasks with partial metadata:   {partial}")
    print(f"Tasks without any mapping:     {missing}")
    print(f"Total master tasks inspected:  {total}")


if __name__ == "__main__":
    main()
