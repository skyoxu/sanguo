#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hard-code absolute paths to local demo repositories into:
  - .taskmaster/tasks/tasks.json
  - .taskmaster/tasks/tasks_back.json
  - .taskmaster/tasks/tasks_gameplay.json

This is intended for local Taskmaster + superclaude usage only, where the
agent can open files directly by absolute Windows paths.

Constraints:
  - Field names and overall JSON schema are not changed.
  - Task ids remain natural numbers in tasks.json and SG-/GM- ids in views.

Usage (from project root, Windows):
  py -3 scripts/python/hardcode_demo_paths_in_tasks.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASKS_MAIN = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks.json"
TASKS_BACK = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_back.json"
TASKS_GAMEPLAY = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_gameplay.json"

# Local demo roots (absolute paths, for this machine only).
DEMO_ROOT = r"C:\buildgame\godotdemo\demo\godot-demo-projects"
DAFUWENG_ROOT = r"C:\buildgame\godotdemo\dafuweng"
HOWTOUSE_MD = DEMO_ROOT + r"\howtouse.md"


def _paths_for_task_id(tid: int) -> List[str]:
    """
    Decide which external demo paths are most relevant for a given task id.
    This uses the three learning modules from taskup.md as the main spine.
    """
    paths: List[str] = []

    # Module 1: board / city / ring route.
    module1_ids = {2, 3, 10, 23}
    # Module 2: turn loop + calendar.
    module2_ids = {6, 17, 21}
    # Module 3: economy / environment events.
    module3_ids = {7, 8, 12, 13, 14, 15, 16, 19, 24}

    if tid in module1_ids:
        paths.extend(
            [
                DEMO_ROOT + r"\2d\hexagonal_map",
                DEMO_ROOT + r"\2d\dynamic_tilemap_layers",
                DAFUWENG_ROOT + r"\monopoly_clone",
            ]
        )

    if tid in module2_ids:
        paths.extend(
            [
                DAFUWENG_ROOT + r"\Prototype",
                DAFUWENG_ROOT + r"\casus-belli",
                DEMO_ROOT + r"\2d\pong",
            ]
        )

    if tid in module3_ids:
        paths.extend(
            [
                DAFUWENG_ROOT + r"\monopoly_clone",
                DAFUWENG_ROOT + r"\Prototype",
            ]
        )

    # AI-related tasks.
    if tid in {11, 25}:
        paths.extend(
            [
                DEMO_ROOT + r"\2d\finite_state_machine",
                DAFUWENG_ROOT + r"\Prototype",
            ]
        )

    # UI-related tasks.
    if tid in {9, 19, 20, 21, 22, 23, 24}:
        paths.extend(
            [
                DEMO_ROOT + r"\gui\control_gallery",
                DEMO_ROOT + r"\gui\accessibility",
            ]
        )

    # Help / tutorial.
    if tid == 30:
        paths.append(HOWTOUSE_MD)

    # Bootstrap / architecture might benefit from casus-belli layout.
    if tid == 1:
        paths.append(DAFUWENG_ROOT + r"\casus-belli")

    # Deduplicate while preserving order.
    seen = set()
    unique_paths: List[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique_paths.append(p)
    return unique_paths


def _append_line_once(text: str, marker: str, line: str) -> str:
    if marker in text:
        return text
    return text + line


def update_tasks_main() -> None:
    """
    Append demo path hints to testStrategy of selected tasks in tasks.json.
    """
    data = json.loads(TASKS_MAIN.read_text(encoding="utf-8"))
    tasks = data.get("master", {}).get("tasks", [])

    for t in tasks:
        try:
            tid = int(t.get("id"))
        except (TypeError, ValueError):
            continue
        paths = _paths_for_task_id(tid)
        if not paths:
            continue

        ts = str(t.get("testStrategy", ""))
        marker = "Local demo paths:"
        line = "\nLocal demo paths: " + " ; ".join(paths)
        t["testStrategy"] = _append_line_once(ts, marker, line)

    TASKS_MAIN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def update_view_list(path: Path) -> None:
    """
    Append demo path hints into acceptance/test_strategy arrays for
    tasks_back.json or tasks_gameplay.json.
    """
    entries = json.loads(path.read_text(encoding="utf-8"))
    for e in entries:
        try:
            tid = int(e.get("taskmaster_id", 0))
        except (TypeError, ValueError):
            continue

        paths = _paths_for_task_id(tid)
        if not paths:
            continue

        paths_str = " ; ".join(paths)
        acc = list(e.get("acceptance") or [])
        ts = list(e.get("test_strategy") or [])

        acc_line = "Local demo references: " + paths_str
        ts_line = "Local demo paths for implementation/tests: " + paths_str

        if not any("Local demo references:" in a for a in acc):
            acc.append(acc_line)
        if not any("Local demo paths for implementation/tests:" in t for t in ts):
            ts.append(ts_line)

        e["acceptance"] = acc
        e["test_strategy"] = ts

    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    print(f"[hardcode-demo-paths] Project root: {PROJECT_ROOT}")
    if not TASKS_MAIN.exists():
        raise SystemExit(f"tasks.json not found at {TASKS_MAIN}")
    if not TASKS_BACK.exists() or not TASKS_GAMEPLAY.exists():
        raise SystemExit("tasks_back.json or tasks_gameplay.json not found; run gen_sanguo_tasks_views.py first.")

    update_tasks_main()
    update_view_list(TASKS_BACK)
    update_view_list(TASKS_GAMEPLAY)

    print("[hardcode-demo-paths] Updated tasks.json, tasks_back.json, tasks_gameplay.json with local demo paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

