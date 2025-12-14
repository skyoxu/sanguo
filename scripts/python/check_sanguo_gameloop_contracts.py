#!/usr/bin/env python
"""
Minimal checks for Sanguo core game loop contracts.

This script validates that the core Sanguo game turn domain events
are present in Game.Core/Contracts/Sanguo/GameEvents.cs and have
expected EventType constants and namespace.

Contracts checked (all in one file):
- Game.Core/Contracts/Sanguo/GameEvents.cs
  - SanguoGameTurnStarted     -> core.sanguo.game.turn.started
  - SanguoGameTurnEnded       -> core.sanguo.game.turn.ended
  - SanguoGameTurnAdvanced    -> core.sanguo.game.turn.advanced

Exit code:
- 0 when all checks pass.
- 1 when any check fails.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = PROJECT_ROOT / "Game.Core" / "Contracts" / "Sanguo" / "GameEvents.cs"


def main() -> int:
    result: Dict[str, Any] = {
        "ok": False,
        "file": str(CONTRACT_PATH),
        "checks": []  # type: List[Dict[str, Any]]
    }

    if not CONTRACT_PATH.exists():
        result["checks"].append(
            {
                "name": "GameEventsFile",
                "exists": False,
                "namespace_ok": False,
                "events": [],
            }
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    text = CONTRACT_PATH.read_text(encoding="utf-8")

    namespace_ok = "namespace Game.Core.Contracts.Sanguo;" in text

    specs = [
        {
            "record_name": "SanguoGameTurnStarted",
            "event_type": "core.sanguo.game.turn.started",
        },
        {
            "record_name": "SanguoGameTurnEnded",
            "event_type": "core.sanguo.game.turn.ended",
        },
        {
            "record_name": "SanguoGameTurnAdvanced",
            "event_type": "core.sanguo.game.turn.advanced",
        },
    ]

    events_results: List[Dict[str, Any]] = []
    all_ok = namespace_ok

    for spec in specs:
        record_name = spec["record_name"]
        event_type = spec["event_type"]

        record_ok = f"public sealed record {record_name}" in text
        event_type_literal = f'public const string EventType = "{event_type}";'
        event_type_ok = event_type_literal in text

        events_results.append(
            {
                "record_name": record_name,
                "event_type": event_type,
                "record_ok": record_ok,
                "event_type_ok": event_type_ok,
            }
        )

        all_ok = all_ok and record_ok and event_type_ok

    result["checks"].append(
        {
            "name": "SanguoGameLoopContracts",
            "exists": True,
            "namespace_ok": namespace_ok,
            "events": events_results,
        }
    )
    result["ok"] = bool(all_ok)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
