# task-112-chapter6-residual-followup

- Title: task-112-chapter6-residual-followup
- Status: superseded
- Branch: task/T112
- Git Head: 124725c80a825748bc20cd9662725d2319413f2e
- Goal: Close remaining P1 in Chapter 6 under protocol-compliant narrow path.
- Scope: Follow-up actions after first residual checkpoint for Task 112.
- Current step: Follow-up plan captured and superseded by second-loop follow-up.
- Last completed step: First residual checkpoint recorded and routed to continuation.
- Stop-loss: Respect stop-loss signals and avoid blind full 6.7 reruns.
- Next action: `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 112 --recommendation-only`
- Recovery command: `py -3 scripts/python/dev_cli.py chapter6-route --task-id 112 --recommendation-only`
- Open questions: none
- Exit criteria: No P0/P1 in effective summary, with residual documentation when medium/low remains.
- Related ADRs: ADR-0003, ADR-0004, ADR-0005, ADR-0010, ADR-0020
- Related decision logs: `decision-logs/2026-05-01-task-112-chapter6-residual-needs-fix.md`
- Related task id(s): `112`
- Related run id: `run-20260501-101759`
- Related latest.json: `logs/ci/2026-05-01/sc-review-pipeline-task-112/latest.json`
- Related pipeline artifacts: `logs/ci/2026-05-01/sc-review-pipeline-task-112/run-20260501-101759`

## Planned Steps
1. Resume by protocol order:
   - `resume-task --task-id 112 --recommendation-only`
   - `chapter6-route --task-id 112 --recommendation-only`
   - `inspect-run --task-id 112 --kind pipeline --recommendation-only` only if still ambiguous.
2. If approval sidecar is `pending`, pause and wait.
3. If approval sidecar is `approved`, run `fork-task` with approval payload.
4. Re-run route and follow `preferred_lane` strictly.
5. Only enter 6.8 when lane is `run-6.8` and there is real `Needs Fix`.
