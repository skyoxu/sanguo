# task-112-chapter6-residual-needs-fix-2

- Title: task-112-chapter6-residual-needs-fix-2
- Date: 2026-05-01
- Status: accepted
- Supersedes: `decision-logs/2026-05-01-task-112-chapter6-residual-needs-fix.md`
- Superseded by: none
- Branch: task/T112
- Git Head: 124725c80a825748bc20cd9662725d2319413f2e
- Why now: A second checkpoint was required because route status remained non-final before entering the next narrow convergence loop.
- Context: After first residual recording, Chapter 6 still required protocol-compliant continuation and sidecar-state-driven progression.
- Decision: Keep strict protocol order, record a second residual checkpoint, and continue only through approved sidecar transitions.
- Consequences: Preserves explicit audit trail between first and second residual checkpoints before final convergence.
- Recovery impact: Resume logic can pick the latest residual snapshot and avoid ambiguous checkpoint selection.
- Validation: `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 112 --recommendation-only`
- Related ADRs: ADR-0003, ADR-0004, ADR-0005, ADR-0010, ADR-0020
- Related execution plans: `execution-plans/2026-05-01-task-112-chapter6-residual-followup-2.md`
- Related task id(s): `112`
- Related run id: `run-20260501-104923`
- Related latest.json: `logs/ci/2026-05-01/sc-review-pipeline-task-112/latest.json`
- Related pipeline artifacts: `logs/ci/2026-05-01/sc-review-pipeline-task-112/run-20260501-104923`

## Evidence
- `logs/ci/2026-05-01/sc-review-pipeline-task-112/run-20260501-104923/summary.json`
- `logs/ci/2026-05-01/sc-review-pipeline-task-112/run-20260501-104923/repair-guide.json`
- `logs/ci/2026-05-01/sc-review-pipeline-task-112/run-20260501-104923/run-events.jsonl`
