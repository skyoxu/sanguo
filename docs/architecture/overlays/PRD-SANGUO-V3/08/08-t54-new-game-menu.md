---
PRD-ID: PRD-SANGUO-V3
Title: V3 Campaign Config Menu and HUD Parameter Panel
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0010
Arch-Refs:
  - CH06
  - CH10
Test-Refs:
  - Tests.Godot/tests/UI/Task54/test_task54_new_game_setup_constraints_and_start.gd
  - Tests.Godot/tests/UI/Task54/test_task54_new_game_setup_starts_game_with_selected_players_and_money.gd
---

# V3 Campaign Config Menu and HUD Parameter Panel

Owner page for T95.

## ConfigUi Ownership

| Task | Concern | Current extant EventType set |
|---|---|---|
| T95 | campaign HUD parameter panel and i18n | `core.sanguo.game.started`, `core.sanguo.game.turn.advanced`, `core.sanguo.boss.challenge.prompted`, `core.sanguo.random_event.applied` |

## Config Menu Responsibilities

- Show campaign-only inputs before run start.
- Confirm commander, strategem, map, and seed as one coherent start package.
- Hand the same normalized fields to the in-run HUD panel.

## HUD Parameter Panel Responsibilities

- Show commander, strategems, round marker, and Boss-pressure context.
- Use zh/en localization.
- In release mode, never surface raw i18n keys or raw event codes.

## Current vs Planned Contract Surface

Extant task-view event set:

- `core.sanguo.game.started`
- `core.sanguo.game.turn.advanced`
- `core.sanguo.boss.challenge.prompted`
- `core.sanguo.random_event.applied`

Planned additive names that stay in overlay text for now:

- `core.sanguo.hud.context.refreshed`
- `ui.menu.campaign.settings.confirmed`

## Guardrails

- The HUD panel renders DTOs; it does not infer rules from raw state blobs.
- The menu and the HUD panel must not drift into two different field vocabularies.
- Localization fallback behavior follows the V3 explainability gate, not ad hoc UI logic.
