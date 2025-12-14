#!/usr/bin/env python3
"""
Append machine-local reference paths to selected Task Master tasks.

This script updates `.taskmaster/tasks/tasks.json` by appending a single line to `testStrategy`
for a subset of T2 tasks, pointing to local demo repositories (Windows-only).

It then regenerates `.taskmaster/tasks/tasks_back.json` and `.taskmaster/tasks/tasks_gameplay.json`
via `gen_sanguo_tasks_views`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASKS_PATH = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks.json"

# Machine-local demo repo roots (absolute paths; intended for local-only workflows).
DEMO_ROOT = Path(r"C:\buildgame\godotdemo\demo\godot-demo-projects")
DAFUWENG_ROOT = Path(r"C:\buildgame\godotdemo\dafuweng")
HOWTOUSE_MD = DEMO_ROOT / "howtouse.md"


def load_tasks() -> Dict[str, Any]:
    data = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    if "master" not in data or "tasks" not in data["master"]:
        raise SystemExit("tasks.json is missing 'master.tasks' section.")
    return data


def _append_paths_to_test_strategy(task: Dict[str, Any], paths: List[Path]) -> None:
    """Append a single 'Local reference paths: ...' line to testStrategy if missing."""
    if not paths:
        return
    ts = str(task.get("testStrategy", ""))
    path_str = "; ".join(str(p) for p in paths)
    if path_str in ts:
        return
    line = f"\nLocal reference paths: {path_str}"
    task["testStrategy"] = ts + line


def update_task_fields(tasks: Dict[int, Dict[str, Any]]) -> None:
    """Append demo reference paths to a subset of tasks (no overwrites)."""

    task_refs: Dict[int, List[Path]] = {
        2: [
            DEMO_ROOT / "2d" / "hexagonal_map",
            DEMO_ROOT / "2d" / "dynamic_tilemap_layers",
            DAFUWENG_ROOT / "monopoly_clone",
        ],
        4: [
            DEMO_ROOT / "2d" / "platformer",
            DEMO_ROOT / "2d" / "kinematic_character",
            DAFUWENG_ROOT / "casus-belli",
        ],
        6: [
            DAFUWENG_ROOT / "Prototype",
            DAFUWENG_ROOT / "casus-belli",
            DEMO_ROOT / "2d" / "pong",
        ],
        7: [
            DAFUWENG_ROOT / "monopoly_clone",
            DAFUWENG_ROOT / "Prototype",
        ],
        9: [
            DEMO_ROOT / "gui" / "control_gallery",
            DEMO_ROOT / "gui" / "accessibility",
        ],
        11: [
            DEMO_ROOT / "2d" / "finite_state_machine",
            DAFUWENG_ROOT / "Prototype",
        ],
        30: [HOWTOUSE_MD],
    }

    for tid, refs in task_refs.items():
        task = tasks.get(tid)
        if not task:
            continue
        _append_paths_to_test_strategy(task, refs)


def write_tasks(data: Dict[str, Any]) -> None:
    TASKS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def regenerate_views() -> None:
    try:
        from gen_sanguo_tasks_views import main as gen_sanguo_tasks_views_main
    except Exception as exc:  # pragma: no cover
        print(f"[enhance-tasks] Warning: unable to import gen_sanguo_tasks_views: {exc}")
        return
    gen_sanguo_tasks_views_main()


def main() -> int:
    print(f"[enhance-tasks] Project root: {PROJECT_ROOT}")
    if not TASKS_PATH.exists():
        raise SystemExit(f"tasks.json not found at {TASKS_PATH}")

    data = load_tasks()
    master_tasks = data["master"]["tasks"]
    by_id = {int(t["id"]): t for t in master_tasks}

    update_task_fields(by_id)

    # Keep the original order; update content only.
    write_tasks(data)
    print("[enhance-tasks] Updated tasks.json details/testStrategy for demo-related tasks.")

    regenerate_views()
    print("[enhance-tasks] Regenerated tasks_back.json and tasks_gameplay.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
