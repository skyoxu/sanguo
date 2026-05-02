# task-68-175-refs-and-completeness-needs-fix

- Title: task-68-175-refs-and-completeness-needs-fix
- Date: 2026-05-02
- Status: completed
- Supersedes: none
- Superseded by: none
- Branch: chapter7update
- Git Head: 9c33f680331f
- Why now: A full audit was requested for Taskmaster range T68-T175 to verify test refs path existence and implementation completeness signals.
- Context: The deterministic and semantic audit pipeline found residual Needs Fix tasks that should not be treated as complete without targeted follow-up.
- Decision: Record all residual Needs Fix items first, then execute a narrow fix plan by category instead of broad reruns.
- Consequences: Recovery and CI triage should prioritize task-level targeted fixes for this range and avoid high-cost blanket reruns.
- Recovery impact: Resume workflows should consume this decision and related execution plan as the primary fix entrypoint for T68-T175.
- Validation: `py -3 scripts/python/audit_done_tasks_semantic.py --task-ids 68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175`
- Related ADRs: none yet
- Related execution plans: `execution-plans/2026-05-02-task-68-175-refs-and-completeness-followup.md`
- Related task id(s): `68-175`
- Related run id: `25255857177`
- Related latest.json: `logs/ci/2026-05-02/sc-review-pipeline-task-175/latest.json` (artifact reference, may not exist locally)
- Related pipeline artifacts: `logs/ci/2026-05-02/task-audit-done/summary.json`, `logs/ci/2026-05-02/task-audit-done/report.md`

## Recorded Residual Needs Fix

- Range scanned: `T68-T175` (108 tasks)
- Keep done: `91`
- Needs Fix (`redo`): `17`
- Needs Fix task ids:
  - `69, 78, 80, 103, 111, 112, 129, 131, 141, 155, 156, 157, 162, 163, 164, 165, 173`

## Closure Update (2026-05-02)

- Follow-up execution plan completed: `execution-plans/2026-05-02-task-68-175-refs-and-completeness-followup.md`
- Deterministic validators now pass for all previously listed residual tasks.
- Full range re-audit output confirms closure:
  - `logs/ci/2026-05-02/task-audit-done/summary.json`
  - Result: `keep=108`, `redo=0`

## Category Snapshot

- Missing or malformed refs/file targets:
  - `T78`: `Game.Core.Tests/Tasks/Task78RewardDraftEngineTests.cs`, `Game.Core.Tests/Tasks/Task78SplitIntegrationTests.cs`
  - `T111`: `Game.Core.Tests/Tasks/Task149V3Tests.cs`, `Game.Core.Tests/Tasks/Task150V3Tests.cs`
  - `T129`: malformed tokens from acceptance refs parsing: `(anchor:`, `ACC:T129.1)`, `ACC:T129.2)`
  - `T131`: malformed tokens from acceptance refs parsing: `(anchor:`, `ACC:T131.1)`
  - `T155`: `Game.Core.Tests/Tasks/Task155FreezeChangeControlGateTests.cs`
- Godot behavior mentioned but no `.gd` refs:
  - `T69, T156, T157, T162, T163`
- Deterministic refactor-stage gates failed:
  - `T78, T80, T103, T111, T112, T129, T131, T141, T155, T164, T165, T173`
