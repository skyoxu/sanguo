---
PRD-ID: PRD-SANGUO-V3
Title: V3 Commander and Strategem Selection
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0010
Arch-Refs:
  - CH05
  - CH06
  - CH10
Test-Refs:
  - Game.Core.Tests/Tasks/Task55CharacterConfigParsingTests.cs
  - Game.Core.Tests/Tasks/Task55CharacterEventSnapshotTests.cs
---

# V3 Commander and Strategem Selection

Owner page for T94, T121, and T122.

## CommanderSelection Ownership

| Task | Concern | Current extant EventType set |
|---|---|---|
| T94 | commander roster and strategem pick flow integration | `core.sanguo.game.started` |
| T121 | commander roster lock/open states | `core.sanguo.game.started` |
| T122 | active/passive strategem selection guard | `core.sanguo.game.started` |

## Goal

- Upgrade `character` into the V3 commander entry point.
- Require exactly one commander, one active strategem, and one passive strategem at start.
- Keep commander and strategem decisions inside the start payload rather than distributing them across unrelated runtime state updates.

## State Model

- `locked`
- `available`
- `selected`

First delivery may expose one default commander and leave the rest explicitly locked.

## Current vs Planned Contract Surface

Extant task-view event set:

- `core.sanguo.game.started`

Why the extant set is this small:

- Current task views treat commander and strategem selection as start-payload ownership, not as independent runtime event families.
- Until dedicated contract records land, selection closure is proven by the shape of `core.sanguo.game.started` payload rather than by extra event names.

Planned additive names that stay in overlay text for now:

- `core.sanguo.commander.selected`
- `core.sanguo.strategem.selected`

## Interaction Guardrails

- Pick results enter the start payload; they do not live as menu-only state.
- Core validates pick legality; UI only renders availability and selection state.
- Locked roster items must remain explainable in localized UI copy.
- If a future implementation starts emitting runtime commander-state updates, task views and this owner page must be updated together.
