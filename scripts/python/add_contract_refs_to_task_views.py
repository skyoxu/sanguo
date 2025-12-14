#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add contractRefs (domain event references) to Taskmaster view files:
  - .taskmaster/tasks/tasks_back.json
  - .taskmaster/tasks/tasks_gameplay.json

Notes:
- tasks.json is left untouched to avoid changing its schema.
- contractRefs is a simple list of event type strings, following the
  naming convention used in T2 overlay:
    core.sanguo.<entity>.<action>

Usage (from project root, Windows):
  py -3 scripts/python/add_contract_refs_to_task_views.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASKS_BACK = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_back.json"
TASKS_GAMEPLAY = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_gameplay.json"


def contract_refs_for_task(task_id: int) -> List[str]:
    """
    Map Taskmaster task id to a list of domain event types.
    This follows the T2 overlay and previous contract suggestions.
    """
    events: Dict[int, List[str]] = {
        # Board / movement
        2: ["core.sanguo.board.token.moved"],
        10: ["core.sanguo.board.token.moved"],
        # City / economy
        7: ["core.sanguo.economy.month.settled"],
        8: ["core.sanguo.economy.season.event.applied"],
        12: ["core.sanguo.city.bought"],
        13: ["core.sanguo.city.toll.paid"],
        14: ["core.sanguo.economy.month.settled"],
        15: ["core.sanguo.economy.season.event.applied"],
        16: ["core.sanguo.economy.year.price.adjusted"],
        # Game loop / save / end
        6: ["core.sanguo.game.turn.started", "core.sanguo.game.turn.ended"],
        17: ["core.sanguo.game.turn.advanced"],
        18: ["core.sanguo.game.saved", "core.sanguo.game.loaded"],
        26: ["core.sanguo.game.ended"],
        # Dice / AI
        5: ["core.sanguo.dice.rolled"],
        11: ["core.sanguo.ai.decision.made"],
        25: ["core.sanguo.ai.decision.made"],
        # UI tasks subscribe to existing events; we list the main ones.
        19: [
            "core.sanguo.board.token.moved",
            "core.sanguo.city.bought",
            "core.sanguo.city.toll.paid",
            "core.sanguo.economy.month.settled",
            "core.sanguo.economy.season.event.applied",
            "core.sanguo.game.ended",
        ],
        20: ["core.sanguo.player.state.changed"],
        21: ["core.sanguo.game.turn.advanced"],
        22: ["core.sanguo.dice.rolled"],
        23: [
            "core.sanguo.city.bought",
            "core.sanguo.city.toll.paid",
            "core.sanguo.economy.season.event.applied",
        ],
        24: [
            "core.sanguo.board.token.moved",
            "core.sanguo.city.bought",
            "core.sanguo.city.toll.paid",
            "core.sanguo.economy.month.settled",
            "core.sanguo.economy.season.event.applied",
            "core.sanguo.economy.year.price.adjusted",
            "core.sanguo.game.ended",
        ],
        # Help / tutorial
        30: [
            "core.sanguo.dice.rolled",
            "core.sanguo.board.token.moved",
            "core.sanguo.city.bought",
            "core.sanguo.city.toll.paid",
            "core.sanguo.economy.month.settled",
            "core.sanguo.economy.season.event.applied",
            "core.sanguo.economy.year.price.adjusted",
            "core.sanguo.game.turn.advanced",
            "core.sanguo.game.ended",
        ],
    }
    return events.get(task_id, [])


def update_view_file(path: Path) -> None:
    entries: List[Dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    for e in entries:
        try:
            tid = int(e.get("taskmaster_id", 0))
        except (TypeError, ValueError):
            continue
        refs = contract_refs_for_task(tid)
        if not refs:
            # Leave as-is if we have no explicit mapping.
            continue
        # Only set contractRefs if not already present.
        if "contractRefs" not in e or not e["contractRefs"]:
            e["contractRefs"] = refs
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    print(f"[add-contract-refs] Project root: {PROJECT_ROOT}")
    if not TASKS_BACK.exists() or not TASKS_GAMEPLAY.exists():
        raise SystemExit("tasks_back.json or tasks_gameplay.json not found; run gen_sanguo_tasks_views.py first.")

    update_view_file(TASKS_BACK)
    update_view_file(TASKS_GAMEPLAY)

    print("[add-contract-refs] Updated tasks_back.json and tasks_gameplay.json with contractRefs where applicable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

