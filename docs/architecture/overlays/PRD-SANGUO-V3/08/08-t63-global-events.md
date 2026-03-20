---
PRD-ID: PRD-SANGUO-V3
Title: V3 Boss Pressure, Reveal, and Forced Challenge
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0015
Arch-Refs:
  - CH05
  - CH06
  - CH09
Test-Refs:
  - Game.Core.Tests/Tasks/Task63GlobalEventsTests.cs
  - Game.Core.Tests/Tasks/Task63GlobalEventStartCombatRejectedTests.cs
---

# V3 Boss Pressure, Reveal, and Forced Challenge

Owner page for T76, T89, T90, T101~T103, and T131~T136.

## BossPressureEngine Ownership

| Task | Concern | Current extant EventType set |
|---|---|---|
| T76 | pressure-engine integration | `core.sanguo.game.turn.advanced`, `core.sanguo.boss.challenge.prompted`, `core.sanguo.combat.started`, `core.sanguo.combat.ended` |
| T89 | pressure timeline and escalation | `core.sanguo.game.turn.advanced`, `core.sanguo.combat.started` |
| T90 | forced-challenge preemption | `core.sanguo.boss.challenge.prompted`, `core.sanguo.combat.started`, `core.sanguo.combat.ended` |
| T101 | Boss dice profile by difficulty and target duration | none yet; schema/config task until Boss profile contracts land |
| T102 | pressure resolver and explainability payload | none yet; result DTO and explainability task without landed Boss-pressure event family |
| T103 | reveal delay, challenge dragging, and hard-cap forcing | `core.sanguo.boss.challenge.prompted`, `core.sanguo.game.turn.ended` |
| T131 | Boss difficulty profile schema | none yet; schema task |
| T132 | Boss count and duration target validator | none yet; validator task |
| T133 | Boss elite-attack pressure resolver | none yet; calculation task without landed Boss-pressure event family |
| T134 | Boss pressure explain payload mapper | none yet; DTO mapper task without landed Boss-pressure event family |
| T135 | Boss reveal delay pressure stacking | `core.sanguo.boss.challenge.prompted`, `core.sanguo.game.turn.ended` |
| T136 | hard-cap forced challenge preemption | `core.sanguo.boss.challenge.prompted`, `core.sanguo.game.turn.ended` |

## Minimum Mechanic

- Boss dice profile is configured by difficulty and target duration.
- Resolution outputs:
  - elite wave count for the round
  - persistent pressure or debuff payload
- After Boss reveal, dragging is allowed, but cross-round pressure keeps increasing.
- At the hard cap, forced challenge is triggered on the leave-camp boundary.

## Current vs Planned Contract Surface

Extant task-view event set:

- `core.sanguo.game.turn.advanced`
- `core.sanguo.boss.challenge.prompted`
- `core.sanguo.combat.started`
- `core.sanguo.combat.ended`
- `core.sanguo.game.turn.ended`

Tasks intentionally keeping empty `contractRefs` right now:

- `T101`
- `T102`
- `T131`
- `T132`
- `T133`
- `T134`

Notes on extant surface:

- These six tasks currently do not have an honest landed Boss-specific runtime event family to bind to.
- They are schema, validator, resolver, or DTO-mapper tasks first, so empty `contractRefs` is less misleading than borrowing an unrelated sentinel.
- `T103`, `T135`, and `T136` already anchor to the more direct prompt and round-end sentinels.

Planned additive names that stay in overlay text for now:

- `core.sanguo.boss.revealed`
- `core.sanguo.boss.pressure.applied`
- `core.sanguo.boss.force_challenge_preempted_board`

## Force-Challenge Preemption Rule

- forced challenge resolves on the leave-camp boundary, not while board traversal is already active
- once the preemption branch starts, board actions do not resume for that round
- the reject path returns to camp and ends the round; it does not continue into board movement

## Explainability Requirement

Every pressure entry must explain:

- source
- value
- duration
- whether the value came from delay-based stacking

Forced-challenge prompt copy must explain:

- reject consequence
- current win-rate tier
- next-round pressure forecast

## System Coupling

- shares leave-camp boundary rules with `08-t52-turn-window-and-event-ordering.md`
- shares prompt or payload contract rules with `08-Contracts-Sanguo-GameLoop-Events.md`
- shares Boss-end precedence with `08-t60-game-end-and-settlement.md`

## Contract Debt Called Out Explicitly

`T101`, `T102`, and `T131~T134` now intentionally keep empty `contractRefs` until a dedicated Boss-pressure contract family lands. If a real Boss-profile or Boss-pressure record is introduced later, task views for these six tasks must be updated together in the same change.
