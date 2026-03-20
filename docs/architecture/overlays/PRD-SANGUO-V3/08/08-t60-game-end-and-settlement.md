---
PRD-ID: PRD-SANGUO-V3
Title: V3 Campaign Endgame and Settlement
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH06
  - CH10
Test-Refs:
  - Game.Core.Tests/Tasks/Task60GameEndEventContractTests.cs
  - Tests.Godot/tests/UI/test_task60_settlement_screen_driven_by_game_ended_event.gd
---

# V3 Campaign Endgame and Settlement

Owner page for T74, T85, T86, T100, T107, T129, T130, T143, and T144.

## CampaignRuleEngine Ownership

| Task | Concern | Current extant EventType set |
|---|---|---|
| T74 | rule-engine integration closure | `core.sanguo.game.started`, `core.sanguo.game.ended`, `core.sanguo.player.eliminated` |
| T85 | campaign runmode isolation | `core.sanguo.game.started`, `core.sanguo.game.ended` |
| T86 | endgame adjudicator | `core.sanguo.game.ended`, `core.sanguo.player.eliminated` |
| T100 | settlement and fatal-camp integration | `core.sanguo.game.ended` |
| T107 | campaign win-lose adjudicator completion | `core.sanguo.game.ended` |
| T129 | camp durability fatal preemption rule | `core.sanguo.game.ended` |
| T130 | camp-fail settlement routing | `core.sanguo.game.ended` |
| T143 | final-Boss victory adjudication branch | `core.sanguo.game.ended` |
| T144 | camp-failure defeat adjudication branch | `core.sanguo.game.ended` |

## RunMode Isolation

- `Campaign` mode uses a new win/lose set:
  - defeat the final Boss -> win
  - camp-building durability reaches zero -> lose
- legacy elimination or bankruptcy semantics may still exist for other modes, but they may not leak into Campaign adjudication

## Settlement Order

- building-durability fatal conditions outrank other pending outcomes
- if the Boss branch ends the run directly, no new objective is published
- settlement triggers diagnostic-retention cleanup
- `core.sanguo.game.ended` is the extant runtime sentinel; finer campaign completed or failed names remain additive-only until landed

## Pending Additive Contracts

Planned names kept in overlay text only until landed:

- `core.sanguo.campaign.completed`
- `core.sanguo.campaign.failed`
- `core.sanguo.settlement.rendered`

## Failure Precedence

- building-durability fatal conditions outrank pending objective publication
- final Boss victory outranks next-round objective generation
- replay and save-header outputs must match the same adjudication result as the settlement UI
- branch-specific closure tasks in this page currently converge on the shared sentinel `core.sanguo.game.ended`; they do not yet own finer-grained landed event families

## Key Outputs

- endgame adjudication result
- settlement DTO
- save-header final state
- diagnostic-retention cleanup trigger
