#!/usr/bin/env python3
"""
Create overlay documentation for the T2 vertical slice (Sanguo Monopoly loop)
and wire it into Taskmaster task JSON files.

This script:
  1. Creates docs/architecture/overlays/PRD-SANGUO-T2/08/ directory.
  2. Writes:
       - _index.md
  3. Updates:
       - .taskmaster/tasks/tasks.json      (overlay field)
       - .taskmaster/tasks/tasks_back.json (overlay / overlay_refs)
       - .taskmaster/tasks/tasks_gameplay.json (overlay / overlay_refs)

All reading and writing is done via Python; existing schemas and ids are
preserved.

Usage (from project root, Windows):
  py -3 scripts/python/create_t2_overlay.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OVERLAY_ROOT = PROJECT_ROOT / "docs" / "architecture" / "overlays" / "PRD-SANGUO-T2" / "08"
INDEX_MD = OVERLAY_ROOT / "_index.md"

TASKS_MAIN = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks.json"
TASKS_BACK = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_back.json"
TASKS_GAMEPLAY = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_gameplay.json"


OVERLAY_PATH_STR = "docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md"


def ensure_overlay_dir() -> None:
    OVERLAY_ROOT.mkdir(parents=True, exist_ok=True)
    if not INDEX_MD.exists():
        raise SystemExit(
            f"Missing overlay index file: {INDEX_MD}. "
            "Restore overlay docs from the repository history instead of generating new content here."
        )


def update_tasks_main() -> None:
    if not TASKS_MAIN.exists():
        return
    data = json.loads(TASKS_MAIN.read_text(encoding="utf-8"))
    master = data.get("master", {})
    tasks: List[Dict[str, Any]] = master.get("tasks", [])
    for t in tasks:
        # Only set overlay if it is missing or null.
        if "overlay" not in t or t["overlay"] in (None, ""):
            t["overlay"] = OVERLAY_PATH_STR
    TASKS_MAIN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def update_view(path: Path) -> None:
    if not path.exists():
        return
    entries: List[Dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    for e in entries:
        # overlay_refs is an array; ensure the new overlay path is present.
        overlay_refs = list(e.get("overlay_refs") or [])
        if OVERLAY_PATH_STR not in overlay_refs:
            overlay_refs.append(OVERLAY_PATH_STR)
        e["overlay_refs"] = overlay_refs
        # Also set overlay camelCase field.
        e["overlay"] = OVERLAY_PATH_STR
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    print(f"[create-t2-overlay] Project root: {PROJECT_ROOT}")
    ensure_overlay_dir()
    update_tasks_main()
    update_view(TASKS_BACK)
    update_view(TASKS_GAMEPLAY)
    print(f"[create-t2-overlay] Overlay docs written under {OVERLAY_ROOT}")
    print("[create-t2-overlay] Updated overlay links in tasks.json, tasks_back.json, tasks_gameplay.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
