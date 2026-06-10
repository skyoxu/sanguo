# Task 206 Approval-Pending Needs Fix Stop

- Title: task-206-approval-pending-needs-fix-stop
- Date: 2026-06-10
- Status: accepted
- Supersedes: none
- Superseded by: `decision-logs/2026-06-10-task-206-chapter6-residual-needs-fix.md`
- Branch: task/T206
- Git Head: 28d2dc96adf8b0e29394f746075ab37d11f4c71d
- Why now: Chapter 6 inspect reported approval-pending state after the review pipeline produced Needs Fix findings.
- Context: `inspect-run --kind pipeline --recommendation-only` reported `chapter6_next_action=pause`, `blocked_by=approval_pending`, `approval_status=pending`, allowed actions `inspect | pause`, and blocked actions `fork | resume | rerun`.
- Decision: Stop Chapter 6 execution at approval-pending Needs Fix state until the approval sidecar is resolved.
- Consequences: Do not run 6.8, resume, fork, or rerun while approval remains pending.
- Recovery impact: After approval state changes, rerun the inspect command and follow the reported transition: `approved -> fork`, `denied -> resume`, `invalid/mismatched -> inspect`.
- Validation: `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --latest logs/ci/2026-06-10/sc-review-pipeline-task-206/latest.json --recommendation-only`
- Related ADRs: none yet
- Related execution plans: none yet
- Related task id(s): `206`
- Related run id: `5aa03a20a03d48c59c1701447a3d14ae`
- Related latest.json: `logs/ci/2026-06-10/sc-review-pipeline-task-206/latest.json`
- Related pipeline artifacts: `logs/ci/2026-06-10/sc-review-pipeline-task-206-5aa03a20a03d48c59c1701447a3d14ae`
- Task: 206
- Reason: `inspect-run --kind pipeline --recommendation-only` reported `chapter6_next_action=pause`, `blocked_by=approval_pending`, `approval_status=pending`, allowed actions `inspect | pause`, and blocked actions `fork | resume | rerun`.
- Latest reason: `step_failed:sc-llm-review`
- Latest run type: `full`
- Latest reuse mode: `none`
- Artifact integrity: no artifact-integrity stop was reported in `latest_summary_signals`.
- Stop-loss: `diagnostics.llm_retry_stop_loss.kind=single_timeout_after_deterministic_green`; deterministic `sc-test` and `sc-acceptance-check` are already green.
- Approval required action: `fork`
- Approval status: `pending`
- Approval decision: empty
- Approval reason: The repair guide includes fork so the failing artifact set can stay immutable.
- Forbidden command: `py -3 scripts/sc/run_review_pipeline.py --task-id 206`

## Evidence

- Single-task summary: `logs/ci/2026-06-10/single-task-chapter6-task-206/summary.json`
- Pipeline latest: `logs/ci/2026-06-10/sc-review-pipeline-task-206/latest.json`
- Pipeline summary: `logs/ci/2026-06-10/sc-review-pipeline-task-206-5aa03a20a03d48c59c1701447a3d14ae/summary.json`
- Repair guide: `logs/ci/2026-06-10/sc-review-pipeline-task-206-5aa03a20a03d48c59c1701447a3d14ae/repair-guide.json`
- Agent review: `logs/ci/2026-06-10/sc-review-pipeline-task-206-5aa03a20a03d48c59c1701447a3d14ae/agent-review.json`
- Run events: `logs/ci/2026-06-10/sc-review-pipeline-task-206-5aa03a20a03d48c59c1701447a3d14ae/run-events.jsonl`
- Approval request: `logs/ci/2026-06-10/sc-review-pipeline-task-206-5aa03a20a03d48c59c1701447a3d14ae/approval-request.json`

## Next Entry

Do not run 6.8, resume, fork, or rerun while approval remains pending. After approval state changes, rerun:

```powershell
py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --latest logs/ci/2026-06-10/sc-review-pipeline-task-206/latest.json --recommendation-only
```

Then follow the reported approval transition: `approved -> fork`, `denied -> resume`, `invalid/mismatched -> inspect`.
