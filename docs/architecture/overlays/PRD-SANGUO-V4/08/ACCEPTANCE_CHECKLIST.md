---
PRD-ID: PRD-SANGUO-V4
Title: Acceptance Checklist
Status: Accepted
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0011
  - ADR-0024
Arch-Refs:
  - CH04
Test-Refs:
  - scripts/python/validate_task_overlays.py
---

# Acceptance Checklist

Use this checklist to confirm the PRD-SANGUO-V4 combat overlay covers the
minimal-intrusion PVE battle upgrade, additive contract evolution, scene reuse,
and test evidence expectations.

## Document Completeness

- [ ] References `docs/prd/prd_v4.md`,
  `docs/prd/PRD_V4_RULES_FREEZE.md`,
  `docs/prd/PRD_V4_ACCEPTANCE_ASSERTIONS.md`, and
  `docs/prd/PRD_V4_TRACEABILITY_MATRIX.md`.
- [ ] States that v4 scope covers character attributes, enemy and Boss
  attributes, PVE combat rules, and battle scene UI.
- [ ] States that parallel schemas, combat events, battle scenes, and start
  config surfaces must not be created.

## Architecture Checks

- [ ] Reuses `SanguoCharacterDefinition`, `GameStartConfig`,
  `SanguoCombatStarted`, `SanguoCombatEnded`, `SanguoCombatResolver`,
  `SanguoBattleView.tscn`, and `SanguoBattleView.cs`.
- [ ] Keeps `CombatRating` as a compatibility field.
- [ ] Defines the runtime attribute composition chain for battle start.
- [ ] Covers auto-attack timing, priority, summon targeting, AoE, reflect,
  DoT, win/loss handling, caps, and rounding rules.
- [ ] States that Boss and normal enemies use the same combat formula and only
  differ by configuration, presentation, and rewards.

## Implementation Checks

- [ ] Extends `Game.Core/Contracts/Sanguo/SanguoCharacterDefinition.cs` and
  updates `Game.Core/Services/Sanguo/SanguoCharactersCatalogLoader.cs`.
- [ ] Extends `Game.Core/Contracts/Sanguo/SanguoCombatContracts.cs` additively
  instead of introducing parallel event names.
- [ ] Routes v4 combat simulation through
  `Game.Core/Services/Sanguo/SanguoCombatResolver.cs`.
- [ ] Extends `Game.Godot/Scenes/Sanguo/SanguoBattleView.tscn` and
  `Game.Godot/Scripts/Sanguo/SanguoBattleView.cs` in place.
- [ ] Supports battle log window, pause and continue, 2x speed, shared result
  modal structure, and multi-reward display.

## Test Checks

- [ ] Adds loader coverage for extended combat attributes and `CombatRating`
  compatibility.
- [ ] Adds xUnit coverage for `AttackSpeed` floor, dodge and reduction caps,
  direct-damage minimum, DoT minimum, and reflect behavior.
- [ ] Adds deterministic evidence for summons, AoE, reflect, DoT, and post-fight
  HP handling.
- [ ] Adds Godot or scene-glue evidence for pause and continue, 2x speed,
  battle report flow, and reward display.
