#!/usr/bin/env python3
"""
Build Task Master compatible .taskmaster/tasks/tasks.json from NG/GM task files.

Exports a dependency-closed task set into a Task Master tag (default: `master`) using numeric `id` / `dependencies`.

Side effects on source tasks: `taskmaster_id` (numeric), `taskmaster_exported` (bool).

Schema constraints (see docs/task-master-constraints.md): root object is { "<tag>": { "tasks": [...] }, ... }.
"""

from __future__ import annotations

import json
import argparse
from pathlib import Path
from typing import Dict, List, Set


ROOT = Path(__file__).resolve().parents[2]

TASKS_DIR = ROOT / ".taskmaster" / "tasks"
TASKMASTER_TASKS_FILE = TASKS_DIR / "tasks.json"

# Seed tasks considered as "T2 scene" roots; their dependency closure will be exported
# when no explicit --ids/--ids-file are provided.
T2_ROOT_IDS: Set[str] = {"NG-0020", "NG-0021", "GM-0101", "GM-0103"}


def load_tasks(task_file: Path) -> List[Dict]:
    if not task_file.exists():
        return []
    data = json.loads(task_file.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "tasks" in data and isinstance(data["tasks"], list):
        return data["tasks"]
    return []


def build_all_tasks(task_files: List[Path]) -> Dict[str, Dict]:
    """Load tasks from given task_files into a flat id->task mapping."""
    all_tasks: Dict[str, Dict] = {}
    for path in task_files:
        tasks = load_tasks(path)
        for t in tasks:
            tid = t.get("id")
            if not tid:
                continue
            # Later files can overwrite, but in practice ids are unique per file group.
            all_tasks[tid] = t
    return all_tasks


def get_dependencies(t: Dict) -> List[str]:
    deps = t.get("depends_on") or t.get("dependencies") or []
    return [d for d in deps if isinstance(d, str) and d]


def compute_closure(all_tasks: Dict[str, Dict], root_ids: Set[str]) -> Set[str]:
    """Compute dependency closure starting from root_ids."""
    closure: Set[str] = set()
    stack: List[str] = list(root_ids)
    while stack:
        tid = stack.pop()
        if tid in closure:
            continue
        closure.add(tid)
        t = all_tasks.get(tid)
        if not t:
            continue
        for dep in get_dependencies(t):
            if dep not in closure:
                stack.append(dep)
    return closure


def map_status(status: str | None) -> str:
    if not status:
        return "pending"
    s = status.strip().lower()
    if s in {"pending", "in-progress", "done", "deferred", "cancelled", "blocked"}:
        return s
    if s in {"in_progress", "inprogress"}:
        return "in-progress"
    if s in {"completed", "complete"}:
        return "done"
    return "pending"


def map_priority(priority: str | None) -> str:
    if not priority:
        return "medium"
    p = priority.strip().upper()
    if p in {"HIGH", "MEDIUM", "LOW"}:
        return p.lower()
    if p in {"P0", "P1"}:
        return "high"
    if p == "P2":
        return "medium"
    if p in {"P3", "P4"}:
        return "low"
    return "medium"


def build_taskmaster_tasks(args: argparse.Namespace) -> None:
    # 1) Resolve source task file list (SSoT).
    if not args.tasks_files:
        print("Error: --tasks-file is required (one or more).")
        raise SystemExit(1)

    task_files: List[Path] = []
    for p_str in args.tasks_files:
        p = Path(p_str)
        if not p.is_absolute():
            p = ROOT / p
        task_files.append(p)

    all_tasks = build_all_tasks(task_files)
    if not all_tasks:
        print("No tasks loaded from task files; aborting.")
        return

    # 2) Resolve root task ids.
    root_ids: Set[str] = set()
    if args.ids:
        root_ids.update(args.ids)
    if args.ids_file:
        ids_path = Path(args.ids_file)
        if not ids_path.is_absolute():
            ids_path = ROOT / ids_path
        try:
            id_data = json.loads(ids_path.read_text(encoding="utf-8"))
            if isinstance(id_data, list):
                for x in id_data:
                    if isinstance(x, str) and x:
                        root_ids.add(x)
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: failed to read ids-file {ids_path}: {exc}")
    if not root_ids:
        root_ids = set(T2_ROOT_IDS)

    # 3) Compute dependency closure.
    t2_ids = compute_closure(all_tasks, root_ids)
    if not t2_ids:
        print("Closure is empty; nothing to export.")
        return

    # Topologically sort T2 ids so that:
    # - Dependencies appear before dependents.
    # - Prefer NG-* (backbone) before GM-* (gameplay), when ties exist.
    visited: Dict[str, bool] = {}
    ordered: List[str] = []

    def visit(tid: str) -> None:
        if tid in visited:
            return
        visited[tid] = True
        t = all_tasks.get(tid)
        if t:
            for dep in sorted(get_dependencies(t)):
                if dep in t2_ids:
                    visit(dep)
        ordered.append(tid)

    for tid in sorted(t2_ids):
        visit(tid)

    sorted_ids = ordered
    # 4) Load existing Task Master tasks.json (if present) and prepare the target tag.
    root_obj: Dict[str, Dict]
    if TASKMASTER_TASKS_FILE.exists():
        try:
            root_obj = json.loads(TASKMASTER_TASKS_FILE.read_text(encoding="utf-8"))
            if not isinstance(root_obj, dict):
                print("Existing tasks.json is not an object; resetting.")
                root_obj = {}
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: failed to read existing tasks.json: {exc}")
            root_obj = {}
    else:
        root_obj = {}

    tag = args.tag or "master"
    tag_obj = root_obj.get(tag)
    if not isinstance(tag_obj, dict):
        tag_obj = {}
        root_obj[tag] = tag_obj
    tag_tasks = tag_obj.get("tasks")
    if not isinstance(tag_tasks, list):
        tag_tasks = []
        tag_obj["tasks"] = tag_tasks

    # Collect already used numeric ids across all tags to avoid collisions.
    used_ids: Set[int] = set()
    for v in root_obj.values():
        if not isinstance(v, dict):
            continue
        tasks_list = v.get("tasks")
        if not isinstance(tasks_list, list):
            continue
        for t in tasks_list:
            tid_val = t.get("id")
            if isinstance(tid_val, int):
                used_ids.add(tid_val)

    # 5) Allocate stable numeric ids for string ids (prefer existing `taskmaster_id`).
    id_map: Dict[str, int] = {}
    next_id = (max(used_ids) if used_ids else 0) + 1

    for tid in sorted_ids:
        src = all_tasks.get(tid)
        if not src:
            continue
        existing = src.get("taskmaster_id")
        num: int | None = None
        if isinstance(existing, int) and existing > 0:
            num = existing
            if num not in used_ids:
                used_ids.add(num)
        if num is None:
            # Allocate a new globally unique numeric id.
            while next_id in used_ids:
                next_id += 1
            num = next_id
            used_ids.add(num)
            next_id += 1
        id_map[tid] = num

    print("Tasks to export (string id -> numeric id):")
    for tid in sorted_ids:
        num = id_map.get(tid)
        print(f"  {tid} -> {num}")

    # 6) Build/update the Task Master task list under the target tag.
    existing_by_id: Dict[int, int] = {
        t["id"]: idx
        for idx, t in enumerate(tag_tasks)
        if isinstance(t, dict) and isinstance(t.get("id"), int)
    }

    for tid in sorted_ids:
        src = all_tasks.get(tid)
        if not src:
            continue
        num_id = id_map[tid]
        title = src.get("title") or tid
        description = src.get("description") or ""

        # Build details as a markdown-like blob with meta info.
        details_parts: List[str] = []
        story_id = src.get("story_id")
        if story_id:
            details_parts.append(f"Story: {story_id}")
        for key, label in (
            ("adr_refs", "ADR Refs"),
            ("chapter_refs", "Chapters"),
            ("overlay_refs", "Overlays"),
            ("test_refs", "Test Refs"),
            ("acceptance", "Acceptance"),
            ("test_strategy", "Test Strategy"),
            ("labels", "Labels"),
            ("owner", "Owner"),
            ("layer", "Layer"),
        ):
            val = src.get(key)
            if not val:
                continue
            if isinstance(val, list):
                text = "; ".join(str(v) for v in val)
            else:
                text = str(val)
            details_parts.append(f"{label}: {text}")
        details = "\n".join(details_parts) if details_parts else ""

        # Map test_strategy (list) to single string testStrategy if present.
        ts = src.get("test_strategy")
        if isinstance(ts, list):
            test_strategy_str = "\n".join(str(x) for x in ts)
        elif isinstance(ts, str):
            test_strategy_str = ts
        else:
            test_strategy_str = ""

        # Map dependencies to numeric ids (only within closure subset).
        dep_ids: List[int] = []
        for dep in get_dependencies(src):
            num_dep = id_map.get(dep)
            if num_dep is not None:
                dep_ids.append(num_dep)

        tm_task: Dict = {
            "id": num_id,
            "title": title,
            "description": description,
            "status": map_status(src.get("status")),
            "priority": map_priority(src.get("priority")),
            "dependencies": dep_ids,
        }
        if details:
            tm_task["details"] = details
        if test_strategy_str:
            tm_task["testStrategy"] = test_strategy_str

        existing_idx = existing_by_id.get(num_id)
        if existing_idx is not None:
            tag_tasks[existing_idx] = tm_task
        else:
            existing_by_id[num_id] = len(tag_tasks)
            tag_tasks.append(tm_task)

    # Assemble root object for Task Master and persist.
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    TASKMASTER_TASKS_FILE.write_text(
        json.dumps(root_obj, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote Task Master tasks file to: {TASKMASTER_TASKS_FILE}")

    # 7) Update bookkeeping fields in source task files.
    def mark_exported(file_path: Path) -> None:
        if not file_path.exists():
            return
        data = json.loads(file_path.read_text(encoding="utf-8"))
        is_list = isinstance(data, list)
        tasks = data if is_list else data.get("tasks", [])
        for t in tasks:
            tid = t.get("id")
            if not tid:
                continue
            if tid in id_map:
                t["taskmaster_id"] = id_map[tid]
                t["taskmaster_exported"] = True
            else:
                # Only write False when missing to avoid overriding a previous True.
                if "taskmaster_exported" not in t:
                    t["taskmaster_exported"] = False
        if is_list:
            new_data = tasks
        else:
            new_data = data
            new_data["tasks"] = tasks
        file_path.write_text(
            json.dumps(new_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Updated source task file: {file_path}")

    # Only update source files participating in this run.
    for src_file in task_files:
        mark_exported(src_file)

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build or update Task Master-compatible tasks.json from NG/GM tasks, "
            "optionally for a specific tag and task id set."
        )
    )
    parser.add_argument(
        "--tag",
        default="master",
        help="Task Master tag name to update (default: master).",
    )
    parser.add_argument(
        "--tasks-file",
        dest="tasks_files",
        action="append",
        help="Source tasks json file (e.g. .taskmaster/tasks/tasks_back.json). "
             "Can be given multiple times; defaults to tasks_back/gameplay/longterm.",
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        help="Task ids (e.g. NG-0020 GM-0101) to export (closure of dependencies will be included).",
    )
    parser.add_argument(
        "--ids-file",
        help="JSON file containing an array of task ids (strings) to export.",
    )
    args = parser.parse_args()
    build_taskmaster_tasks(args)


if __name__ == "__main__":
    main()
