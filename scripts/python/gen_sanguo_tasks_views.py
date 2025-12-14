#!/usr/bin/env python3
"""
Generate Taskmaster auxiliary views for the Sanguo template based on the
existing .taskmaster/tasks/tasks.json plus the T2 PRD and task notes.

This script produces:
  - .taskmaster/tasks/tasks_back.json
  - .taskmaster/tasks/tasks_gameplay.json

Design notes (ADR alignment):
  - ADR-0005-quality-gates: tasks include acceptance and test strategy hints.
  - ADR-0018-godot-csharp-tech-stack: core/gameplay tasks assume Godot + C#.
  - ADR-0025-godot-test-strategy: xUnit + GdUnit4 testing expectations.
  - ADR-0021-csharp-domain-layer-architecture: core logic kept in Game.Core.
  - ADR-0024-sanguo-template-lineage: tasks target the Sanguo T2 vertical slice.

Usage (from project root, Windows):
  py -3 scripts/python/gen_sanguo_tasks_views.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASKS_JSON_PATH = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks.json"
PRD_PATH = PROJECT_ROOT / ".taskmaster" / "docs" / "prd.txt"
TASKUP_PATH = PROJECT_ROOT / "taskup.md"

BACK_PATH = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_back.json"
GAMEPLAY_PATH = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_gameplay.json"


@dataclass(frozen=True)
class TaskConfig:
    story_id: str
    layer: str
    labels: List[str]
    include_in_gameplay: bool = False


# Per-layer static metadata reused by all tasks in that layer.
LAYER_META: Dict[str, Dict[str, Any]] = {
    "infra": {
        "priority": "P1",
        "adr_refs": ["ADR-0001", "ADR-0005", "ADR-0011", "ADR-0018"],
        "chapter_refs": ["CH01", "CH07"],
        "owner": "architecture",
        "acceptance": [
            "Taskmaster configuration and helper scripts run on Windows without breaking the existing CI flow.",
            "Generated task views map 1:1 to task ids in `.taskmaster/tasks/tasks.json`.",
        ],
        "test_strategy": [
            "Validate task-view generation via Python unit tests or a minimal smoke script.",
            "Run Taskmaster MCP locally to read the new views and confirm parsing succeeds.",
        ],
    },
    "core": {
        "priority": "P1",
        "adr_refs": ["ADR-0018", "ADR-0021", "ADR-0025", "ADR-0005", "ADR-0015", "ADR-0024"],
        "chapter_refs": ["CH01", "CH04", "CH05", "CH06", "CH09"],
        "owner": "gameplay",
        "acceptance": [
            "Core gameplay types/methods live in `Game.Core` and do not depend on Godot APIs.",
            "xUnit tests exist and pass for the task (see `test_refs` placeholders).",
        ],
        "test_strategy": [
            "Write xUnit + FluentAssertions unit tests covering key state machines and calculations.",
            "Use coverlet to ensure core logic meets ADR-0005 coverage gates.",
        ],
    },
    "ui": {
        "priority": "P2",
        "adr_refs": ["ADR-0018", "ADR-0022", "ADR-0005"],
        "chapter_refs": ["CH01", "CH06", "CH10"],
        "owner": "gameplay",
        "acceptance": [
            "Godot scenes and UI controls load successfully in headless smoke tests.",
            "Key UI interactions are covered by GdUnit4 tests in `Tests.Godot`.",
        ],
        "test_strategy": [
            "Use GdUnit4 to write scene-level tests for main UI flows; cover at least the T2 vertical slice.",
            "Run UI smoke in `smoke_headless` to ensure no main-loop stall or crash.",
        ],
    },
}


# Task-level config: keep minimal metadata for the Sanguo T2 vertical slice.
TASK_CONFIG: Dict[int, TaskConfig] = {
    1: TaskConfig("PRD-SANGUO-T2-BOOTSTRAP", "infra", ["bootstrap", "godot", "csharp"], True),
    2: TaskConfig("PRD-SANGUO-T2-BOARD", "core", ["board", "map", "city"], True),
    3: TaskConfig("PRD-SANGUO-T2-CITY", "core", ["city", "economy"], True),
    4: TaskConfig("PRD-SANGUO-T2-PLAYER", "core", ["player", "economy"], True),
    5: TaskConfig("PRD-SANGUO-T2-DICE", "core", ["dice", "random"], True),
    6: TaskConfig("PRD-SANGUO-T2-TURN-MANAGER", "core", ["turn", "calendar"], True),
    7: TaskConfig("PRD-SANGUO-T2-ECONOMY", "core", ["economy", "settlement"], True),
    8: TaskConfig("PRD-SANGUO-T2-ENV-EVENTS", "core", ["events", "environment"], True),
    9: TaskConfig("PRD-SANGUO-T2-UI-SKELETON", "ui", ["ui", "hud"], True),
    10: TaskConfig("PRD-SANGUO-T2-TOKEN-MOVE", "core", ["movement", "board"], True),
    11: TaskConfig("PRD-SANGUO-T2-AI-CORE", "core", ["ai", "agent"], True),
    12: TaskConfig("PRD-SANGUO-T2-BUY-LAND", "core", ["economy", "buy"], True),
    13: TaskConfig("PRD-SANGUO-T2-TOLL", "core", ["economy", "toll"], True),
    14: TaskConfig("PRD-SANGUO-T2-MONTH-END", "core", ["economy", "month-end"], True),
    15: TaskConfig("PRD-SANGUO-T2-SEASON-EVENTS", "core", ["events", "season"], True),
    16: TaskConfig("PRD-SANGUO-T2-YEAR-PRICE", "core", ["economy", "price"], True),
    17: TaskConfig("PRD-SANGUO-T2-GAME-LOOP", "core", ["loop", "calendar"], True),
    18: TaskConfig("PRD-SANGUO-T2-SAVELOAD", "core", ["save", "persistence"], True),
    19: TaskConfig("PRD-SANGUO-T2-UI-EVENT-TIPS", "ui", ["ui", "notifications"], True),
    20: TaskConfig("PRD-SANGUO-T2-UI-MONEY", "ui", ["ui", "money"], True),
    21: TaskConfig("PRD-SANGUO-T2-UI-DATE", "ui", ["ui", "calendar"], True),
    22: TaskConfig("PRD-SANGUO-T2-UI-DICE", "ui", ["ui", "dice"], True),
    23: TaskConfig("PRD-SANGUO-T2-UI-CITY-STATE", "ui", ["ui", "city"], True),
    24: TaskConfig("PRD-SANGUO-T2-UI-LOG", "ui", ["ui", "log"], True),
    25: TaskConfig("PRD-SANGUO-T2-AI-OPT", "core", ["ai", "tuning"]),
    26: TaskConfig("PRD-SANGUO-T2-GAME-END", "core", ["loop", "end"]),
    27: TaskConfig("PRD-SANGUO-T2-AUDIO", "ui", ["audio", "ux"]),
    28: TaskConfig("PRD-SANGUO-T2-MENU-MAIN", "ui", ["ui", "menu"]),
    29: TaskConfig("PRD-SANGUO-T2-MENU-SETTINGS", "ui", ["ui", "settings"]),
    30: TaskConfig("PRD-SANGUO-T2-HELP", "ui", ["ui", "help"]),
}


def load_master_tasks() -> Dict[int, Dict[str, Any]]:
    raw = json.loads(TASKS_JSON_PATH.read_text(encoding="utf-8"))
    master = raw.get("master", {}).get("tasks", [])
    by_id: Dict[int, Dict[str, Any]] = {}
    for task in master:
        raw_id = task.get("id")
        try:
            tid = int(raw_id)
        except (TypeError, ValueError):
            continue
        by_id[tid] = task
    return by_id


def read_prd_and_notes() -> None:
    # Read PRD and task notes only for traceability in local logs.
    if PRD_PATH.exists():
        prd_text = PRD_PATH.read_text(encoding="utf-8", errors="ignore")
        first_line = prd_text.splitlines()[0].strip() if prd_text else ""
    else:
        first_line = ""

    if TASKUP_PATH.exists():
        taskup_text = TASKUP_PATH.read_text(encoding="utf-8", errors="ignore")
        taskup_hint = "T2" if "T2" in taskup_text else ""
    else:
        taskup_hint = ""

    print(f"[gen-tasks] PRD first line: {first_line}")
    if taskup_hint:
        print("[gen-tasks] taskup.md contains T2 guidance.")


def build_back_tasks(master_tasks: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    back_tasks: List[Dict[str, Any]] = []
    for tid, cfg in sorted(TASK_CONFIG.items()):
        task = master_tasks.get(tid)
        if not task:
            # Some tasks may not be exported to master yet.
            continue

        layer_meta = LAYER_META[cfg.layer]
        depends_ids = task.get("dependencies", []) or []
        depends_back = [f"SG-{int(dep):04d}" for dep in depends_ids if int(dep) in TASK_CONFIG]

        back_tasks.append(
            {
                "id": f"SG-{tid:04d}",
                "story_id": cfg.story_id,
                "title": task.get("title", ""),
                "description": task.get("description", ""),
                "status": "pending",
                "priority": layer_meta["priority"],
                "layer": cfg.layer,
                "depends_on": depends_back,
                "adr_refs": layer_meta["adr_refs"],
                "chapter_refs": layer_meta["chapter_refs"],
                "overlay_refs": [],
                "labels": cfg.labels,
                "owner": layer_meta["owner"],
                "test_refs": [],
                "acceptance": layer_meta["acceptance"],
                "test_strategy": layer_meta["test_strategy"],
                "taskmaster_id": tid,
                "taskmaster_exported": True,
            }
        )
    return back_tasks


def build_gameplay_tasks(master_tasks: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    gameplay_tasks: List[Dict[str, Any]] = []
    for tid, cfg in sorted(TASK_CONFIG.items()):
        if not cfg.include_in_gameplay:
            continue
        task = master_tasks.get(tid)
        if not task:
            continue

        layer_meta = LAYER_META[cfg.layer]
        depends_ids = task.get("dependencies", []) or []
        # Keep dependencies only if the dependency itself is included in gameplay.
        depends_gm = [
            f"GM-{int(dep):04d}"
            for dep in depends_ids
            if int(dep) in TASK_CONFIG and TASK_CONFIG[int(dep)].include_in_gameplay
        ]

        gameplay_tasks.append(
            {
                "id": f"GM-{tid:04d}",
                "story_id": cfg.story_id,
                "title": task.get("title", ""),
                "description": task.get("description", ""),
                "status": "pending",
                "priority": layer_meta["priority"],
                "layer": cfg.layer,
                "depends_on": depends_gm,
                "adr_refs": layer_meta["adr_refs"],
                "chapter_refs": layer_meta["chapter_refs"],
                "overlay_refs": [],
                "labels": cfg.labels + ["t2-gameplay"],
                "owner": layer_meta["owner"],
                "test_refs": [],
                "acceptance": layer_meta["acceptance"],
                "test_strategy": layer_meta["test_strategy"],
                "taskmaster_id": tid,
                "taskmaster_exported": True,
            }
        )
    return gameplay_tasks


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    print(f"[gen-tasks] Project root: {PROJECT_ROOT}")
    read_prd_and_notes()

    master_tasks = load_master_tasks()
    missing = [tid for tid in TASK_CONFIG if tid not in master_tasks]
    if missing:
        print(f"[gen-tasks] WARNING: master tasks missing ids: {missing}")

    back_tasks = build_back_tasks(master_tasks)
    gameplay_tasks = build_gameplay_tasks(master_tasks)

    write_json(BACK_PATH, back_tasks)
    write_json(GAMEPLAY_PATH, gameplay_tasks)

    ts = datetime.now().isoformat()
    print(
        f"[gen-tasks] {ts} wrote "
        f"{len(back_tasks)} back tasks -> {BACK_PATH}, "
        f"{len(gameplay_tasks)} gameplay tasks -> {GAMEPLAY_PATH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
