# Task 205 Needs Fix Follow-up

- Title: Task 205 Needs Fix Follow-up
- Status: superseded-by-residual-record
- Branch: task/T205
- Git Head: e04177f8ce452f5c9eaf52ab421ad1438f26d4b4
- Goal: Close Task 205 reviewer Needs Fix findings without violating Chapter 6 route stop-loss.
- Scope: Task 205 deterministic evidence and reviewer Needs Fix follow-up for localization, audio, load, and runtime-status evidence.
- Current step: Residual record created after deterministic verification stayed green and route remained `inspect-first`.
- Last completed step: 6.6 refactor and task-scoped deterministic validation passed on 2026-06-10.
- Stop-loss: Do not run full 6.7 or 6.7 `--resume` while Forbidden commands list those commands; do not run 6.8 unless route returns `preferred_lane=run-6.8`.
- Next action: `py -3 scripts/python/dev_cli.py chapter6-route --task-id 205 --recommendation-only`
- Recovery command: `py -3 scripts/python/dev_cli.py resume-task --task-id 205 --recommendation-only`
- Open questions: none
- Exit criteria: Route either permits targeted 6.8 and reviewer Needs Fix clears, or residual Needs Fix remains explicitly recorded for a later change.
- Related ADRs: ADR-0005, ADR-0011, ADR-0015, ADR-0018, ADR-0021, ADR-0024, ADR-0025
- Related decision logs: `decision-logs/2026-06-10-task-205-review-needs-fix-route-stop.md`, `decision-logs/2026-06-10-task-205-chapter6-residual-needs-fix-3.md`
- Related task id(s): `205`
- Related run id: `369166d327234023ac51d42693bef8a2`
- Related latest.json: `logs/ci/2026-06-10/sc-review-pipeline-task-205/latest.json`
- Related pipeline artifacts: `logs/ci/2026-06-10/sc-review-pipeline-task-205-369166d327234023ac51d42693bef8a2`

Date: 2026-06-10
Task: 205

## Current State

Task 205 has deterministic Chapter 6 evidence through 6.6 green after test and task-view evidence updates.

The latest full 6.7 pipeline is deterministic-clean but reviewer-not-clean:

- `sc-test`: ok
- `sc-acceptance-check`: ok
- `sc-llm-review`: warn / Needs Fix
- `agent-review`: needs-fix

## Completed This Turn

- Recovered state with `resume-task --recommendation-only`.
- Ran `chapter6-route --recommendation-only`.
- Ran `inspect-run --kind pipeline --recommendation-only` only after route was insufficient.
- Entered top-level Chapter 6 orchestration for the new task.
- Fixed Task 205 acceptance `Refs:` and illegal test path input.
- Added acceptance anchors to referenced test files.
- Added stronger deterministic evidence for localization, audio, load, and runtime-status reviewer concerns.
- Reran 6.4 red-first, 6.5 green, and 6.6 refactor successfully.
- Ran full 6.7 once; deterministic gates passed, reviewer returned Needs Fix.
- Stopped before 6.8 because route remained `preferred_lane=inspect-first`.

## Follow-up Entry

First re-run the route, not the full pipeline:

```powershell
py -3 scripts/python/dev_cli.py resume-task --task-id 205 --recommendation-only
py -3 scripts/python/dev_cli.py chapter6-route --task-id 205 --recommendation-only
```

Only if route changes to `preferred_lane=run-6.8`, use the recommended narrow command:

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 205 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1
```

Do not run these while forbidden by recovery fields:

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id 205
py -3 scripts/sc/run_review_pipeline.py --task-id 205 --resume
```

## Evidence Paths

- Full 6.7 pipeline: `logs/ci/2026-06-10/sc-review-pipeline-task-205-369166d327234023ac51d42693bef8a2/summary.json`
- Active task recovery: `logs/ci/active-tasks/task-205.active.md`
- Reviewer findings: `logs/ci/2026-06-10/sc-llm-review-task-205/review-code-reviewer.md`; `logs/ci/2026-06-10/sc-llm-review-task-205/review-security-auditor.md`
- Latest deterministic refactor: `logs/ci/2026-06-10/sc-build-tdd/summary.refactor.json`
- Acceptance refs: `logs/ci/2026-06-10/sc-build-tdd/acceptance-refs.json`
- Acceptance anchors: `logs/ci/2026-06-10/sc-build-tdd/acceptance-anchors.json`
