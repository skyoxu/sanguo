#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add ADR/architecture reference metadata fields to Taskmaster task JSON files:
  - .taskmaster/tasks/tasks.json       (adrRefs, archRefs, overlay)
  - .taskmaster/tasks/tasks_back.json  (adrRefs, archRefs, overlay)
  - .taskmaster/tasks/tasks_gameplay.json (adrRefs, archRefs, overlay)

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


def update_tasks_main() -> None:
    """
    Ensure every task in tasks.json has adrRefs/archRefs/overlay fields.
    ADR/CH are derived from layer metadata (infra/core/ui).
    Overlay is optional and left as None for now.
    """
    layer_meta, task_config = load_layer_meta_and_config()

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
        # Overlay is optional; we just ensure the field exists.
        if "overlay" not in t:
            t["overlay"] = None

    TASKS_MAIN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def update_view_file(path: Path) -> None:
    """
    Mirror ADR/CH metadata into camelCase fields for back/gameplay views.
    Existing snake_case fields (adr_refs, chapter_refs, overlay_refs)
    are preserved; we only add adrRefs/archRefs/overlay for scripts that
    expect these names.
    """
    entries: List[Dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))

    for e in entries:
        # Derive from existing snake_case fields if present.
        adr_refs = e.get("adr_refs") or []
        ch_refs = e.get("chapter_refs") or []
        overlay_refs = e.get("overlay_refs") or []

        if not e.get("adrRefs"):
            e["adrRefs"] = list(adr_refs)
        if not e.get("archRefs"):
            e["archRefs"] = list(ch_refs)

        if "overlay" not in e:
            overlay = None
            if overlay_refs:
                # Use the first overlay reference as primary overlay hint.
                overlay = overlay_refs[0]
            e["overlay"] = overlay

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

    print("[add-task-ref-fields] Added adrRefs/archRefs/overlay to tasks.json, tasks_back.json, tasks_gameplay.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

