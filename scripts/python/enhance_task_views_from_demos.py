#!/usr/bin/env python3
"""
Enhance tasks_back.json and tasks_gameplay.json with demo-based
acceptance/test_strategy hints derived from taskup.md's three learning
modules and the Godot demo how-to guide.

All reading and writing is done via Python; JSON schemas and ids are
preserved:
  - No field names are changed.
  - taskmaster_id stays numeric; id stays SG-xxxx / GM-xxxx.

Usage (from project root):
  py -3 scripts/python/enhance_task_views_from_demos.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACK_PATH = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_back.json"
GAMEPLAY_PATH = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_gameplay.json"


# Learning modules as described in taskup.md
MODULE1_IDS = {2, 3, 10, 23}  # Board/cities/ring-route + token move + city UI
MODULE2_IDS = {6, 17, 21}  # Turn loop + game loop + date UI
MODULE3_IDS = {7, 8, 12, 13, 14, 15, 16, 19, 24}  # Economy + environment events + related UI

# Legacy markers (Chinese) used by older task-view generations. Kept via \u escapes for idempotency.
LEGACY_MARKER_MODULE1 = "\u5b66\u4e60\u6a21\u5757\u4e00"
LEGACY_MARKER_MODULE2 = "\u5b66\u4e60\u6a21\u5757\u4e8c"
LEGACY_MARKER_MODULE3 = "\u5b66\u4e60\u6a21\u5757\u4e09"


def _append_unique(lines: List[str], text: str, markers: List[str]) -> List[str]:
    if any(any(m in line for m in markers) for line in lines):
        return lines
    return lines + [text]


def enhance_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    tid = int(entry.get("taskmaster_id", 0))
    acceptance: List[str] = list(entry.get("acceptance") or [])
    test_strategy: List[str] = list(entry.get("test_strategy") or [])

    if tid in MODULE1_IDS:
        # Learning module 1: board/cities/ring route.
        acceptance = _append_unique(
            acceptance,
            "[LEARNING_MODULE_1] Study Godot demos `2d/hexagonal_map` and `2d/dynamic_tilemap_layers` for board/scene/data structure patterns (reuse patterns, not code).",
            ["[LEARNING_MODULE_1]", LEGACY_MARKER_MODULE1],
        )
        test_strategy = _append_unique(
            test_strategy,
            "[LEARNING_MODULE_1] Before implementation, run and inspect the TileMap demos; design unit/scene tests that validate ring-route movement and city state updates.",
            ["[LEARNING_MODULE_1]", LEGACY_MARKER_MODULE1],
        )

    if tid in MODULE2_IDS:
        # Learning module 2: turn loop + time axis.
        acceptance = _append_unique(
            acceptance,
            "[LEARNING_MODULE_2] Turn advancement and date/month/year ticks are traceable and aligned with the T2 PRD day -> month-end -> season -> year loop.",
            ["[LEARNING_MODULE_2]", LEGACY_MARKER_MODULE2],
        )
        test_strategy = _append_unique(
            test_strategy,
            "[LEARNING_MODULE_2] Study game-loop demos (e.g., `dodge_the_creeps`, `pong`); write xUnit tests simulating multiple turns and verifying trigger points match the PRD.",
            ["[LEARNING_MODULE_2]", LEGACY_MARKER_MODULE2],
        )

    if tid in MODULE3_IDS:
        # Learning module 3: property/toll/economy/events.
        acceptance = _append_unique(
            acceptance,
            "[LEARNING_MODULE_3] Economy (yield/toll/seasonal events/yearly price adjustment) is settled in Game.Core with clear, traceable UI feedback.",
            ["[LEARNING_MODULE_3]", LEGACY_MARKER_MODULE3],
        )
        test_strategy = _append_unique(
            test_strategy,
            "[LEARNING_MODULE_3] Before implementing economy/events, review module-3 notes in taskup.md and relevant demos; write combined tests for month-end, seasonal events, and yearly price adjustment, including log assertions.",
            ["[LEARNING_MODULE_3]", LEGACY_MARKER_MODULE3],
        )

    entry["acceptance"] = acceptance
    entry["test_strategy"] = test_strategy
    return entry


def enhance_list(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [enhance_entry(e) for e in entries]


def main() -> int:
    print(f"[enhance-views] Project root: {PROJECT_ROOT}")

    if not BACK_PATH.exists() or not GAMEPLAY_PATH.exists():
        raise SystemExit("tasks_back.json or tasks_gameplay.json not found; run gen_sanguo_tasks_views.py first.")

    back_entries = json.loads(BACK_PATH.read_text(encoding="utf-8"))
    gameplay_entries = json.loads(GAMEPLAY_PATH.read_text(encoding="utf-8"))

    back_entries = enhance_list(back_entries)
    gameplay_entries = enhance_list(gameplay_entries)

    BACK_PATH.write_text(json.dumps(back_entries, ensure_ascii=False, indent=2), encoding="utf-8")
    GAMEPLAY_PATH.write_text(json.dumps(gameplay_entries, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"[enhance-views] Updated acceptance/test_strategy for "
        f"{len(back_entries)} back tasks and {len(gameplay_entries)} gameplay tasks (where applicable)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
