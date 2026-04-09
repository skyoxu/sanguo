# Project Documentation Index (sanguo)

This file is the top-level navigation for project docs.

## Start Order After Context Reset

1. `README.md`
2. `docs/agents/00-index.md`
3. `docs/agents/01-session-recovery.md`
4. `docs/PROJECT_DOCUMENTATION_INDEX.md`
5. `docs/agents/13-rag-sources-and-session-ssot.md`
6. `DELIVERY_PROFILE.md`
7. `docs/testing-framework.md`
8. `docs/agents/16-directory-responsibilities.md`
9. `docs/workflows/prototype-lane.md`
10. Newest file in `execution-plans/`
11. Newest file in `decision-logs/`
12. If available: `logs/ci/<date>/sc-review-pipeline-task-<task-id>/latest.json`

## Authoritative Sources

- Taskmaster triplet: `.taskmaster/tasks/tasks.json`, `.taskmaster/tasks/tasks_back.json`, `.taskmaster/tasks/tasks_gameplay.json`
- PRD: `.taskmaster/docs/prd.txt`, `docs/prd/**`
- ADR: `docs/adr/ADR-*.md`, `docs/architecture/ADR_INDEX_GODOT.md`
- Base architecture: `docs/architecture/base/**`
- Overlay slices: `docs/architecture/overlays/**/08/**`
- Testing rules: `docs/testing-framework.md`
- Delivery/run protocol: `DELIVERY_PROFILE.md`, `docs/workflows/run-protocol.md`, `docs/workflows/local-hard-checks.md`

## Workflow Docs

- Daily workflow (authoritative execution order): `workflow.md`
- Chapter 6 optimization guide: `docs/workflows/chapter-6-t56-optimization-guide.md`
- Upgrade guide: `docs/workflows/business-repo-upgrade-guide.md`
- Template upgrade protocol: `docs/workflows/template-upgrade-protocol.md`
- Project health dashboard: `docs/workflows/project-health-dashboard.md`
- Local hard checks: `docs/workflows/local-hard-checks.md`
- Stable entrypoint index: `docs/workflows/stable-public-entrypoints.md`
- Script entrypoint index: `docs/workflows/script-entrypoints-index.md`

## Recovery And Stop-Loss

- Canonical recovery command: `py -3 scripts/python/dev_cli.py resume-task --task-id <task-id>`
- Deep inspection command: `py -3 scripts/python/inspect_run.py --kind pipeline --task-id <task-id>`
- Recovery reading order: `docs/agents/01-session-recovery.md`
- Stable recovery/entry routing: `docs/workflows/stable-public-entrypoints.md`
- Sidecar and consumer contract: `docs/workflows/run-protocol.md`

Read these recovery signals before reopening a full Chapter 6 pipeline:

- `latest_summary_signals.reason`
- `latest_summary_signals.run_type`
- `latest_summary_signals.reuse_mode`
- `latest_summary_signals.artifact_integrity`
- `chapter6_hints.next_action`
- `chapter6_hints.blocked_by`
- `recommended_action_why` from `active-task` or project-health when available

High-value interpretation rules:

- `run_type = planned-only` or `reason = planned_only_incomplete` means the newest bundle is evidence-only, not a resumable producer run.
- `artifact_integrity` means you should fall back to the previous real producer bundle before rerunning Chapter 6.
- `recommended_action = needs-fix-fast` usually means the deterministic evidence is already good enough and you should close targeted anchors instead of paying for another full rerun.

Current stop-loss families:

- `rerun_guard`
- `llm_retry_stop_loss`
- `sc_test_retry_stop_loss`
- `waste_signals`
- `artifact_integrity`

## Evidence and Logs

- CI and local evidence: `logs/ci/<YYYY-MM-DD>/`
- Review pipeline artifact entry: `logs/ci/<YYYY-MM-DD>/sc-review-pipeline-task-<task>/latest.json`
- Local hard-check latest pointer: `logs/ci/<YYYY-MM-DD>/local-hard-checks-latest.json`
- Project-health latest pointer: `logs/ci/project-health/latest.json`
- Project-health dashboard page: `logs/ci/project-health/latest.html`
- Project-health report catalog: `logs/ci/project-health/report-catalog.latest.json`
