---
PRD-ID: PRD-SANGUO-V3
Title: V3 Campaign Start Config and Bootstrap Payload
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH05
  - CH06
  - CH10
Test-Refs:
  - Game.Core.Tests/Tasks/Task50GameStartConfigTests.cs
  - Tests.Godot/tests/UI/test_task50_new_game_menu_started_event_payload.gd
---

# V3 Campaign Start Config and Bootstrap Payload

Owner page for T93.

## StartPayload Ownership

| Task | Concern | Current extant EventType set |
|---|---|---|
| T93 | campaign run mode and bootstrap payload completion | `core.sanguo.game.started`, `core.run.state.transitioned` |

## Goal

- Make campaign mode an explicit runtime mode, not a side effect of UI branching.
- Carry commander, strategem, map, seed, and content-pack identity through one bootstrap payload.
- Emit a real run-mode transition marker so later replay or diagnostics can prove that campaign mode was entered intentionally.

## Minimum Fields

- `RunMode`
- `CommanderId`
- `ActiveStrategemId`
- `PassiveStrategemId`
- `MapId`
- `Seed`
- `ContentPackId`
- `ContentPackVersion`
- `ContentFingerprint`

## Current vs Planned Contract Surface

Extant task-view event set:

- `core.sanguo.game.started`
- `core.run.state.transitioned`

Notes on extant surface:

- `core.sanguo.game.started` is the current Sanguo run-start sentinel.
- `core.run.state.transitioned` is currently provided by `Game.Core/Contracts/EventTypes.cs` as a generic compatibility constant and is allowed in task-view `contractRefs` because it is already landed.

Planned additive names that stay in overlay text for now:

- `core.sanguo.campaign.started`
- `core.sanguo.bootstrap.validated`

## Runtime Requirements

- UI config -> `GameStartConfig` -> runtime bootstrap -> save header must stay field-identical.
- Campaign bootstrap fields are replay-trust inputs, not temporary UI-only values.
- `RunMode` transition and start payload must agree; a campaign payload paired with a non-campaign transition is invalid evidence.
- If a new field affects replay or save compatibility, it must be added to the contract and gate set together.

## Key Outputs

- campaign bootstrap payload
- normalized start config snapshot
- save-header bootstrap fields
- first `core.run.state.transitioned` record for campaign entry
- first `core.sanguo.game.started` envelope
