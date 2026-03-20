---
PRD-ID: PRD-SANGUO-V3
Title: V3 Reward Sources, Relics, and Gold Compensation
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH05
  - CH06
Test-Refs:
  - Game.Core.Tests/Tasks/Task62RelicsTests.cs
  - Tests.Godot/tests/UI/test_task62_relics_event_log.gd
---

# V3 Reward Sources, Relics, and Gold Compensation

Owner page for T106, T141, and T142.

## RewardSource Ownership

| Task | Concern | Current extant EventType set |
|---|---|---|
| T106 | random-objective reward source integration | `core.reward.offer.presented`, `core.reward.offer.selected`, `core.sanguo.loot.granted` |
| T141 | objective reward source integration | `core.reward.offer.presented`, `core.reward.offer.selected`, `core.sanguo.loot.granted` |
| T142 | objective reward draft deterministic hook | `core.reward.offer.presented`, `core.reward.offer.selected`, `core.sanguo.loot.granted` |

## V3 Semantics

- Random objectives, camp buildings, and Boss rewards may all feed the reward-source pipeline.
- If the relic pool is exhausted, reward fallback becomes gold compensation.
- Reward source and commit result must both enter explainability.

## Current vs Planned Contract Surface

Extant task-view event set:

- `core.reward.offer.presented`
- `core.reward.offer.selected`
- `core.sanguo.loot.granted`

Notes on extant surface:

- `core.reward.offer.presented` and `core.reward.offer.selected` are generic compatibility constants already landed in `Game.Core/Contracts/EventTypes.cs`.
- `core.sanguo.loot.granted` remains the concrete Sanguo-side reward result sentinel after the offer path commits.

Planned additive names that stay in overlay text for now:

- `core.sanguo.reward.source.tagged`
- `core.sanguo.reward.fallback.gold_granted`

## Design Requirements

- source tags enter contracts and logs
- deterministic hooks keep reward draft and replay aligned
- UI must not infer reward origin from side effects; it consumes DTOs only
- if the repository later lands a dedicated reward-source event family, task views for `T106`, `T141`, and `T142` must move off the current generic offer constants together
