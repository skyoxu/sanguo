#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export backlog (non-exported) SG-* tasks from tasks_back.json into Taskmaster
tasks.json (master.tasks) using the existing tasks.json schema in this repo.

Why:
- Taskmaster MCP primarily reads .taskmaster/tasks/tasks.json.
- tasks_back.json contains richer acceptance/test strategy context, but MCP may
  not consume its custom schema.
- By exporting backlog items into tasks.json with "deferred" status, we keep
  them visible to MCP without forcing them into the main T2 execution queue.

This script:
- Finds SG-* tasks in tasks_back.json with taskmaster_exported != true.
- Assigns numeric ids based on SG-XXXX -> int(XXXX) (must not collide).
- Appends/updates corresponding entries in tasks.json master.tasks.
- Adds taskmaster_id + taskmaster_exported=true to the source SG tasks.

Usage (Windows, from repo root):
  py -3 scripts/python/export_backlog_to_tasks_json.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = ROOT / ".taskmaster" / "tasks"
TASKS_JSON = TASKS_DIR / "tasks.json"
TASKS_BACK = TASKS_DIR / "tasks_back.json"
TASKS_GAMEPLAY = TASKS_DIR / "tasks_gameplay.json"

OVERLAY_INDEX_DEFAULT = "docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_sg_numeric_id(task_id: str) -> int | None:
    m = re.fullmatch(r"SG-(\d{4})", task_id)
    if not m:
        return None
    return int(m.group(1))


def priority_to_taskmaster(value: str | None) -> str:
    if not value:
        return "medium"
    p = value.strip().upper()
    if p in {"HIGH", "MEDIUM", "LOW"}:
        return p.lower()
    if p in {"P0", "P1"}:
        return "high"
    if p == "P2":
        return "medium"
    if p in {"P3", "P4"}:
        return "low"
    return "medium"


def build_string_id_to_numeric_map(back: List[Dict[str, Any]], gameplay: List[Dict[str, Any]]) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for t in back + gameplay:
        tid = t.get("id")
        tm_id = t.get("taskmaster_id")
        if isinstance(tid, str) and isinstance(tm_id, int) and tm_id > 0:
            mapping[tid] = tm_id
    return mapping


def build_taskmaster_task_from_backlog(
    src: Dict[str, Any],
    numeric_id: int,
    id_map: Dict[str, int],
) -> Dict[str, Any]:
    # Keep the exact key set used by existing tasks.json entries.
    title = str(src.get("title") or f"Backlog {numeric_id}")
    description = str(src.get("description") or "")

    # Prefer using tasks_back's rich fields to help MCP.
    details_lines: List[str] = []
    if description:
        details_lines.append(description)

    story_id = src.get("story_id")
    if story_id:
        details_lines.append(f"Story: {story_id}")

    acceptance = src.get("acceptance") or []
    if isinstance(acceptance, list) and acceptance:
        details_lines.append("Acceptance:")
        details_lines.extend(f"- {x}" for x in acceptance)

    test_strategy_list = src.get("test_strategy") or []
    test_strategy_str = ""
    if isinstance(test_strategy_list, list) and test_strategy_list:
        test_strategy_str = "\n".join(str(x) for x in test_strategy_list)
    elif isinstance(test_strategy_list, str) and test_strategy_list.strip():
        test_strategy_str = test_strategy_list.strip()

    # Map depends_on (string ids) to dependencies (numeric ids) where possible.
    deps: List[int] = []
    for dep in src.get("depends_on") or []:
        if not isinstance(dep, str):
            continue
        num = id_map.get(dep)
        if isinstance(num, int):
            deps.append(num)

    adr_refs = src.get("adr_refs") or []
    chapter_refs = src.get("chapter_refs") or []

    overlay = OVERLAY_INDEX_DEFAULT
    # If the task already has an overlay ref, use the first one as the default link.
    overlay_refs = src.get("overlay_refs") or []
    if isinstance(overlay_refs, list) and overlay_refs:
        overlay = str(overlay_refs[0])

    # Backlog tasks should not disrupt the main queue.
    status = "deferred"

    return {
        "id": numeric_id,
        "title": title,
        "description": description,
        "details": "\n".join(details_lines).strip(),
        "testStrategy": test_strategy_str,
        "priority": priority_to_taskmaster(src.get("priority")),
        "dependencies": deps,
        "status": status,
        "subtasks": [],
        "adrRefs": list(adr_refs) if isinstance(adr_refs, list) else [],
        "archRefs": list(chapter_refs) if isinstance(chapter_refs, list) else [],
        "overlay": overlay,
    }


def main() -> int:
    tasks_data = load_json(TASKS_JSON)
    back = load_json(TASKS_BACK)
    gameplay = load_json(TASKS_GAMEPLAY)

    master_tasks: List[Dict[str, Any]] = tasks_data.get("master", {}).get("tasks", [])
    if not isinstance(master_tasks, list) or not master_tasks:
        raise SystemExit("tasks.json: master.tasks missing or empty")

    # Enforce existing schema key set for safety.
    expected_keys = set(master_tasks[0].keys())
    for t in master_tasks:
        if set(t.keys()) != expected_keys:
            raise SystemExit("tasks.json: master.tasks schema is inconsistent; aborting")

    existing_ids = {t.get("id") for t in master_tasks if isinstance(t, dict)}
    if not all(isinstance(x, int) and x > 0 for x in existing_ids if x is not None):
        raise SystemExit("tasks.json: found non-integer id in master.tasks; aborting")

    id_map = build_string_id_to_numeric_map(back, gameplay)

    backlog_src: List[Tuple[str, Dict[str, Any], int]] = []
    for t in back:
        tid = t.get("id")
        if not isinstance(tid, str):
            continue
        if t.get("taskmaster_exported"):
            continue
        numeric_id = parse_sg_numeric_id(tid)
        if numeric_id is None:
            continue
        backlog_src.append((tid, t, numeric_id))

    backlog_src.sort(key=lambda x: x[2])
    if not backlog_src:
        print("No backlog SG-* tasks to export.")
        return 0

    added = 0
    updated = 0

    # Index existing master tasks by id for updates.
    master_by_id: Dict[int, int] = {t["id"]: idx for idx, t in enumerate(master_tasks) if isinstance(t.get("id"), int)}

    for tid, src, numeric_id in backlog_src:
        if numeric_id in existing_ids:
            # Update in place to keep mapping stable.
            tm_task = build_taskmaster_task_from_backlog(src, numeric_id, id_map)
            tm_task["id"] = numeric_id
            tm_task["subtasks"] = []
            tm_task["dependencies"] = tm_task.get("dependencies") or []
            tm_task["status"] = "deferred"
            idx = master_by_id.get(numeric_id)
            if idx is not None:
                master_tasks[idx] = tm_task
                updated += 1
            # else: should not happen
        else:
            tm_task = build_taskmaster_task_from_backlog(src, numeric_id, id_map)
            master_tasks.append(tm_task)
            existing_ids.add(numeric_id)
            master_by_id[numeric_id] = len(master_tasks) - 1
            added += 1

        # Mark exported in tasks_back.json for mapping.
        src["taskmaster_id"] = numeric_id
        src["taskmaster_exported"] = True
        # Keep status aligned (optional but makes intent clear).
        src["status"] = "deferred"
        id_map[tid] = numeric_id

    tasks_data["master"]["tasks"] = master_tasks

    write_json(TASKS_JSON, tasks_data)
    write_json(TASKS_BACK, back)

    print(f"Exported backlog tasks to tasks.json: added={added}, updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

