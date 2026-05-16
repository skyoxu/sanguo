# Execution Plan

- Date: 2026-05-16
- Task: 184
- Status: active

## Goal

Close residual semantic Needs Fix for Task 184 acceptance semantics without violating Chapter 6 stop-loss routing.

## Scope

- Task files: `.taskmaster/tasks/tasks_back.json`, `.taskmaster/tasks/tasks.json`
- Evidence anchors in referenced tests:
  - `Game.Core.Tests/Domain/CityTests.cs`
  - `Game.Core.Tests/Domain/SanguoPlayerTests.cs`
  - `Game.Core.Tests/Services/SanguoSaveLoadServiceTests.cs`
  - `Game.Core.Tests/Tasks/Task59CombatDeterminismTests.cs`
  - `Tests.Godot/tests/Scenes/Smoke/test_main_scene_smoke.gd`

## Current Step

Stop-loss hold: route requires `inspect` due to `recent_failure_summary` repeated failure family.

## Stop-Loss Boundary

Do not rerun full 6.7 or additional 6.8 while `chapter6_next_action=inspect` and `blocked_by=recent_failure_summary` remain active.

## Next Action

1. Reconcile acceptance semantic wording so each acceptance item maps to a concrete, falsifiable behavior and matching refs.
2. Re-run only the lane explicitly recommended by `chapter6-route --recommendation-only` after step 1.
3. If route unlocks and all P0/P1 findings clear, continue to 6.9 local hard checks.

## Exit Criteria

- `resume-task` no longer reports `recommended_action=inspect` and `blocked_by=recent_failure_summary`.
- Latest review artifacts show no unresolved P0/P1 Needs Fix for Task 184 under fast-ship policy.
- 6.9 local hard checks executed and passing evidence captured.

## Evidence Paths

- `logs/ci/2026-05-16/task-resume/task-184-resume-summary.json`
- `logs/ci/2026-05-16/sc-review-pipeline-task-184-96fb9000348c496e9d3bc7fabbe00f38/summary.json`
- `logs/ci/2026-05-16/sc-needs-fix-fast-task-184/summary.json`
- `logs/ci/2026-05-16/sc-needs-fix-fast-task-184/round-1/review-semantic-equivalence-auditor.md`
