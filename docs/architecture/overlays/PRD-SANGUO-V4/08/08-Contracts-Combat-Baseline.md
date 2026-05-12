---
PRD-ID: PRD-SANGUO-V4
Title: Contracts Combat Baseline
Status: Accepted
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0011
  - ADR-0024
Arch-Refs:
  - CH04
Test-Refs:
  - Game.Core.Tests/Domain/SanguoContractsTests.cs
  - Game.Core.Tests/Tasks/Task73ContractCompatibilityGateTests.cs
Contracts-Refs:
  - Game.Core/Contracts/Sanguo/SanguoCharacterDefinition.cs
  - Game.Core/Contracts/Sanguo/SanguoCombatContracts.cs
Status: Accepted
---

# Contracts Combat Baseline

This page defines the minimal additive contract baseline for PRD-SANGUO-V4 combat work. It extends existing `Game.Core/Contracts/Sanguo/` surfaces without renaming event types, removing `CombatRating`, or introducing parallel combat DTO families.

## Reused Contract Surfaces

- `Game.Core/Contracts/Sanguo/SanguoCharacterDefinition.cs` remains the player character schema entry point.
- `Game.Core/Contracts/Sanguo/GameStartConfig.cs` remains the game-start contract surface.
- `Game.Core/Contracts/Sanguo/SanguoCombatContracts.cs` remains the combat event and result surface.
- Existing event names `core.sanguo.combat.started` and `core.sanguo.combat.ended` stay unchanged.

## Character Contract Extension Boundary

`SanguoCharacterDefinition` is extended additively for v4 combat-readiness:

- Keep existing fields unchanged, especially `CombatRating`.
- Add optional combat stat payload for runtime-capable combat configuration.
- Keep economy-step and portrait fields in place; v4 does not split character config into a second schema.
- Treat missing v4 combat payload as compatibility mode, not as a schema error for legacy callers.

Recommended additive shape:

- `SanguoCombatStatsDefinition`: base combat attributes for player, enemy, and Boss definitions.
- `SanguoSummonStatsDefinition`: additive summon defaults and inheritance knobs.
- `SanguoCharacterCombatProfile`: optional character-owned combat profile container that can grow without changing the legacy constructor call sites.

## Combat Contract Extension Boundary

`SanguoCombatContracts.cs` is extended additively:

- `SanguoCombatResult` keeps `Outcome`, `MoneyDelta`, `EncounterTarget`, and `EffectiveCombatRating`.
- Add optional battle-detail payload fields for runtime HP, reward list, battle log summary, and enemy/Boss identifiers.
- Keep `SanguoCombatStarted` and `SanguoCombatEnded` event type constants unchanged.
- Allow optional runtime snapshot payloads on combat start and end events rather than replacing the current constructor surface.

Recommended additive shape:

- `SanguoCombatRuntimeSnapshot`: runtime-computed unit state shown to battle UI and tests.
- `SanguoCombatUnitSnapshot`: unit name, role, runtime stats, passive-skill ids, relic ids, and placeholder buff/debuff ids.
- `SanguoCombatRewardItem`: reward popup item payload.
- `SanguoCombatLogEntry`: structured log window entry payload.

## Additive Compatibility Rules

- Existing public constructor argument order must remain valid for current call sites.
- New fields should be nullable, optional, or default-initialized when added to existing records.
- New record types must remain BCL-only and stay under `Game.Core.Contracts.Sanguo`.
- Overlay and contract evolution must satisfy `V4-A-024`: additive-only changes, unchanged event names, and no parallel combat event surface.

## Gate Ownership

- Contract structure gate: `py -3 scripts/python/validate_contracts.py`
- Domain contract lint gate: `py -3 scripts/python/check_domain_contracts.py`
- Compatibility intent gate: `Game.Core.Tests/Tasks/Task73ContractCompatibilityGateTests.cs`

## Change Control

If v4 combat contract fields, event payloads, or runtime snapshot boundaries change, update together:

1. `docs/prd/PRD_V4_RULES_FREEZE.md`
2. `docs/prd/PRD_V4_ACCEPTANCE_ASSERTIONS.md`
3. `docs/prd/PRD_V4_TRACEABILITY_MATRIX.md`
4. `docs/architecture/overlays/PRD-SANGUO-V4/08/08-Contracts-Combat-Baseline.md`
5. `Game.Core/Contracts/Sanguo/` additive contract code
