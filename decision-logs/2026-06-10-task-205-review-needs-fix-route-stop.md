# Task 205 Review Needs Fix Route Stop

- Title: Task 205 Review Needs Fix Route Stop
- Date: 2026-06-10
- Status: accepted
- Supersedes: none
- Superseded by: `decision-logs/2026-06-10-task-205-chapter6-residual-needs-fix-3.md`
- Branch: task/T205
- Git Head: e04177f8ce452f5c9eaf52ab421ad1438f26d4b4
- Why now: Chapter 6 recovery reported reviewer Needs Fix with deterministic evidence already green and rerun guard active.
- Context: Task 205 full 6.7 pipeline completed with `pipeline_clean`, but agent review produced Needs Fix findings and recovery forbade full rerun commands.
- Decision: Stop full 6.7 and 6.7 `--resume`; require route permission before targeted 6.8.
- Consequences: Follow-up must use route/recovery sidecars and targeted reviewer closure only when allowed.
- Recovery impact: Recovery must start with `resume-task --recommendation-only`, then `chapter6-route --recommendation-only`, and respect Forbidden commands.
- Validation: Deterministic evidence was later refreshed by `sc-test --type all --task-id 205` and `build.py tdd --stage refactor`.
- Related ADRs: ADR-0005, ADR-0011, ADR-0015, ADR-0018, ADR-0021, ADR-0024, ADR-0025
- Related execution plans: `execution-plans/2026-06-10-task-205-needs-fix-followup.md`, `execution-plans/2026-06-10-task-205-chapter6-residual-followup-3.md`
- Related task id(s): `205`
- Related run id: `369166d327234023ac51d42693bef8a2`
- Related latest.json: `logs/ci/2026-06-10/sc-review-pipeline-task-205/latest.json`
- Related pipeline artifacts: `logs/ci/2026-06-10/sc-review-pipeline-task-205-369166d327234023ac51d42693bef8a2`

Date: 2026-06-10
Task: 205
Status: Needs Fix not reviewer-cleared

## Decision

Do not run a full `6.7` rerun or `6.7 --resume` for Task 205. The latest recovery fields mark deterministic evidence as green and activate the rerun guard.

Do not enter `6.8` from this turn because `chapter6-route --recommendation-only` returned `preferred_lane=inspect-first`, not `run-6.8`, even though the recommended command points at `needs-fix-fast`.

## Evidence

- `logs/ci/2026-06-10/sc-review-pipeline-task-205/latest.json`
- `logs/ci/2026-06-10/sc-review-pipeline-task-205-369166d327234023ac51d42693bef8a2/summary.json`
- `logs/ci/2026-06-10/sc-review-pipeline-task-205-369166d327234023ac51d42693bef8a2/execution-context.json`
- `logs/ci/2026-06-10/sc-review-pipeline-task-205-369166d327234023ac51d42693bef8a2/agent-review.json`
- `logs/ci/2026-06-10/sc-review-pipeline-task-205-369166d327234023ac51d42693bef8a2/repair-guide.md`
- `logs/ci/2026-06-10/sc-review-pipeline-task-205-369166d327234023ac51d42693bef8a2/run-events.jsonl`
- `logs/ci/active-tasks/task-205.active.md`

## Protocol Fields Consumed

- Latest reason: `pipeline_clean`
- Latest run type: `full`
- Latest reuse mode: `none`
- Latest artifact integrity: none
- Chapter6 next action: `inspect`
- Chapter6 can skip 6.7: `True`
- Chapter6 can go to 6.8: `True`
- Chapter6 blocked by: `rerun_guard` / `review-needs-fix`
- Approval status: `not-needed`
- Recommended command: `py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 205 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1`
- Forbidden commands: `py -3 scripts/sc/run_review_pipeline.py --task-id 205`; `py -3 scripts/sc/run_review_pipeline.py --task-id 205 --resume`

## Current Findings

Latest reviewer evidence reported P1/P2 behavior-strength issues in localization, audio, load, and runtime-status evidence. This turn added stronger deterministic evidence and reran 6.4, 6.5, and 6.6 successfully, but reviewer closure was not rerun because route stayed at `inspect-first`.
