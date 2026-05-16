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
  "generated_at": "2026-05-16T05:06:01.109537+00:00",
  "files": [
    {
      "path": ".taskmaster/tasks/tasks.json",
      "exists": true,
      "sha256": "d0861a840ee2552269fbc28ae46778e0d749e9b588c48719a469ebd68ab78723",
      "bytes": 457196
    },
    {
      "path": ".taskmaster/tasks/tasks_back.json",
      "exists": true,
      "sha256": "1c1d451acec57752440811efed645c0211ecdba79ec5dc7103539637fb7a4ca7",
      "bytes": 558858
    },
    {
      "path": ".taskmaster/tasks/tasks_gameplay.json",
      "exists": true,
      "sha256": "35b2058c796875ce6d2ca526b39fcbc80f680ae5c2bfa2fb885a218553e803b1",
      "bytes": 622702
    }
  ]
}
```
<!-- TASK_BASELINE_END -->
