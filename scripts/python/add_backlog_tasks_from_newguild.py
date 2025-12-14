#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add selected backlog-style tasks (inspired by newguild's tasks_back.json)
into this repo's .taskmaster/tasks/tasks_back.json.

Why:
- newguild keeps a set of migration/backlog tasks (Phase 13-22) in tasks_back.json
  even when they are not exported to tasks.json.
- sanguo currently focuses tasks.json on T2 gameplay. We mirror useful backlog tasks
  into tasks_back.json so Taskmaster/SuperClaude can reference them as needed.

Notes:
- This script does NOT rename existing SG-* tasks.
- Backlog tasks added here do NOT get taskmaster_id / taskmaster_exported.
- We hardcode absolute reference paths to the local newguild repo for convenience
  (this is intentionally machine-local only, per user request).

Usage (Windows, from repo root):
  py -3 scripts/python/add_backlog_tasks_from_newguild.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SANGUO_TASKS_BACK = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_back.json"
NEWGUILD_TASKS_BACK = Path(r"C:\buildgame\newguild\.taskmaster\tasks\tasks_back.json")


SOURCE_TASK_IDS: List[str] = [
    "NG-0012",
    "NG-0013",
    "NG-0014",
    "NG-0015",
    "NG-0016",
    "NG-0017",
    "NG-0018",
    "NG-0019",
    "NG-0023",
    "NG-0024",
    "NG-0027",
    "NG-0028",
    "NG-0029",
    "NG-0030",
    "NG-0031",
    "NG-0032",
    "NG-0033",
    "NG-0038",
]


