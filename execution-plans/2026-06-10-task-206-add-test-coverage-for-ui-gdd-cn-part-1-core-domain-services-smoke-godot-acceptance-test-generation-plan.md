# Task 206 Add test coverage for ui gdd cn part 1 core domain services smoke godot acceptance-test generation plan

- Title: Task 206 Add test coverage for ui gdd cn part 1 core domain services smoke godot acceptance-test generation plan
- Status: active
- Branch: task/T206
- Git Head: 309d9be1e25649647639849cea26bdddbfda5d56
- Goal: Control acceptance-driven test generation complexity for task 206.
- Scope: 0 missing refs across 0 test roots; seed refs: no missing refs detected
- Current step: Review missing acceptance refs and choose the first safe red step.
- Last completed step: n/a (new execution plan scaffold; no completed step recorded yet)
- Stop-loss: Do not start Codex test generation until the ref mix and verify mode are explicit.
- Next action: Run llm_generate_tests_from_acceptance_refs.py after confirming the sequence for missing refs.
- Recovery command: `py -3 scripts/sc/run_review_pipeline.py --task-id 206 --resume`
- Open questions: none recorded yet
- Exit criteria: The next acceptance-driven test generation step is explicit and low-ambiguity.
- Related ADRs: none yet
- Related decision logs: none yet
- Related task id(s): `206`
- Related run id: n/a (no pipeline run id linked yet)
- Related latest.json: n/a (no task-scoped latest.json pointer resolved yet)
- Related pipeline artifacts: n/a (no pipeline artifact directory resolved yet)


## 2026-06-10 Chapter 6 Stop Update

- Status: paused, approval pending.
- Last completed step: 6.7 deterministic portion passed (`sc-test=ok`, `sc-acceptance-check=ok`); `sc-llm-review` timed out with rc=124.
- Current blocking field: `chapter6_next_action=pause`, `blocked_by=approval_pending` from `inspect-run --kind pipeline --recommendation-only`.
- Latest protocol fields: `latest_reason=step_failed:sc-llm-review`, `run_type=full`, `reuse_mode=none`, `diagnostics.llm_retry_stop_loss=single_timeout_after_deterministic_green`.
- Approval fields: `required_action=fork`, `status=pending`, `decision=`, `reason=The repair guide includes fork so the failing artifact set can stay immutable.`
- Forbidden command: `py -3 scripts/sc/run_review_pipeline.py --task-id 206`.
- Evidence: `logs/ci/2026-06-10/sc-review-pipeline-task-206/latest.json`, `logs/ci/2026-06-10/sc-review-pipeline-task-206-5aa03a20a03d48c59c1701447a3d14ae/summary.json`, `logs/ci/2026-06-10/sc-review-pipeline-task-206-5aa03a20a03d48c59c1701447a3d14ae/repair-guide.json`, `logs/ci/2026-06-10/sc-review-pipeline-task-206-5aa03a20a03d48c59c1701447a3d14ae/agent-review.json`, `logs/ci/2026-06-10/sc-review-pipeline-task-206-5aa03a20a03d48c59c1701447a3d14ae/run-events.jsonl`.
- Decision log: `decision-logs/2026-06-10-task-206-approval-pending-needs-fix-stop.md`.
- Next safe command after approval changes: `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --latest logs/ci/2026-06-10/sc-review-pipeline-task-206/latest.json --recommendation-only`.
