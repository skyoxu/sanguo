# Task 208 Validate part 1 state config validation deterministic draft acceptance-test generation plan

- Title: Task 208 Validate part 1 state config validation deterministic draft acceptance-test generation plan
- Status: paused
- Branch: task/T208
- Git Head: 2b37c795bd2a329be7143dd002e254bfbe8f7592
- Goal: Control acceptance-driven test generation complexity for task 208.
- Scope: 0 missing refs across 0 test roots; seed refs: no missing refs detected
- Current step: Chapter 6 paused after 6.7 deterministic failure because approval sidecar is pending.
- Last completed step: 6.6 refactor passed (`logs/ci/2026-06-11/sc-build-tdd/summary.refactor.json`).
- Stop-loss: Do not run full 6.7, `--resume`, `--fork`, or 6.8 while `approval_status=pending`.
- Next action: Resolve the approval sidecar, then restart from `resume-task --recommendation-only` and `chapter6-route --recommendation-only`.
- Recovery command: `py -3 scripts/python/dev_cli.py resume-task --task-id 208 --recommendation-only`
- Open questions: none recorded yet
- Exit criteria: The next acceptance-driven test generation step is explicit and low-ambiguity.
- Related ADRs: none yet
- Related decision logs: `decision-logs/2026-06-11-task-208-chapter6-approval-pending-needs-fix.md`
- Related task id(s): `208`
- Related run id: `92a8a58bdb984ccdae2ffacfc592d307`
- Related latest.json: `logs/ci/2026-06-11/sc-review-pipeline-task-208/latest.json`
- Related pipeline artifacts: `logs/ci/2026-06-11/sc-review-pipeline-task-208-92a8a58bdb984ccdae2ffacfc592d307`

## Progress

- 6.1 recovery was attempted first. Initial `resume-task`, `chapter6-route`, and `inspect-run` had no latest run index.
- 6.3 created this execution plan because the TDD preflight threshold was hit (`anchor_count=8`).
- 6.4 red-first initially failed on missing `Refs:` in Task 208 acceptance items, then passed after refs were added.
- 6.5 green passed.
- 6.6 refactor initially failed on acceptance anchor binding and then passed after adding Task 208 xUnit evidence.
- 6.7 pipeline failed at `sc-test` / `gdunit-hard`.

## Current Blocker

- `Latest reason`: `step_failed:sc-test`
- `Latest run type`: `deterministic-only`
- `Latest reuse mode`: `none`
- `Latest artifact integrity`: empty / not flagged
- `Chapter6 next action`: `pause`
- `Chapter6 can skip 6.7`: `false`
- `Chapter6 can go to 6.8`: `false`
- `Chapter6 blocked by`: `approval_pending`
- `Approval required action`: `fork`
- `Approval status`: `pending`
- `Approval decision`: empty
- `Approval reason`: The repair guide includes fork so the failing artifact set can stay immutable.

## Forbidden Commands

- `py -3 scripts/sc/run_review_pipeline.py --task-id 208`
- `py -3 scripts/sc/run_review_pipeline.py --task-id 208 --resume`
- `py -3 scripts/sc/run_review_pipeline.py --task-id 208 --fork`
- `py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 208 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1`
