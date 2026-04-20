# UI GDD Flow - SANGUO Chapter 7 Wiring Board

## 1. Scope And Single Goal

This document is the Chapter 7 UI wiring board for `sanguo`. It converts completed domain and gameplay systems into player-facing UI flows and serves as the governed artifact for post-task UI wiring.

Single goal: connect the minimum playable loop of `main menu -> enter board -> roll / move -> city ownership and toll -> economy settlement -> event / round feedback -> save and continue` before any polish-heavy screen work.

## 2. Player Loop Spine

The currently completed systems already define a strong gameplay spine:

1. Launch the Godot project and enter the board game runtime.
2. Initialize player, city, dice, and round systems.
3. Roll dice and move player pieces on the ring map.
4. Buy land, pay tolls, and update money state.
5. Process monthly, quarterly, and yearly economy or event changes.
6. Persist and resume the game with save/load.

If any of those steps is invisible or unclear to the player, the loop is not yet a complete player-facing UI loop.

## 3. Completed Capability Inventory

Completion state comes only from `.taskmaster/tasks/tasks.json`. The two view files enrich the completed tasks with test, acceptance, and contract context.

| Capability Group | Task IDs | Player-Facing Meaning | Primary UI Need |
| --- | --- | --- | --- |
| Runtime bootstrap and board setup | T01, T09 | Player can launch the game and expects a visible board-game UI shell | MainMenu, board root scene, startup failure feedback |
| Core board and actor systems | T02, T03, T04, T05, T06 | Map, city, player, dice, and turn rules define the core board loop | Board view, player panel, dice result prompt, turn order HUD |
| Economy and system settlement | T07, T12, T13, T14, T15, T16 | Buying land, paying tolls, monthly revenue, quarterly events, and annual value changes shape the economy loop | Money HUD, city ownership panel, toll prompt, settlement summary |
| Movement, AI, and round loop | T10, T11, T17 | Players and AI move through turns across the ring map | Move animation surface, AI action log, round/turn progression strip |
| Save, prompts, and money display | T18, T19, T20 | Save/load, event prompts, and currency display support session continuity and decision feedback | Save/load modal, prompt center, persistent money HUD |
| Event bus and global event visibility | T08, T63, T66, T67 | Domain events, global events, and forced challenge prompt summaries must be observable from player-facing logs or HUD summaries | Event log, prompt center, boss challenge summary strip |
| Combat, settlement, AI, relic, and regional economy extensions | T59, T60, T61, T62, T64, T65 | Combat round-trips, game end settlement, deterministic AI evidence, relic rewards, region capture, and synergy tolls add new mid-run feedback obligations | Combat result screen, settlement screen, AI action log, relic inventory, region/toll breakdown panel |
| Diagnostics and campaign content support | T114, T171 | Diagnostic retention and campaign schema catalogs are support systems that must remain inspectable for validation and authoring workflows | Diagnostics/audit view, content catalog validation report surface |
| Additional completed domain slices | T21, T22, T23, T24, T25, T26, T27, T28, T29, T30, T31, T32, T33, T34, T35, T36, T37, T38, T39, T40, T41, T42, T43, T44, T45, T46, T47, T48, T49, T50, T51, T52, T53, T54, T55, T56, T57, T58 | Completed features must still be discoverable from a player surface once wired | Feature-specific panels, logs, prompts, summaries, and overlays |

## 4. Player Flow Recomposition

### 4.1 Entry Flow

Player intent: enter the game and understand how a new or resumed session begins.

1. MainMenu shows start, continue, settings, and quit.
2. Continue is available only when a save exists.
3. On success, the player enters the board scene with visible money, turn, and active player context.
4. On failure, startup or save-load problems are shown visibly.

### 4.2 Board Turn Flow

Player intent: understand whose turn it is, what dice result occurred, and where the player moved.

1. Turn HUD shows active player and round stage.
2. Dice roll is visible and understandable.
3. Movement along the map is visible and tied to the dice outcome.
4. Landing on a tile triggers the correct city/event/economy surface.

### 4.3 Economy And Ownership Flow

Player intent: understand money changes, city ownership, tolls, and periodic settlements.

1. Current funds are always visible.
2. City ownership changes are visible and queryable.
3. Toll payments and land purchase prompts explain what happened and why.
4. Monthly, quarterly, and yearly settlement results are summarized visibly.

### 4.4 Persistence And Feedback Flow

Player intent: save, resume, and understand the latest important game events.

1. Save/load is reachable from a visible UI surface.
2. Event prompts are visible and actionable.
3. Recent important actions are preserved in logs, prompts, or summary panels.

## 5. UI Wiring Matrix

