# task-68-175-refs-and-completeness-followup

- Title: task-68-175-refs-and-completeness-followup
- Status: completed
- Branch: chapter7update
- Goal: Close all residual Needs Fix items for T68-T175 from refs existence and completeness audit.
- Scope (current): `T68-T175` all residual tasks cleared
- Current step: None (closure completed).
- Last completed step: Batch D re-audit completed with `redo=0` for `T68-T175`.
- Stop-loss:
  - Do not run full-range reruns before fixing known missing refs/files.
  - Do not close tasks while deterministic refactor-stage gates remain failing.
- Exit criteria:
  - All 17 tasks pass `validate_acceptance_refs --stage refactor` and `validate_task_test_refs --require-non-empty`. (done)
  - Re-audit of `T68-T175` yields zero `redo`. (done)
- Related decision logs: `decision-logs/2026-05-02-task-68-175-refs-and-completeness-needs-fix.md`
- Related evidence:
  - `logs/ci/2026-05-02/task-audit-done/summary.json`
  - `logs/ci/2026-05-02/task-audit-done/report.md`

## Fix Batches

1. Batch A (missing files / malformed refs):
   - Tasks: `T78, T111, T129, T131, T155`
   - Actions:
     - Create or rebind missing test files for `T78, T111, T155`.
     - Normalize acceptance refs format for `T129, T131` so parser outputs valid repo-relative file paths only.
   - Validation:
     - `py -3 scripts/python/validate_acceptance_refs.py --task-id <id> --stage refactor --out logs/ci/<date>/task-audit-done/acceptance-refs.<id>.json`
     - `py -3 scripts/python/validate_task_test_refs.py --task-id <id> --require-non-empty --out logs/ci/<date>/task-audit-done/task-test-refs.<id>.json`
   - Result:
     - Completed on `2026-05-02`.
     - Added tests: `Game.Core.Tests/Tasks/Task78RewardDraftEngineTests.cs`, `Game.Core.Tests/Tasks/Task78SplitIntegrationTests.cs`, `Game.Core.Tests/Tasks/Task155FreezeChangeControlGateTests.cs`.
     - Updated task views for refs/test_refs on `T78, T111, T129, T131, T155`.

2. Batch B (Godot behavior without `.gd` refs):
   - Tasks: `T69, T156, T157, T162, T163`
   - Actions:
     - Add/attach valid `Tests.Godot/tests/**` `.gd` refs that match actual acceptance behavior.
     - If requirement is not Godot-side, rewrite acceptance/test strategy wording to remove false-positive Godot requirements.
  - Validation:
    - Same two task-level validators above.
  - Result:
    - Completed on `2026-05-02`.
    - Added task-scoped Godot refs/files for `T69, T156, T157, T162, T163`.
    - Acceptance preflight (`refs + anchors`) now passes for these tasks.

3. Batch C (deterministic gate failures without immediate missing files):
   - Tasks: `T80, T103, T112, T141, T164, T165, T173`
   - Actions:
     - Inspect per-task artifacts under `logs/ci/2026-05-02/task-audit-done/*.<id>.json` and corresponding logs.
     - Fix naming/refs mismatch and strict gate violations task-by-task.
  - Validation:
    - `py -3 scripts/python/check_test_naming.py --task-id <id> --style strict`
    - Two task-level validators above.
  - Result:
    - Completed on `2026-05-02`.
    - Fixed refs/test_refs and naming constraints for `T80, T103, T112, T141, T164, T165, T173`.
    - Added task-scoped Godot alias files for `T164, T165, T173` and removed non-test/workflow refs from acceptance.

4. Batch D (range re-audit):
   - Action:
     - Re-run full range audit after A/B/C complete.
  - Validation:
    - `py -3 scripts/python/audit_done_tasks_semantic.py --task-ids 68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175`
    - Expectation: `redo=0`.
  - Result:
    - Completed on `2026-05-02`.
    - Output: `logs/ci/2026-05-02/task-audit-done/summary.json`
    - Final status: `TASK_AUDIT_DONE status=ok keep=108 redo=0`.
