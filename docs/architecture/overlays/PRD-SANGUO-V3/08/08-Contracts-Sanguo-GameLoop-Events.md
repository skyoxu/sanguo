---
PRD-ID: PRD-SANGUO-V3
Title: Campaign GameLoop Contracts
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0010
Arch-Refs:
  - CH01
  - CH03
  - CH06
  - CH10
Test-Refs:
  - Game.Core.Tests/Domain/SanguoContractsTests.cs
  - Game.Core.Tests/Domain/SanguoContractInstantiationTests.cs
  - Tests.Godot/tests/UI/test_event_log_summary_localized.gd
  - Tests.Godot/tests/UI/test_task50_new_game_menu_started_event_payload.gd
Contracts-Refs:
  - Game.Core/Contracts/EventTypes.cs
  - Game.Core/Contracts/Sanguo/GameStartConfig.cs
  - Game.Core/Contracts/Sanguo/SanguoBossChallengePrompted.cs
  - Game.Core/Contracts/Sanguo/SanguoObjectiveSkipped.cs
---

# Campaign GameLoop Contracts

Owner page for T66~T70, T81~T84, T92, T109, T145~T146, T156, T169~T170, plus the semantic contract side of T151~T153 and T173.

## Contract Goals

- Extend the existing T2 contract surface with V3 campaign semantics instead of replacing it.
- Keep contract evolution additive-only.
- Ensure the UI consumes DTO or view-model shapes rather than raw event JSON.
- Distinguish landed runtime events from planned additive events so task-view `contractRefs` remain machine-checkable.
- Allow both Sanguo-specific event records and extant generic compatibility constants when they are actually landed in C#.

## Current Extant Contract Surface

The following event families already exist as C# contract constants and are allowed in task-view `contractRefs`.

### Sanguo lifecycle and replay baseline

- `core.sanguo.game.started`
- `core.sanguo.game.saved`
- `core.sanguo.game.loaded`
- `core.sanguo.game.turn.advanced`
- `core.sanguo.game.turn.started`
- `core.sanguo.game.turn.ended`
- `core.sanguo.game.ended`

### Sanguo explainability and reward-result baseline

- `core.sanguo.random_event.applied`
- `core.sanguo.action_card.played`
- `core.sanguo.action_card.play.rejected`
- `core.sanguo.building.built`
- `core.sanguo.loot.granted`
- `core.sanguo.relic.applied`
- `core.sanguo.objective.skipped`

### Sanguo forced-challenge and combat baseline

- `core.sanguo.boss.challenge.prompted`
- `core.sanguo.combat.started`
- `core.sanguo.combat.ended`

### Generic compatibility constants already landed in C#

- `core.run.state.transitioned`
- `core.run.continue.blocked`
- `core.reward.offer.presented`
- `core.reward.offer.selected`
- `core.reward.offer.skipped`

### Runtime guard baseline

- `core.sanguo.ai.decision.made`
- `core.sanguo.player.eliminated`
- `core.sanguo.player.state.changed`

## Deferred Additive Surface

The following names are valid V3 design targets, but they are not allowed inside task-view `contractRefs` until matching C# contracts land.

- `core.sanguo.camp.entered`
- `core.sanguo.camp.leave_requested`
- `core.sanguo.camp.leave_allowed`
- `core.sanguo.boss.pressure.applied`
- `core.sanguo.objective.published`
- `core.sanguo.objective.settled`
- `core.sanguo.reward.draft.opened`
- `core.sanguo.reward.draft.committed`

This rule prevents a fake sense of completeness where overlays mention a contract that the repository cannot actually compile or validate yet.

## Minimum V3 Contract Surface

### Start Payload

`GameStartConfig` must be able to carry at least:

- `RunMode`
- `CommanderId`
- `ActiveStrategemId`
- `PassiveStrategemId`
- `CampaignSeed`
- `ContentPackId`
- `ContentPackVersion`
- `ContentFingerprint`

### Common Field Baseline

- `RoundNumber`
- `CorrelationId`
- `CausationId`
- `RunMode`
- `ContentFingerprint`
- `SaveUntrusted`
- `ReplayTrustState`

## Task-to-Contract Binding

