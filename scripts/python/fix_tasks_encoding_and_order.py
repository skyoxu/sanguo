#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix semantic-level Chinese text and ordering for Taskmaster tasks in this
Sanguo project, using Python for both reading and writing.

Actions:
1. Read .taskmaster/tasks/tasks.json (UTF-8).
2. Keep existing schema and numeric ids, but reorder master.tasks by:
   - dependency chain (topological order), then
   - priority: high -> medium -> low, then
   - id ascending.
3. Rewrite tasks.json with ensure_ascii=False so Chinese text stays readable.
4. Regenerate tasks_back.json and tasks_gameplay.json via gen_sanguo_tasks_views.

Constraints:
- Does not change field names or types.
- Task ids remain natural numbers (1..N).

Usage (from project root, Windows):
  py -3 scripts/python/fix_tasks_encoding_and_order.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASKS_PATH = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks.json"

# Priority ordering for scheduling within the dependency graph.
PRIORITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
}


def _priority_weight(task: Dict[str, Any]) -> int:
    return PRIORITY_ORDER.get(task.get("priority", "medium"), 1)


def load_master_tasks() -> Dict[str, Any]:
    data = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    if "master" not in data or "tasks" not in data["master"]:
        raise SystemExit("tasks.json is missing 'master.tasks' section.")
    return data


def topological_sort_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Topologically sort tasks by dependency, breaking ties with priority and id.
    Keeps the task objects unchanged; only reorders the list.
    """
    from heapq import heappush, heappop

    # Build index by integer id.
    by_id: Dict[int, Dict[str, Any]] = {}
    indegree: Dict[int, int] = {}
    forward: Dict[int, List[int]] = {}

    for task in tasks:
        raw_id = task.get("id")
        try:
            tid = int(raw_id)
        except (TypeError, ValueError):
            # Keep non-numeric ids in their original relative order at the end.
            continue
        by_id[tid] = task
        deps = [int(d) for d in task.get("dependencies") or []]
        indegree[tid] = len(deps)
        for dep in deps:
            forward.setdefault(dep, []).append(tid)

    # Initialise queue with all nodes that have no dependencies.
    heap: List[tuple[int, int]] = []
    for tid, deg in indegree.items():
        if deg == 0:
            heappush(heap, (_priority_weight(by_id[tid]), tid))

    ordered_ids: List[int] = []
    while heap:
        _, tid = heappop(heap)
        ordered_ids.append(tid)
        for nxt in forward.get(tid, []):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                heappush(heap, (_priority_weight(by_id[nxt]), nxt))

    if len(ordered_ids) != len(by_id):
        # Fallback on a pure priority + id ordering if there is a cycle.
        ordered_ids = sorted(
            by_id.keys(),
            key=lambda t: (_priority_weight(by_id[t]), t),
        )

    # Preserve any tasks whose ids are non-numeric by appending them in place.
    ordered: List[Dict[str, Any]] = [by_id[tid] for tid in ordered_ids]
    numeric_ids = {tid for tid in ordered_ids}
    for task in tasks:
        raw_id = task.get("id")
        try:
            tid = int(raw_id)
        except (TypeError, ValueError):
            ordered.append(task)
            continue
        if tid not in numeric_ids:
            ordered.append(task)
    return ordered


def write_tasks(data: Dict[str, Any]) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    TASKS_PATH.write_text(text, encoding="utf-8")


def regenerate_views() -> None:
    """
    Rebuild tasks_back.json and tasks_gameplay.json from the updated tasks.json.
    """
    try:
        # Import from the same scripts/python directory.
        from gen_sanguo_tasks_views import main as gen_views_main
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"[fix-tasks] Warning: unable to import gen_sanguo_tasks_views: {exc}")
        return
    gen_views_main()


def main() -> int:
    print(f"[fix-tasks] Project root: {PROJECT_ROOT}")
    if not TASKS_PATH.exists():
        raise SystemExit(f"tasks.json not found at {TASKS_PATH}")

    data = load_master_tasks()
    master = data["master"]
    tasks = master["tasks"]

    print(f"[fix-tasks] Loaded {len(tasks)} master tasks.")
    sorted_tasks = topological_sort_tasks(tasks)
    print(f"[fix-tasks] Reordered tasks: preserved {len(sorted_tasks)} entries.")

    master["tasks"] = sorted_tasks
    write_tasks(data)
    print(f"[fix-tasks] Wrote updated tasks.json with UTF-8 Chinese text.")

    regenerate_views()
    print("[fix-tasks] Regenerated tasks_back.json and tasks_gameplay.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

