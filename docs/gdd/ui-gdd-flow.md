---
GDD-ID: GDD-TEMPLATE-UI-FLOW-V1
Title: Template UI Wiring Flow GDD
Status: Template
Owner: template-owner
Last Updated: 2026-04-20
Encoding: UTF-8
Applies-To:
  - .taskmaster/tasks/tasks.json
  - .taskmaster/tasks/tasks_back.json
  - .taskmaster/tasks/tasks_gameplay.json
ADR-Refs:
  - ADR-0010
  - ADR-0011
  - ADR-0019
  - ADR-0025
---

# Template UI Wiring Flow GDD

This file is the Chapter 7 UI wiring SSoT template. Business repositories should replace the placeholder rows with their own player-facing UI flow, scenes, contracts, tests, and acceptance evidence.

## 1. Scope And Goal

Chapter 7 does not rewrite PRD, GDD, or architecture overlays. It converts completed domain and gameplay capabilities into player-facing UI wiring.

Use this document after the relevant backlog slice has completed Chapter 6 and no unrecorded P0/P1 Needs Fix remains.

## 2. Player Loop Backbone

Describe the playable loop from the player's point of view.

Example structure:

1. Main menu.
2. New run or continue.
3. Character or setup selection.
4. Core gameplay screen.
5. Reward, event, shop, rest, or summary surfaces.
6. Return, fail, win, or continue boundary.

## 3. Completed Capability Groups

Group completed tasks by player-facing capability, not by implementation module.

| Capability Group | Task IDs | Player-Facing Meaning | Primary UI Need |
| --- | --- | --- | --- |
| Example runtime foundation | T0 | Player can start the project | Main scene enters a visible shell |

## 4. Player Experience Flows

Document the concrete flows the player should experience.

### 4.1 Main Entry Flow

Describe how the player reaches the first meaningful interaction.

### 4.2 Core Gameplay Flow

Describe the main loop and state transitions.

### 4.3 Secondary Surface Flow

Describe supporting screens such as reward, rest, shop, event, inventory, settings, or run summary.
Completed scope list for this track:

- T147 `Module: campaign content schema extension (split from T110) integration pack`
- T148 `Module: campaign content quality gates closure (split from T110)`
- T149 `Module: campaign full-loop boss-win scenario (split from T111)`
- T150 `Module: campaign full-loop camp-fail scenario (split from T111)`
- T151 `Module: core assertion hard-gate closure (split from T112) integration pack`
- T152 `Module: UI assertion hard-gate closure (split from T112)`
- T153 `Module: R4 end-to-end explainability and replayability gate`
- T154 `Module: freeze policy guard for non-crash feedback suppression`
- T155 `Module: freeze change-control triplet gate`
- T156 `Module: signal XML documentation completeness gate (PH9-B2)`
- T157 `Module: CI signal compliance workflow hard-gate (PH9-B4) integration pack`
- T158 `Module: GDScript subscription lifecycle leak guard (PH9-B5) integration pack`
- T159 `Module: privacy-compliance document and policy gate (PH16-B4)`
- T160 `Module: logging-guidelines document and lint gate (PH16-B5)`
- T161 `Module: migration compatibility report automation gate (PH20-B3) integration pack`
- T162 `Module: signal compliance aggregator implementation (split from T157)`
- T163 `Module: signal compliance workflow hard-gate wiring (split from T157)`
- T165 `Module: GdUnit signal lifecycle leak fixtures (split from T158)`
- T166 `Module: migration compatibility report generator (split from T161)`
- T167 `Module: migration compatibility completeness validator (split from T161)`
- T168 `Module: migration compatibility CI hard-gate integration (split from T161)`
- T169 `Module: campaign contract additive set and versioning (split from T145)`
- T171 `Module: campaign content schema catalog extension (split from T147)`
- T172 `Module: campaign content cross-table constraints and bump rules (split from T147)`
- T173 `Module: core assertion hard-gate bundle A-013 to A-015 (split from T151)`
- T174 `Module: core assertion hard-gate bundle A-016 to A-019 (split from T151)`
- T175 `Module: core assertion hard-gate A-020 compatibility closure (split from T151)`
- T176 `Wire UI: MainMenu And Boot Flow`
- T177 `Wire UI: Runtime HUD And Outcome Surfaces`
- T178 `Wire UI: Combat Pressure And Interaction Surfaces`
- T179 `Wire UI: Economy Build And Progression Panels`
- T180 `Wire UI: Config Audit And Migration Surfaces`

## 5. UI Wiring Matrix

Every completed feature that needs a player-facing surface should appear here.

| Feature | Task IDs | UI Surface | Player Action | System Response | State Boundary | Test Refs |
| --- | --- | --- | --- | --- | --- | --- |
| Example completed feature | T0 | `Game.Godot/Scenes/Main.tscn` | Start | Show first playable screen | Does not mutate save data | `TODO` |

## 6. Screen Contracts

Define the UI contract for each major surface.

### 6.1 Main Menu

Required visible state:

- TODO

Required commands:

- TODO

### 6.2 Core Gameplay Screen

Required visible state:

- TODO

Required commands:

- TODO

## 7. Validation Plan

List automated or manual validation for each flow.

| Flow | Validation Type | Test Refs Or Manual Evidence |
| --- | --- | --- |
| Main entry | automated or manual | TODO |

## 8. Risks And Stop-Loss

List UI wiring risks that should stop Chapter 7.

- A completed `status = done` task has no UI surface or explicit no-UI rationale.
- A UI surface bypasses the domain/service boundary.
- Player-visible text bypasses localization rules when the project has i18n requirements.
- UI actions mutate deterministic state during preview, hover, refresh, or open-panel behavior.

## 9. Unwired UI Feature List

List completed features that are not wired to UI yet, or explicitly mark them as no-UI-needed.

| Task IDs | Capability | Missing UI Surface | Reason | Next Action |
| --- | --- | --- | --- | --- |
| T0 | Example completed feature | Main surface | Template placeholder | Replace in business repo |

## 10. Next UI Wiring Task Candidates

Generate follow-up tasks from this section only after the matrix and unwired list are current.

| Candidate | Source Matrix Row | Scope | Suggested Test Refs |
| --- | --- | --- | --- |
| Wire first playable surface | Example completed feature | Add visible scene and command binding | TODO |