REF_DOCS: Dict[str, List[str]] = {
    "NG-0012": [
        "Phase-12-Headless-Smoke-Backlog.md",
        "Phase-12-Headless-Smoke-Tests.md",
    ],
    "NG-0013": [
        "Phase-13-Quality-Gates-Backlog.md",
        "Phase-13-Quality-Gates-Script.md",
    ],
    "NG-0014": [
        "Phase-14-Godot-Security-Backlog.md",
        "Phase-14-Godot-Security-Baseline.md",
    ],
    "NG-0015": [
        "Phase-15-Performance-Budgets-and-Gates.md",
        "Phase-15-Performance-Budgets-Backlog.md",
    ],
    "NG-0016": [
        "Phase-16-Observability-Sentry-Integration.md",
        "Phase-16-Observability-Backlog.md",
    ],
    "NG-0017": [
        "Phase-17-Build-System-and-Godot-Export.md",
        "Phase-17-Build-Backlog.md",
        "Phase-17-Export-Checklist.md",
    ],
    "NG-0018": [
        "Phase-18-Staged-Release-and-Canary-Strategy.md",
        "Phase-18-Staged-Release-Backlog.md",
        "Phase-19-Emergency-Rollback-and-Monitoring.md",
        "Phase-19-Emergency-Rollback-Backlog.md",
    ],
    "NG-0019": [
        "Phase-20-Functional-Acceptance-Testing.md",
        "Phase-20-Functional-Acceptance-Backlog.md",
        "Phase-21-Performance-Optimization.md",
        "Phase-21-Performance-Optimization-Backlog.md",
        "Phase-22-Documentation-and-Release-Notes.md",
        "Phase-22-Documentation-Backlog.md",
    ],
    "NG-0023": [
        "Phase-9-Signal-Backlog.md",
        "Phase-9-Signal-System.md",
    ],
    "NG-0024": [
        "Phase-16-Observability-Backlog.md",
    ],
    "NG-0027": [
        "Phase-13-Quality-Gates-Backlog.md",
        "Phase-13-Quality-Gates-Script.md",
    ],
    "NG-0028": [
        "Phase-13-Quality-Gates-Backlog.md",
        "Phase-15-Performance-Budgets-and-Gates.md",
    ],
    "NG-0029": [
        "Phase-14-Godot-Security-Backlog.md",
        "Phase-14-Godot-Security-Baseline.md",
    ],
    "NG-0030": [
        "Phase-15-Performance-Budgets-Backlog.md",
    ],
    "NG-0031": [
        "Phase-15-Performance-Budgets-Backlog.md",
    ],
    "NG-0032": [
        "Phase-17-Build-Backlog.md",
    ],
    "NG-0033": [
        "Phase-17-Build-Backlog.md",
        "Phase-17-Export-Checklist.md",
    ],
    "NG-0038": [
        "Phase-7-UI-Migration.md",
        "Phase-5-Adapter-Layer.md",
        "Phase-4-Domain-Layer.md",
    ],
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def next_sg_id(existing_ids: Set[str], start: int = 31) -> str:
    used = set()
    for tid in existing_ids:
        m = re.match(r"SG-(\d{4})$", str(tid))
        if m:
            used.add(int(m.group(1)))
    n = start
    while n in used:
        n += 1
    return f"SG-{n:04d}"


def normalize_text(value: str) -> str:
    # Make newguild-derived text less confusing in sanguo.
    out = value.replace("newguild", "sanguo")
    out = out.replace("NewGuild", "Sanguo")
    return out


def add_reference_lines(task: Dict[str, Any], source_id: str) -> None:
    files = REF_DOCS.get(source_id, [])
    if not files:
        return

    internal = [f"docs/migration/{name}" for name in files if (PROJECT_ROOT / "docs" / "migration" / name).exists()]
    external = [fr"C:\buildgame\newguild\docs\migration\{name}" for name in files]

    line = "Internal references (this repo): " + " ; ".join(internal) if internal else ""
    line2 = "External references (newguild repo): " + " ; ".join(external) if external else ""

    acceptance = task.get("acceptance") or []
    if isinstance(acceptance, list):
        if line:
            acceptance.append(line)
        if line2:
            acceptance.append(line2)
        task["acceptance"] = acceptance


def main() -> int:
    if not SANGUO_TASKS_BACK.exists():
        raise SystemExit(f"Missing: {SANGUO_TASKS_BACK}")
    if not NEWGUILD_TASKS_BACK.exists():
        raise SystemExit(f"Missing: {NEWGUILD_TASKS_BACK}")

    sanguo_tasks: List[Dict[str, Any]] = load_json(SANGUO_TASKS_BACK)
    newguild_tasks: List[Dict[str, Any]] = load_json(NEWGUILD_TASKS_BACK)
    by_id: Dict[str, Dict[str, Any]] = {str(t.get("id")): t for t in newguild_tasks if t.get("id")}

    existing_ids: Set[str] = {str(t.get("id")) for t in sanguo_tasks if t.get("id")}

    added = 0
    for src_id in SOURCE_TASK_IDS:
        src = by_id.get(src_id)
        if not src:
            continue

        # Skip if we already added this backlog item before (by story_id + title heuristic).
        title = normalize_text(str(src.get("title", ""))).strip()
        story_id = str(src.get("story_id", "")).strip()
        already = any(
            (t.get("story_id") == story_id and str(t.get("title", "")).strip() == title)
            for t in sanguo_tasks
        )
        if already:
            continue

        new_id = next_sg_id(existing_ids)
        existing_ids.add(new_id)

        new_task: Dict[str, Any] = {}
        for k in [
            "story_id",
            "title",
            "description",
            "status",
            "priority",
            "layer",
            "depends_on",
            "adr_refs",
            "chapter_refs",
            "overlay_refs",
            "labels",
            "owner",
            "test_refs",
            "acceptance",
            "test_strategy",
        ]:
            if k in src:
                new_task[k] = src.get(k)

        new_task["id"] = new_id

        # Normalize text fields
        if isinstance(new_task.get("title"), str):
            new_task["title"] = normalize_text(new_task["title"])
        if isinstance(new_task.get("description"), str):
            new_task["description"] = normalize_text(new_task["description"])
        if isinstance(new_task.get("acceptance"), list):
            new_task["acceptance"] = [normalize_text(str(x)) for x in new_task["acceptance"]]
        if isinstance(new_task.get("test_strategy"), list):
            new_task["test_strategy"] = [normalize_text(str(x)) for x in new_task["test_strategy"]]

        # These backlog tasks are not exported from tasks.json by default.
        new_task["taskmaster_exported"] = False

        # Mirror fields used by other scripts (keep in sync)
        new_task["adrRefs"] = list(new_task.get("adr_refs") or [])
        new_task["archRefs"] = list(new_task.get("chapter_refs") or [])

        # Overlay is optional; for generic backlog tasks keep it empty.
        new_task["overlay"] = ""

        # Avoid carrying guild-specific overlay refs into sanguo backlog tasks.
        if src_id == "NG-0023":
            new_task["overlay_refs"] = [
                "docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md",
            ]
            new_task["overlay"] = "docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md"

        # For machine-local reference, append absolute doc paths.
        add_reference_lines(new_task, src_id)

        # Backlog tasks in sanguo should not depend on newguild NG-xxxx ids.
        new_task["depends_on"] = []

        sanguo_tasks.append(new_task)
        added += 1

    # Stable order: SG-0001.. then SG-00xx backlog tasks.
    def sort_key(t: Dict[str, Any]) -> tuple[int, str]:
        tid = str(t.get("id", ""))
        m = re.match(r"SG-(\d{4})$", tid)
        if m:
            return (int(m.group(1)), tid)
        return (9999, tid)

    sanguo_tasks_sorted = sorted(sanguo_tasks, key=sort_key)
    write_json(SANGUO_TASKS_BACK, sanguo_tasks_sorted)
    print(f"Added backlog tasks: {added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
