# task-112-chapter6-residual-needs-fix

- Title: task-112-chapter6-residual-needs-fix
- Date: 2026-05-01
- Status: accepted
- Supersedes: none
- Superseded by: `decision-logs/2026-05-01-task-112-chapter6-residual-needs-fix-2.md`
- Branch: task/T112
- Git Head: 124725c80a825748bc20cd9662725d2319413f2e
- Why now: Chapter 6 route entered stop-loss posture and reported active P1 reviewer finding before final narrow-loop convergence.
- Context: Route summary preferred `record-residual`; pipeline evidence included stop-loss signals (`planned_only_incomplete`, `repo-noise`) and an unresolved P1 at this checkpoint.
- Decision: Do not force a full 6.7 rerun; record residual and continue with protocol-compliant follow-up planning.
- Consequences: Residual is explicitly traceable and can be resumed without replaying high-cost non-deterministic lanes.
- Recovery impact: Recovery must consume route/artifact evidence first and only reopen 6.8 under lane and Needs Fix conditions.
- Validation: `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 112 --recommendation-only`
- Related ADRs: ADR-0003, ADR-0004, ADR-0005, ADR-0010, ADR-0020
- Related execution plans: `execution-plans/2026-05-01-task-112-chapter6-residual-followup.md`
- Related task id(s): `112`
- Related run id: `run-20260501-101759`
- Related latest.json: `logs/ci/2026-05-01/sc-review-pipeline-task-112/latest.json`
- Related pipeline artifacts: `logs/ci/2026-05-01/sc-review-pipeline-task-112/run-20260501-101759`

## Evidence
- `logs/ci/2026-05-01/sc-review-pipeline-task-112/run-20260501-101759/summary.json`
- `logs/ci/2026-05-01/sc-review-pipeline-task-112/run-20260501-101759/repair-guide.json`
- `logs/ci/2026-05-01/sc-review-pipeline-task-112/run-20260501-101759/run-events.jsonl`