| Feature | UI Surface | Player Action | System Response | Test Refs |
| --- | --- | --- | --- | --- |
| T01/T09 runtime and UI shell | MainMenu / board root | Launch game | Enter the canonical game shell and show visible startup failure feedback when the board cannot initialize | `Tests.Godot/tests/Scenes/Smoke/test_main_scene_smoke.gd`, `Tests.Godot/tests/Tasks/test_task0001_acceptance.gd`, `Tests.Godot/tests/Tasks/test_task0009_acceptance.gd` |
| T02/T03/T04 board, city, and player state | Board view / player panel | Start a session and inspect the board | Show cities, players, and current board state in a player-readable layout | `Game.Core.Tests/Tasks/Task0002AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0003AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0004AcceptanceTests.cs` |
| T05/T10 dice and movement | Dice panel / move animation surface | Roll and move | Present dice outcome, movement path, and landing result clearly | `Game.Core.Tests/Tasks/Task0005AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0010AcceptanceTests.cs` |
| T06/T11/T17 turn loop and AI | Turn HUD / action log | Advance turns | Show active player, AI actions, and round progression | `Game.Core.Tests/Tasks/Task0006AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0011AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0017AcceptanceTests.cs` |
| T07/T12/T13/T14/T15/T16/T20 economy and settlement | Money HUD / city prompt / settlement summary | Buy land, pay toll, pass monthly or seasonal checkpoints | Update visible funds, ownership, toll outcomes, and settlement summaries | `Game.Core.Tests/Tasks/Task0007AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0012AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0013AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0014AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0015AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0016AcceptanceTests.cs`, `Tests.Godot/tests/Tasks/test_task0020_acceptance.gd` |
| T18/T19 save and event prompts | Save/load modal / prompt center | Save, load, or respond to an event | Persist game state and surface event feedback clearly | `Game.Core.Tests/Tasks/Task0018AcceptanceTests.cs`, `Tests.Godot/tests/Tasks/test_task0019_acceptance.gd` |
| T08/T63 event bus and global event routing | Event log / prompt center | Trigger or inspect domain events | Show event source, event id, replay context, and global event outcome without hiding failures in debug-only logs | `Game.Core.Tests/Services/EventBusTests.cs`, `Game.Core.Tests/Tasks/Task63GlobalEventsTests.cs` |
| T59/T60 combat round-trip and game end settlement | Combat result screen / settlement screen | Enter combat, finish combat, or finish a run | Return cleanly to the map after combat, write rewards or penalties back to map state, and render game-ended payload data on settlement | `Game.Core.Tests/Tasks/Task59CombatTriggerAndReturnTests.cs`, `Game.Core.Tests/Tasks/Task59CombatDeterminismTests.cs`, `Tests.Godot/tests/Scenes/Sanguo/test_task59_sanguo_battle_roundtrip_returns_to_map.gd`, `Game.Core.Tests/Tasks/Task60GameEndEventContractTests.cs`, `Tests.Godot/tests/UI/test_task60_settlement_screen_driven_by_game_ended_event.gd` |
| T61 deterministic AI strategy | Turn HUD / AI action log | Observe AI turns | Render AI decisions as replayable action-log entries with decision context, without skipping player-equivalent flow stages | `Game.Core.Tests/Tasks/Task61AiDeterministicStrategyTests.cs` |
| T62 relic system | Relic inventory / reward summary | Receive or inspect relics | Show unique relic drops, empty-drop exhaustion, and deterministic effect application order in run feedback | `Game.Core.Tests/Tasks/Task62RelicsTests.cs` |
| T64/T65 region capture and synergy tolls | Region overlay / city toll breakdown panel | Inspect owned regions or land on a region city | Show captured/lost region state, active bonuses, synergy toll total, and stable per-city breakdown | `Game.Core.Tests/Tasks/Task64RegionsTests.cs`, `Game.Core.Tests/Tasks/Task65RegionSynergyTollTests.cs`, `Game.Core.Tests/Tasks/Task65SynergyTollDomainEventTests.cs` |
| T66/T67 forced challenge summary path | HUD summary / event log | Trigger boss challenge prompt or fail-to-camp consequence | Render summary-only challenge evidence, localized fail consequence, pressure forecast, and loss context without opening blocking UI in deferred scope | `Tests.Godot/tests/UI/test_task66_force_challenge_prompted_ui_contract.gd`, `Tests.Godot/tests/Adapters/test_task66_boss_challenge_prompt_mapper_view_data.gd`, `Game.Core.Tests/Contracts/SanguoEventContractsTests.cs`, `Tests.Godot/tests/Integration/test_task66_boss_challenge_prompt_deferred_scope_guard.gd`, `Tests.Godot/tests/UI/test_task67_force_challenge_fail_path_to_camp.gd` |
| T114/T171 diagnostics retention and campaign schema catalog | Diagnostics report / content authoring validation report | Inspect retained diagnostics or validate campaign data | Keep cleanup and schema validation results visible as governed support output for QA and content authoring | `Game.Core.Tests/Services/DiagnosticRetentionWindowTests.cs`, `Game.Core.Tests/Tasks/Task114V3Tests.cs`, `Game.Core.Tests/Tasks/Task171SplitTests.cs` |

## 6. Screen Contracts

### 6.1 MainMenu

- Must expose start, continue, settings, and quit.
- Must show save availability for continue.
- Must show startup or load failure visibly.

### 6.2 Board View

