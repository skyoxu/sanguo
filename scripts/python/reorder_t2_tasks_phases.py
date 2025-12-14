#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reorder T2 master tasks (1-30) into two phases:
- Phase 1: minimal playable loop (per PRD T2 closed loop)
- Phase 2: non-blocking extensions/polish

This script updates:
- .taskmaster/tasks/tasks.json (Taskmaster/MCP view)
- .taskmaster/tasks/tasks_back.json (context view)
- .taskmaster/tasks/tasks_gameplay.json (context view)

Constraints:
- Keep existing field schema (no field rename/type change).
- Keep numeric ids in tasks.json unchanged.
- Only reorder task list order; optionally mark Phase 2 statuses as "deferred".

Usage (Windows, from repo root):
  py -3 scripts/python/reorder_t2_tasks_phases.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[2]
TASKS_JSON = ROOT / ".taskmaster" / "tasks" / "tasks.json"
TASKS_BACK = ROOT / ".taskmaster" / "tasks" / "tasks_back.json"
TASKS_GAMEPLAY = ROOT / ".taskmaster" / "tasks" / "tasks_gameplay.json"


# Phase 1: minimal playable closed loop for PRD T2
# Core loop: dice -> move -> buy/pay -> month-end -> quarter event -> year adjustment -> repeat
# Plus essential UI for playability (money/dice/date/city status/event prompt)
PHASE1_ORDER: List[int] = [
    1,  # setup
    2, 3, 4,  # map/city/player core entities
    5,  # dice
    6, 7, 8,  # turn manager, economy, event manager
    9,  # UI skeleton
    22,  # UI dice result
    10,  # movement
    12,  # land purchase
    23,  # UI city status
    13,  # toll payment
    11,  # AI behavior
    14,  # month-end income
    20,  # UI money
    15,  # quarter events
    19,  # UI event prompt
    16,  # yearly land price adjustment
    17,  # turn loop
    21,  # UI date
]

