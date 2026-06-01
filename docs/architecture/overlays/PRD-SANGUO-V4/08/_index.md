---
PRD-ID: PRD-SANGUO-V4
Title: PRD-SANGUO-V4 Feature Slice Index
Status: Accepted
ADR-Refs:
  - ADR-0004
Arch-Refs:
  - CH04
Test-Refs:
  - scripts/python/validate_task_overlays.py
---

# PRD-SANGUO-V4 Feature Slice Index

Index the PRD-SANGUO-V4 overlay slice for the minimal-intrusion combat upgrade, keeping the overlay focused on extensions to existing character data, combat contracts, combat resolver, and SanguoBattleView rather than parallel systems.

## Directory Role

- Collect PRD-SANGUO-V4 feature-slice architecture pages under `docs/architecture/overlays/PRD-SANGUO-V4/08/`.
- Use this overlay to document how v4 combat extends existing repository surfaces: `SanguoCharacterDefinition`, `GameStartConfig`, `SanguoCombatStarted`, `SanguoCombatEnded`, `SanguoCombatResolver`, and `SanguoBattleView`.
- Keep Base architecture and ADR thresholds referenced instead of copied into overlay pages.

## Document Groups

- Combat data and contracts: character attribute extension, enemy/Boss schema, skill schema, runtime stat composition, and combat event payload expansion.
- Combat simulation: auto-attack timing, action priority, direct damage, summons, AoE, reflect damage, DoT, win/loss handling, numeric bounds, and rounding rules.
- Battle scene UI: in-place expansion of `Game.Godot/Scenes/Sanguo/SanguoBattleView.tscn` and `Game.Godot/Scripts/Sanguo/SanguoBattleView.cs` for battle presentation, controls, combat log, result modal, and rewards.

## Pages

- `08-rules-freeze-and-assertion-routing.md`: freeze source routing, assertion ownership, and additive-surface constraints.
- `08-Contracts-Combat-Baseline.md`: additive contract baseline for v4 combat data, runtime snapshot contracts, and event payload extension points.
- `ACCEPTANCE_CHECKLIST.md`: closure checklist for overlay, contract, and test readiness.

<!-- TASK_BASELINE_START -->
```json
{
  "generated_at": "2026-06-01T16:22:57.303042+00:00",
  "files": [
    {
      "path": ".taskmaster/tasks/tasks.json",
      "exists": true,
      "sha256": "627041b84d5ebb30c62eac5965391f13251cfdbdc4a5ab15d693cefc778f746f",
      "bytes": 459776
    },
    {
      "path": ".taskmaster/tasks/tasks_back.json",
      "exists": true,
      "sha256": "cbe4f281018fa327803b37cbd33cb33a0631d49cdd5cd4d2678da7630732e06d",
      "bytes": 559325
    },
    {
      "path": ".taskmaster/tasks/tasks_gameplay.json",
      "exists": true,
      "sha256": "dbf5b956b62ee5f24f4889fb7158dcb8973cdfe20bccc08f3a1f58f56eb0c44e",
      "bytes": 625323
    }
  ]
}
```
<!-- TASK_BASELINE_END -->