- Must show current player, round/turn, and money.
- Must make board position and tile ownership visible.
- Must present dice and movement results as player-facing feedback.

### 6.3 Prompt And Summary Surfaces

- Must explain toll, purchase, event, and settlement outcomes.
- Must keep important economy changes visible to the player.
- Must not hide crucial decisions in logs only.

## 7. Explainability And Prompt Contract

- Critical state: active player, current funds, current tile, current round.
- Critical feedback: dice result, land purchase, toll payment, event trigger, monthly settlement.
- Prompt style should explain what changed and why.

## 8. Flow-Level State And Feedback Contract

- Empty state: before entering a game, show MainMenu instead of a blank board.
- Failure state: startup and save/load failures must be visible.
- Completion state: once in game, board, money, turn, and prompt surfaces must all be coherent.

## 9. Unwired UI Feature List

The following completed systems still need governed UI wiring:

- Board and city systems need a formal ownership and tile-detail surface.
- Dice and movement need a polished but deterministic player-facing result surface.
- Turn and AI progression need a formal action log and turn strip.
- Economy and settlement systems need governed summaries rather than scattered prompts only.
- Save/load and event prompts need a stable menu and modal architecture.
- Combat, settlement, relic, region, boss challenge, and campaign-content support flows need explicit UI surfaces rather than relying on core events or test-only evidence.
- Diagnostic retention and content schema validation need a governed report surface so support-system failures are inspectable outside raw logs.

## 10. Next UI Wiring Task Candidates

1. MainMenu plus continue and settings wiring.
2. Board HUD vertical slice for player, round, money, and tile context.
3. Dice and movement feedback surface.
4. Land ownership / toll / city detail panel.
5. Settlement and event summary surface.
6. Save/load modal and resume feedback flow.
7. Combat round-trip and settlement-result screens driven by core events.
8. Relic inventory, region overlay, synergy toll breakdown, and boss challenge summary surfaces.
9. Diagnostics and campaign schema validation report surfaces for QA/content authoring.

## 11. Current Implementation Audit

- The repo already has a large completed domain surface across board, city, player, economy, events, and save.
- The repo previously had no governed Chapter 7 UI artifact and no Chapter 7 orchestrator.
- The highest-value next wiring work is MainMenu, Board HUD, ownership/economy panels, and save/load flow.
- The completed master-task inventory also includes combat, settlement, relic, regional economy, forced challenge, diagnostics, and campaign schema support obligations that must be represented by explicit UI or report surfaces.

## 12. Flow Validation Matrix

| Flow | Automated Validation | Manual Validation | Evidence / Output |
| --- | --- | --- | --- |
| Entry Flow | `Tests.Godot/tests/Tasks/test_task0001_acceptance.gd`, `Tests.Godot/tests/Tasks/test_task0009_acceptance.gd` | Launch game, enter board shell, verify visible entry actions | GdUnit evidence and startup logs under `logs/ci/<date>/**` |
| Board Turn Flow | `Game.Core.Tests/Tasks/Task0005AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0010AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0017AcceptanceTests.cs` | Roll, move, and verify turn progression feedback | xUnit logs and optional UI smoke evidence |
| Economy Flow | `Game.Core.Tests/Tasks/Task0012AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0013AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0014AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0015AcceptanceTests.cs`, `Game.Core.Tests/Tasks/Task0016AcceptanceTests.cs` | Buy land, pay toll, advance settlement checkpoints, verify money and summary surfaces | xUnit acceptance logs and summary evidence |
| Save And Prompt Flow | `Game.Core.Tests/Tasks/Task0018AcceptanceTests.cs`, `Tests.Godot/tests/Tasks/test_task0019_acceptance.gd` | Save, load, trigger prompt, and verify visible feedback | Save evidence and prompt UI output |

## 13. Formal GDD And UX Distillation Rules

This document is a Chapter 7 wiring board, not the final screen-by-screen UX spec. A flow can move into formal GDD or UX docs only when:

- At least one automated validation covers the main path.
- At least one manual script confirms the player can interpret state and feedback.
- Critical player-facing state is visible on governed UI surfaces.

## 14. Immediate UI Integration Backlog

- MainMenu, continue, and settings shell.
- Board HUD for player, turn, round, and money.
- Dice and move result surface.
- Ownership, toll, and city detail panel.
- Settlement and event summary surfaces.
- Save/load modal and resume feedback flow.

## 15. Validation Plan

- After every `ui-gdd-flow.md` update, run `py -3 scripts/python/validate_chapter7_ui_wiring.py`.
- After every orchestrator or CLI change, run `py -3 scripts/python/dev_cli.py run-chapter7-ui-wiring --delivery-profile fast-ship --self-check`.
- Before submission, run `py -3 scripts/python/run_gate_bundle.py --mode hard --task-files .taskmaster/tasks/tasks_back.json .taskmaster/tasks/tasks_gameplay.json`.

## 16. Open Questions

- How to group player, city, and ownership info without overwhelming the board view.
- Whether event prompts should be modal-first or log-first.
- Whether settlement summaries should appear inline, as overlays, or as end-of-period reports.
