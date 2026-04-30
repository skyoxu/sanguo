# Task 151 Execution Plan

## Goal
Close Task 151 Chapter 6 integration pack with deterministic test evidence and acceptance refs consistency, while resolving in-branch blockers surfaced by hard checks.

## Scope
- Update task view acceptance refs for Task 151 in `.taskmaster/tasks/tasks_back.json` and `.taskmaster/tasks/tasks_gameplay.json`.
- Add deterministic Task151 integration/closure tests:
  - `Game.Core.Tests/Tasks/Task151SplitIntegrationTests.cs`
  - `Game.Core.Tests/Tasks/Task151SplitClosureTests.cs`
- Resolve in-branch blockers encountered during closure:
  - Task111 assertion mismatch in `Game.Core.Tests/Tasks/Task111SplitIntegrationTests.cs`
  - Overlay baseline drift in `docs/architecture/overlays/PRD-SANGUO-V3/08/_index.md`

## Chapter 6 Protocol Decisions
- Recovery order executed per protocol:
  1. `resume-task --recommendation-only`
  2. `chapter6-route --recommendation-only`
  3. `inspect-run --kind pipeline --recommendation-only` only when route fields were insufficient.
- Approval sidecar state machine handled as required:
  - pending -> pause
  - approved -> fork
- Entered 6.8 only when `preferred_lane=run-6.8` with real `Needs Fix`.

## Evidence
- Clean fork pipeline run:
  - `logs/ci/2026-04-30/sc-review-pipeline-task-151-722c745586c149d88975e1f8d6d61a11`
- Local hard checks pass:
  - run_id: `cf30f879e1d9494ba7a6be1744b1bc4d`

## Risks and Mitigations
- Risk: re-running full 6.7 after deterministic closure wastes budget/time.
  - Mitigation: follow route recommendations and stop-loss signals; use narrow closure lane.
- Risk: repo-noise masks task-scope closure.
  - Mitigation: fix blockers in-branch and keep evidence paths explicit.

## Done Criteria
- Task151 acceptance refs consistent across task views and point to Task151 artifacts.
- Task151 deterministic integration/closure tests stable green.
- Chapter6 pipeline clean with no open P0/P1 Needs Fix in task scope.
- Local hard checks pass and evidence is archived under `logs/**`.
