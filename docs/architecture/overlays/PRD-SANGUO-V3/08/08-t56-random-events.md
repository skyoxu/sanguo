---
PRD-ID: PRD-SANGUO-V3
Title: V3 Random Objectives and Pace Compensation
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH05
  - CH06
Test-Refs:
  - Game.Core.Tests/Tasks/Task56RandomEventDeterminismTests.cs
  - Game.Core.Tests/Tasks/Task56RandomEventCoverageTests.cs
  - Tests.Godot/tests/UI/test_task56_hud_event_prompt_uses_payload.gd
---

# V3 Random Objectives and Pace Compensation

Owner page for T77, T105, T117, T118, T139, and T140.

## RandomObjectiveEngine Ownership

| Task | Concern | Current extant EventType set |
|---|---|---|
| T77 | objective loop integration | `core.sanguo.random_event.applied`, `core.sanguo.objective.skipped`, `core.sanguo.loot.granted` |
| T105 | objective publish-settle timeline closure | `core.sanguo.random_event.applied`, `core.sanguo.objective.skipped`, `core.sanguo.loot.granted`, `core.reward.offer.presented`, `core.reward.offer.selected` |
| T117 | objective generation determinism | `core.sanguo.objective.skipped`, `core.reward.offer.presented`, `core.reward.offer.selected` |
| T118 | objective settlement timeline closure | `core.sanguo.objective.skipped`, `core.reward.offer.presented`, `core.reward.offer.selected` |
| T139 | objective publish-after-Boss timing | `core.sanguo.objective.skipped`, `core.reward.offer.presented`, `core.reward.offer.selected` |
| T140 | objective settle and endgame suppression | `core.sanguo.objective.skipped`, `core.reward.offer.presented`, `core.reward.offer.selected` |

## V3 Semantics

- Random objectives are the pace-compensation layer for reaching camp quickly rather than dragging the round.
- At most one objective is active in a round.
- Objective settlement happens at camp start, before free camp actions.
- New objective publication happens after the Boss branch resolves and before board phase begins.
- If the run ends, no new objective is published.

## Timeline Contract

- publish-after-boss
- settle-on-camp-entry
- objective skipped on endgame
- deterministic generation under the same seed and content inputs

## Current vs Planned Contract Surface

Extant task-view event set:

- `core.sanguo.random_event.applied`
- `core.sanguo.objective.skipped`
- `core.sanguo.loot.granted`
- `core.reward.offer.presented`
- `core.reward.offer.selected`

Notes on extant surface:

- `core.reward.offer.presented` and `core.reward.offer.selected` are currently generic compatibility constants from `Game.Core/Contracts/EventTypes.cs`.
- They are allowed in V3 task views because objective settlement now owns reward-offer visibility and commit timing.

Planned additive names that stay in overlay text for now:

- `core.sanguo.objective.published`
- `core.sanguo.objective.settled`

## Guardrails

- HUD and logs consume normalized DTOs rather than inferring rules from raw event blobs.
- Boss timing must not leak objective publication earlier than the frozen order allows.
- The same seed, pack identity, and commander setup must produce the same objective choice and the same reward-offer presentation path.
- Correlation and causation context must survive objective publish, settlement, and reward handoff.

## Key Outputs

- objective selection result
- objective publish checkpoint
- objective settlement result
- reward-offer presentation context
- reward-offer commit context
