#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update tasks_back.json / tasks_gameplay.json "test_refs" for a single task.

This script is intentionally conservative:
  - It never guesses across arbitrary test files.
  - It only auto-adds task-scoped test files under Game.Core.Tests/Tasks/ matching:
      Game.Core.Tests/Tasks/Task<id>*Tests.cs
  - You can add extra refs explicitly via --add.

Why:
  - tasks.json has no test_refs field by design.
  - tasks_back.json / tasks_gameplay.json are the intended place to keep per-task test file evidence.
  - Keeping test_refs in sync prevents "tests exist but traceability metadata is empty".
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def ensure_list_field(obj: dict[str, Any], key: str) -> list[str]:
    v = obj.get(key)
    if v is None:
        obj[key] = []
        return obj[key]
    if isinstance(v, list):
        # Normalize to strings.
        obj[key] = [str(x) for x in v if str(x).strip()]
        return obj[key]
    raise ValueError(f"{key} must be a list")


def find_view_task(view: list[dict[str, Any]], task_id: str) -> dict[str, Any] | None:
    tid = int(str(task_id))
    for t in view:
        if not isinstance(t, dict):
            continue
        if t.get("taskmaster_id") == tid:
            return t
    return None


def to_posix_rel(root: Path, p: Path) -> str:
    return str(p.relative_to(root)).replace("\\", "/")


def auto_task_tests(root: Path, task_id: str) -> list[str]:
    tasks_dir = root / "Game.Core.Tests" / "Tasks"
    if not tasks_dir.exists():
        return []
    pattern = f"Task{task_id}*Tests.cs"
    return [to_posix_rel(root, p) for p in sorted(tasks_dir.glob(pattern))]


def add_unique(dst: list[str], items: list[str]) -> bool:
    before = list(dst)
    seen = set(dst)
    for it in items:
        it = str(it).strip()
        if not it:
            continue
        if it in seen:
            continue
        dst.append(it)
        seen.add(it)
    return dst != before


def main() -> int:
    ap = argparse.ArgumentParser(description="Update tasks_back/tasks_gameplay test_refs for one task.")
    ap.add_argument("--task-id", required=True, help="Task id (e.g. 11).")
    ap.add_argument("--add", action="append", default=[], help="Add a repo-relative test file path (repeatable).")
    ap.add_argument("--auto", action="store_true", help="Auto-add Game.Core.Tests/Tasks/Task<id>*Tests.cs if present.")
    ap.add_argument("--write", action="store_true", help="Write files in-place. Without this flag, runs as dry-run.")
    args = ap.parse_args()

    root = repo_root()
    back_path = root / ".taskmaster" / "tasks" / "tasks_back.json"
    gameplay_path = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"

    back = load_json(back_path)
    gameplay = load_json(gameplay_path)
    if not isinstance(back, list) or not isinstance(gameplay, list):
        raise ValueError("tasks_back.json and tasks_gameplay.json must be JSON arrays")

    task_id = str(args.task_id).strip()
    back_task = find_view_task(back, task_id)
    gameplay_task = find_view_task(gameplay, task_id)
    if back_task is None or gameplay_task is None:
        raise ValueError(f"taskmaster_id not found in both views: {task_id}")

    add_items: list[str] = []
    if args.auto:
        add_items.extend(auto_task_tests(root, task_id))
    add_items.extend([str(x).strip() for x in (args.add or []) if str(x).strip()])

    back_refs = ensure_list_field(back_task, "test_refs")
    game_refs = ensure_list_field(gameplay_task, "test_refs")

    changed_back = add_unique(back_refs, add_items)
    changed_game = add_unique(game_refs, add_items)

    print(f"UPDATE_TASK_TEST_REFS task_id={task_id} add={len(add_items)} changed_back={changed_back} changed_game={changed_game} write={bool(args.write)}")
    if not args.write:
        return 0

    write_json(back_path, back)
    write_json(gameplay_path, gameplay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