| Task | Primary concern | Current extant EventType set |
|---|---|---|
| T66 | forced-challenge prompt copy and confirm flow | `core.sanguo.boss.challenge.prompted` |
| T67 | reject branch returns to camp and ends round | `core.sanguo.boss.challenge.prompted` |
| T68 / T81 / T82 | popup-log atomic commit and HUD windowing | `core.sanguo.random_event.applied`, `core.sanguo.action_card.played`, `core.sanguo.building.built`, `core.sanguo.loot.granted`, `core.sanguo.objective.skipped`, `core.sanguo.game.ended` |
| T69 / T92 / T112 | release or dev i18n exposure policy on UI summaries | `core.sanguo.boss.challenge.prompted`, `core.sanguo.random_event.applied`, `core.sanguo.action_card.played`, `core.sanguo.loot.granted`, `core.sanguo.objective.skipped`, `core.sanguo.game.ended` |
| T70 / T83 / T84 / T91 | replay trust inputs, mismatch policy, save_untrusted | `core.sanguo.game.started`, `core.sanguo.game.saved`, `core.sanguo.game.loaded`, `core.sanguo.game.turn.advanced`, `core.sanguo.game.ended`, `core.sanguo.boss.challenge.prompted` |
| T93 / T96 | campaign bootstrap and lifecycle compatibility markers | `core.sanguo.game.started`, `core.run.state.transitioned` |
| T105 / T117 / T118 | objective publish or settle reward-offer bridge | `core.sanguo.objective.skipped`, `core.reward.offer.presented`, `core.reward.offer.selected` |
| T108 | campaign AI disable runtime guard | `core.run.continue.blocked`, `core.sanguo.ai.decision.made` |
| T119 / T120 | reward draft present, select, and skip | `core.reward.offer.presented`, `core.reward.offer.selected`, `core.reward.offer.skipped` |
| T109 | campaign contracts and DTO mapper completion integration pack | none yet; contract and DTO governance task with empty task-view `contractRefs` |
| T145 | campaign contract set completion | none yet; contract-set governance task with empty task-view `contractRefs` |
| T146 | campaign HUD DTO mapper closure | none yet; DTO mapper governance task with empty task-view `contractRefs` |
| T151 | core assertion hard-gate closure integration pack | none yet; cross-family assertion closure with empty task-view `contractRefs`; semantic contract owner remains this page while execution owner remains `08-Contracts-Quality-Metrics.md` |
| T152 | UI assertion hard-gate closure | none yet; UI summary/assertion bundle with empty task-view `contractRefs`; semantic contract owner remains this page while execution owner remains `08-Contracts-Quality-Metrics.md` |
| T153 | R4 end-to-end explainability and replayability gate | `core.sanguo.game.started`, `core.sanguo.game.saved`, `core.sanguo.game.loaded`, `core.sanguo.game.turn.advanced`, `core.sanguo.boss.challenge.prompted`, `core.sanguo.random_event.applied`, `core.sanguo.action_card.played`, `core.sanguo.loot.granted`, `core.sanguo.objective.skipped`, `core.sanguo.game.ended`; replay/explainability gate now binds task-view `contractRefs` to landed replay/explainability runtime events; semantic contract owner remains this page while runtime-loop semantic owner also includes `08-feature-slice-t2-monopoly-loop.md` |
| T156 | signal XML documentation completeness gate | none yet; documentation completeness gate with empty task-view `contractRefs` |
| T169 | campaign contract additive set and versioning | none yet; additive-only contract governance task with empty task-view `contractRefs` |
| T170 | campaign contract field harmonization for runtime flows | none yet; runtime-field harmonization task with empty task-view `contractRefs` |
| T173 | replay integrity and mismatch policy hard-gate bundle | none yet; replay-trust assertion bundle with empty task-view `contractRefs`; semantic contract owner remains this page while execution owner remains `08-Contracts-Quality-Metrics.md` |

## Contract Hygiene Rule

- Task-view `contractRefs` may cite landed `EventType` constants from either `Game.Core/Contracts/Sanguo/**` or `Game.Core/Contracts/EventTypes.cs`.
- Planned names stay in overlay text only until the matching C# contract surface lands.
- T109, T145, T146, T151, T152, T156, T169, T170, and T173 intentionally keep empty `contractRefs` until they consume or publish a landed runtime event family.
- If a task starts consuming or publishing a different runtime event family, the owner overlay and task views must be updated together.
