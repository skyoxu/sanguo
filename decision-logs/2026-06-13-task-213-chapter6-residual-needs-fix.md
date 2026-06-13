# task-213-chapter6-residual-needs-fix

- Title: task-213-chapter6-residual-needs-fix
- Date: 2026-06-13
- Status: superseded
- Supersedes: none
- Superseded by: latest clean pipeline run `8a0b63533c2648f79f7f4d74174344f3` and local hard checks run `893b25739a304ab9ad141f1e45c32274`
- Branch: task/T213
- Git Head: 1ef645a6704ca47f355a52d55f6632715f11546d
- Why now: Chapter 6 routing determined that another immediate 6.8 rerun would not be cost-effective.
- Context: The latest full 6.7 pipeline is deterministic green (`reason=pipeline_clean`, `run_type=full`, `reuse_mode=none`) but reviewer output reported P1 Needs Fix for missing UI-readable refusal outcome evidence on the unaffordable build/upgrade path. A deterministic fix was added after that review: `SanguoBuildingBuildRejected` plus Task 213 xUnit coverage. The latest reviewer sidecar is therefore stale until a targeted follow-up clears it.
- Decision: Record the residual reviewer Needs Fix pointer and stop this turn before a full 6.7 rerun. Do not use the forbidden full rerun commands.
- Consequences: The residual pointer is retained as historical evidence, but latest protocol inspection now reports `failure_code=ok`, `latest_reason=pipeline_clean`, and `chapter6_next_action=continue`; no targeted 6.8 closure is currently routed.
- Recovery impact: Recovery should inspect the latest pipeline pointer first, then prefer the targeted `llm_review_needs_fix_fast.py --rerun-failing-only` command unless `chapter6-route` changes the lane or an approval sidecar blocks it.
- Validation: `py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 213 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1`
- Related ADRs: none yet
- Related execution plans: none yet
- Related task id(s): `213`
- Related run id: `a5c07e0b2d634f47944e4f64ba16b7db`
- Related latest.json: `logs/ci/2026-06-13/sc-review-pipeline-task-213/latest.json`
- Related pipeline artifacts: `logs/ci/2026-06-13/sc-review-pipeline-task-213-a5c07e0b2d634f47944e4f64ba16b7db`

## Closure Update

- Date: 2026-06-13
- Latest pipeline inspect: `failure_code=ok`, `recommended_action=continue`, `latest_reason=pipeline_clean`, `chapter6_next_action=continue`, `approval_status=not-needed`.
- Latest local hard checks: `status=ok`, hard summary `failed=0/24`.
- Current code evidence: unaffordable build/upgrade path publishes `SanguoBuildingBuildRejected` with UI-readable reason and deterministic payload fields, covered by `Task213StateResourceProgressionBuildUpgradeTests`.
