#!/usr/bin/env python
"""Minimal checks for core guild contracts.

This script validates that the three core guild domain events
are present and have expected EventType constants and namespace.

Contracts checked:
- Game.Core/Contracts/Guild/GuildCreated.cs
- Game.Core/Contracts/Guild/GuildMemberJoined.cs
- Game.Core/Contracts/Guild/GuildMemberLeft.cs

Exit code:
- 0 when all checks pass.
- 1 when any problem is detected.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[2]


@dataclass
class ContractExpectation:
    path: str
    event_type: str
    namespace: str = "Game.Core.Contracts.Guild"


EXPECTED: List[ContractExpectation] = [
    ContractExpectation(
        path="Game.Core/Contracts/Guild/GuildCreated.cs",
        event_type="core.guild.created",
    ),
    ContractExpectation(
        path="Game.Core/Contracts/Guild/GuildMemberJoined.cs",
        event_type="core.guild.member.joined",
    ),
    ContractExpectation(
        path="Game.Core/Contracts/Guild/GuildMemberLeft.cs",
        event_type="core.guild.member.left",
    ),
    ContractExpectation(
        path="Game.Core/Contracts/Guild/GuildDisbanded.cs",
        event_type="core.guild.disbanded",
    ),
    ContractExpectation(
        path="Game.Core/Contracts/Guild/GuildMemberRoleChanged.cs",
        event_type="core.guild.member.role_changed",
    ),
]


def check_contract(exp: ContractExpectation) -> Dict[str, object]:
    rel = Path(exp.path)
    full = ROOT / rel
    result: Dict[str, object] = {
        "path": exp.path,
        "exists": full.exists(),
        "namespace_ok": False,
        "event_type_ok": False,
    }

    if not full.exists():
        return result

    text = full.read_text(encoding="utf-8")
    result["namespace_ok"] = f"namespace {exp.namespace};" in text
    result["event_type_ok"] = (
        f"public const string EventType = \"{exp.event_type}\";" in text
    )
    return result


def main() -> int:
    results = [check_contract(exp) for exp in EXPECTED]
    ok = all(r["exists"] and r["namespace_ok"] and r["event_type_ok"] for r in results)

    report = {
        "ok": ok,
        "contracts": results,
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
