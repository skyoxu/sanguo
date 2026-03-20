---
PRD-ID: PRD-SANGUO-V3
Title: V3 Campaign System Assembly Page (Compatibility Filename)
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0010
Arch-Refs:
  - CH04
  - CH05
  - CH06
  - CH10
---

# V3 Campaign System Assembly Page

This is not a per-task detail page. It answers how V3 campaign mode is assembled inside the current repository instead of creating a parallel game stack.

## Reuse Baseline

- start-config and main-scene bootstrap flow
- event bus and DTO explainability path
- current tile, combat, economy, and save entry points
- current data pack, catalog, and quality-gate stack

## V3 Increment Modules

- commander and strategem selection
- campaign HUD parameter panel
- event-tile auto trigger and skip restriction
- camp building durability and effects
- Boss pressure, reveal, and forced challenge
- objective publish, settle, and reward-source routing
- campaign endgame adjudication

## Assembly Ownership

| Task | Concern | Current extant EventType set |
|---|---|---|
| T104 | event-tile auto-trigger and skip restriction | `core.sanguo.random_event.applied`, `core.sanguo.action_card.play.rejected`, `core.sanguo.combat.started` |
| T110 | content-pack schema and gate extension | none by default; schema/gate task |
| T137 | event-tile auto-trigger enforcement | `core.sanguo.action_card.play.rejected`, `core.sanguo.random_event.applied`, `core.sanguo.combat.started` |
| T138 | skip blocked-reason rule matrix | `core.sanguo.action_card.play.rejected`, `core.sanguo.random_event.applied`, `core.sanguo.combat.started` |
| T141 | objective reward source integration | `core.reward.offer.presented`, `core.reward.offer.selected`, `core.sanguo.loot.granted` |
| T142 | objective reward draft deterministic hook | `core.reward.offer.presented`, `core.reward.offer.selected`, `core.sanguo.loot.granted` |
| T171 | campaign content schema catalog extension | none yet; schema/catalog task with empty task-view `contractRefs` |
| T172 | campaign content cross-table constraints and bump rules | none yet; cross-table schema/gate task with empty task-view `contractRefs` |

## Design Principles

- do not create a parallel UI protocol; extend existing DTO and event paths first
- do not put rules in UI; Core owns rules, UI owns input and rendering
- content expansion must pass schema, catalog, and gate validation before runtime consumption
- schema and gate tasks may keep empty `contractRefs` if they do not own runtime domain events

## Key Couplings

- start payload fields come from `08-t50-game-start-config.md`
- commander and strategem picks come from `08-t55-characters.md`
- event-tile trigger restrictions couple to the board and Boss systems through `08-t63-global-events.md`
- reward-source flow couples `08-t56-random-events.md`, `08-t57-action-cards.md`, and `08-t62-relics.md`
- reward-offer compatibility constants used by `T141~T142` are currently generic landed contracts, not Sanguo-specific reward-source records
