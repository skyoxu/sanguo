---
PRD-ID: PRD-SANGUO-V3
Title: V3 Camp Building Slots, Durability, and Effects
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH05
  - CH06
Test-Refs:
  - Game.Core.Tests/Tasks/Task58BuildingConfigAndEffectsTests.cs
  - Game.Core.Tests/Tasks/Task58BuildingBuildWindowTests.cs
---

# V3 Camp Building Slots, Durability, and Effects

Owner page for T97, T98, T99, and T125~T128.

## CampBuilding Ownership

| Task | Concern | Current extant EventType set |
|---|---|---|
| T97 | slot and durability model integration | `core.sanguo.building.built`, `core.sanguo.game.ended` |
| T98 | one camp action per round guard | `core.sanguo.building.built`, `core.sanguo.action_card.play.rejected`, `core.sanguo.game.turn.advanced` |
| T99 | minimum building effects integration | `core.sanguo.building.built`, `core.sanguo.relic.applied`, `core.sanguo.loot.granted` |
| T125 | camp five-slot durability model | `core.sanguo.building.built`, `core.sanguo.game.ended` |
| T126 | camp durability persistence mapping | `core.sanguo.building.built`, `core.sanguo.game.ended` |
| T127 | camp building effects set A | `core.sanguo.building.built`, `core.sanguo.relic.applied`, `core.sanguo.loot.granted` |
| T128 | camp building effects set B | `core.sanguo.building.built`, `core.sanguo.relic.applied`, `core.sanguo.loot.granted` |

## Fixed Structure

- Camp has 5 fixed building slots.
- Each building has independent durability.
- Each camp round allows exactly 1 camp action.

## Minimum Effect Set

- Relic Workshop
- Tavern
- Defense Center
- War Hall
- Training Ground

## Current vs Planned Contract Surface

Extant task-view event set:

- `core.sanguo.building.built`
- `core.sanguo.relic.applied`
- `core.sanguo.loot.granted`
- `core.sanguo.action_card.play.rejected`
- `core.sanguo.game.turn.advanced`
- `core.sanguo.game.ended`

Planned additive names that stay in overlay text for now:

- `core.sanguo.camp.action.blocked`
- `core.sanguo.building.disabled`
- `core.sanguo.camp.durability.settled`

## Rule Boundaries

- A building at durability 0 is permanently disabled for the run.
- There is no repair path that reopens a 0-durability building in the same run.
- The second camp action attempt must fail deterministically with an explainable blocked reason.
- Building effects must remain replay-safe and explainable.
- Persistence mapping must preserve per-slot durability and disabled state without inventing a second source of truth.
