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
  "generated_at": "2026-06-10T15:50:17.229054+00:00",
  "files": [
    {
      "path": ".taskmaster/tasks/tasks.json",
      "exists": true,
      "sha256": "66e4401ba9832bbd6c6643637661e77c243dcd5fe564d731faa731aeab819846",
      "bytes": 527807
    },
    {
      "path": ".taskmaster/tasks/tasks_back.json",
      "exists": true,
      "sha256": "649a139ff6a9d29b0ab3c71dbd24de2e0f87595b7b453f7f862239ea3e987984",
      "bytes": 559888
    },
    {
      "path": ".taskmaster/tasks/tasks_gameplay.json",
      "exists": true,
      "sha256": "25f8a6e7ae2cb7f2a65c287c124344c6e48108afc64e346ead333f1baf3fdbb5",
      "bytes": 641961
    }
  ]
}
```
<!-- TASK_BASELINE_END -->
