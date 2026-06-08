#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add ADR/architecture reference metadata fields to Taskmaster task JSON files:
  - .taskmaster/tasks/tasks.json       (adrRefs, archRefs, overlay)
  - .taskmaster/tasks/tasks_back.json  (adr_refs, chapter_refs, overlay_refs)
  - .taskmaster/tasks/tasks_gameplay.json (adr_refs, chapter_refs, overlay_refs)

The goal is to satisfy AGENTS/CLAUDE 2.2 requirements and make Python
validation scripts (validate_task_links.py, etc.) pass, while preserving
existing schemas and ids.

Usage (from project root, Windows):
  py -3 scripts/python/add_task_ref_fields.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASKS_MAIN = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks.json"
TASKS_BACK = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_back.json"
TASKS_GAMEPLAY = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_gameplay.json"


def load_layer_meta_and_config():
    """
    Import layer metadata and task config from gen_sanguo_tasks_views.
    """
    from gen_sanguo_tasks_views import LAYER_META, TASK_CONFIG  # type: ignore

    return LAYER_META, TASK_CONFIG


def load_view_overlay_refs() -> Dict[int, List[str]]:
    refs_by_task_id: Dict[int, List[str]] = {}
    for path in (TASKS_BACK, TASKS_GAMEPLAY):
        if not path.exists():
            continue
        entries: List[Dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
        for entry in entries:
            taskmaster_id = entry.get("taskmaster_id")
            if not isinstance(taskmaster_id, int):
                continue
            refs = entry.get("overlay_refs")
            if not isinstance(refs, list):
                continue
            normalized = [str(ref).strip() for ref in refs if str(ref).strip()]
            if normalized and taskmaster_id not in refs_by_task_id:
                refs_by_task_id[taskmaster_id] = normalized
    return refs_by_task_id


def update_tasks_main() -> None:
    """
    Ensure every task in tasks.json has adrRefs/archRefs/overlay fields.
    ADR/CH are derived from layer metadata (infra/core/ui).
    Overlay is optional and left as None for now.
    """
    layer_meta, task_config = load_layer_meta_and_config()
    overlay_refs_by_task_id = load_view_overlay_refs()

    data = json.loads(TASKS_MAIN.read_text(encoding="utf-8"))
    master = data.get("master", {})
    tasks = master.get("tasks", [])

    for t in tasks:
        try:
            tid = int(t.get("id"))
        except (TypeError, ValueError):
            continue
        cfg = task_config.get(tid)
        layer = cfg.layer if cfg is not None else "core"
        meta = layer_meta.get(layer, {})
        adr_refs = list(meta.get("adr_refs", []))
        ch_refs = list(meta.get("chapter_refs", []))

        # Add camelCase fields expected by validation scripts.
        if not t.get("adrRefs"):
            t["adrRefs"] = adr_refs
        if not t.get("archRefs"):
            t["archRefs"] = ch_refs
        if not t.get("overlay"):
            overlay_refs = overlay_refs_by_task_id.get(tid, [])
            t["overlay"] = overlay_refs[0] if overlay_refs else None

    TASKS_MAIN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def update_view_file(path: Path) -> None:
    """
    Ensure the view task file keeps the snake_case reference fields.

    Note:
      - View files are the SSoT for: adr_refs/chapter_refs/overlay_refs.
      - We intentionally DO NOT add the legacy duplicate fields:
            adrRefs/archRefs/overlay
        because they cause drift and confusion (different scripts reading
        different keys).
    """
    entries: List[Dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))

    for e in entries:
        # Keep existing keys; do not mutate schema beyond ensuring lists exist.
        # Any missing values are left to the generator/workflow to populate.
        if "adr_refs" not in e:
            e["adr_refs"] = []
        if "chapter_refs" not in e:
            e["chapter_refs"] = []
        if "overlay_refs" not in e:
            e["overlay_refs"] = []

    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    print(f"[add-task-ref-fields] Project root: {PROJECT_ROOT}")
    if not TASKS_MAIN.exists():
        raise SystemExit(f"tasks.json not found at {TASKS_MAIN}")
    if not TASKS_BACK.exists() or not TASKS_GAMEPLAY.exists():
        raise SystemExit("tasks_back.json or tasks_gameplay.json not found; run gen_sanguo_tasks_views.py first.")

    update_tasks_main()
    update_view_file(TASKS_BACK)
    update_view_file(TASKS_GAMEPLAY)

    print("[add-task-ref-fields] Ensured tasks.json has adrRefs/archRefs/overlay; views use adr_refs/chapter_refs/overlay_refs only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
