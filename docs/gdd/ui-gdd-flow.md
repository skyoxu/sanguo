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