# Phase 2: extensions/polish (safe to defer until Phase 1 playability is validated)
PHASE2_ORDER: List[int] = [
    18,  # save
    24,  # UI event log
    25,  # AI strategy optimization
    26,  # game end conditions (PRD says not required for T2)
    27,  # audio/music
    28, 29, 30,  # main menu, settings, help/tutorial
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_master_schema_consistent(master_tasks: List[Dict[str, Any]]) -> List[str]:
    if not master_tasks:
        raise SystemExit("tasks.json: master.tasks is empty")
    expected = list(master_tasks[0].keys())
    for t in master_tasks:
        if list(t.keys()) != expected:
            raise SystemExit("tasks.json: master.tasks schema is not consistent across tasks")
    return expected


def _validate_phase_partition() -> None:
    all_ids = set(PHASE1_ORDER) | set(PHASE2_ORDER)
    if len(PHASE1_ORDER) != len(set(PHASE1_ORDER)):
        raise SystemExit("Phase 1 order contains duplicate ids")
    if len(PHASE2_ORDER) != len(set(PHASE2_ORDER)):
        raise SystemExit("Phase 2 order contains duplicate ids")
    if set(PHASE1_ORDER) & set(PHASE2_ORDER):
        raise SystemExit("Phase orders overlap")
    expected = set(range(1, 31))
    if all_ids != expected:
        missing = sorted(expected - all_ids)
        extra = sorted(all_ids - expected)
        raise SystemExit(f"Phase partition mismatch. missing={missing}, extra={extra}")


def _validate_dependency_order(tasks_by_id: Dict[int, Dict[str, Any]], ordered_ids: List[int]) -> None:
    pos = {tid: idx for idx, tid in enumerate(ordered_ids)}
    for tid in ordered_ids:
        task = tasks_by_id[tid]
        deps = task.get("dependencies") or []
        for dep in deps:
            if not isinstance(dep, int):
                continue
            if dep not in pos:
                # dependency outside 1..30 or missing from phase plan; ignore here
                continue
            if pos[dep] > pos[tid]:
                raise SystemExit(f"Invalid order: task {tid} depends on {dep} but appears earlier")


def _maybe_defer_status(task: Dict[str, Any]) -> None:
    # Only defer if it's still pending, to avoid clobbering real progress.
    if task.get("status") == "pending":
        task["status"] = "deferred"


def reorder_tasks_json() -> List[int]:
    data = load_json(TASKS_JSON)
    master = data.get("master", {})
    tasks = master.get("tasks", [])
    if not isinstance(tasks, list):
        raise SystemExit("tasks.json: master.tasks is not a list")

    _ensure_master_schema_consistent(tasks)
    _validate_phase_partition()

    # Split tasks into (1..30) and the rest (31+ backlog).
    t2_tasks = [t for t in tasks if isinstance(t, dict) and isinstance(t.get("id"), int) and 1 <= t["id"] <= 30]
    rest_tasks = [t for t in tasks if not (isinstance(t, dict) and isinstance(t.get("id"), int) and 1 <= t["id"] <= 30)]

    if len(t2_tasks) != 30:
        found = sorted(t.get("id") for t in t2_tasks)
        raise SystemExit(f"tasks.json: expected 30 tasks with id 1..30, found {len(t2_tasks)}: {found}")

    by_id = {t["id"]: t for t in t2_tasks}
    phase_order = PHASE1_ORDER + PHASE2_ORDER
    _validate_dependency_order(by_id, phase_order)

    # Apply status deferral for Phase 2.
    for tid in PHASE2_ORDER:
        _maybe_defer_status(by_id[tid])

    # Rebuild master.tasks list with the new order, then keep backlog/others as-is.
    master["tasks"] = [by_id[tid] for tid in phase_order] + rest_tasks
    data["master"] = master

    write_json(TASKS_JSON, data)
    return phase_order


def reorder_view_file(path: Path, desired_numeric_order: List[int]) -> None:
    tasks = load_json(path)
    if not isinstance(tasks, list):
        raise SystemExit(f"{path}: expected a JSON list")

    mapped: List[Dict[str, Any]] = [t for t in tasks if isinstance(t, dict) and isinstance(t.get("taskmaster_id"), int)]
    unmapped: List[Dict[str, Any]] = [t for t in tasks if not (isinstance(t, dict) and isinstance(t.get("taskmaster_id"), int))]

    by_tm: Dict[int, Dict[str, Any]] = {t["taskmaster_id"]: t for t in mapped}

    ordered: List[Dict[str, Any]] = []
    for tm_id in desired_numeric_order:
        t = by_tm.get(tm_id)
        if t is None:
            continue
        # Mirror Phase 2 status deferral into views if applicable.
        if tm_id in PHASE2_ORDER:
            _maybe_defer_status(t)
        ordered.append(t)

    # Append any remaining mapped tasks not in desired order (e.g. future tags) in stable numeric order.
    remaining = [t for tm, t in sorted(by_tm.items()) if tm not in set(desired_numeric_order)]
    ordered.extend(remaining)

    # Keep unmapped tasks at the end in their original order.
    ordered.extend(unmapped)

    write_json(path, ordered)


def main() -> int:
    phase_order = reorder_tasks_json()

    # Reorder views to match tasks.json ordering (including backlog ids 31+ if present).
    # Build full numeric order from tasks.json after rewrite.
    tasks_data = load_json(TASKS_JSON)
    master_tasks = tasks_data.get("master", {}).get("tasks", [])
    full_numeric_order = [
        t["id"] for t in master_tasks if isinstance(t, dict) and isinstance(t.get("id"), int)
    ]

    reorder_view_file(TASKS_BACK, full_numeric_order)
    reorder_view_file(TASKS_GAMEPLAY, full_numeric_order)

    print(f"Reordered tasks.json phases: phase1={len(PHASE1_ORDER)}, phase2={len(PHASE2_ORDER)}")
    print(f"tasks.json master.tasks numeric count: {len(full_numeric_order)}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

