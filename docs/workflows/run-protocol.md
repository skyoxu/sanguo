# Harness Run Protocol

## Purpose

This document defines the local file-protocol harness used by `scripts/sc/run_review_pipeline.py` and the repo-scoped `py -3 scripts/python/dev_cli.py run-local-hard-checks` wrapper.

It is the human-readable contract for durable local runs. The executable schemas remain under `scripts/sc/schemas/` and must not be duplicated into `docs/`.

## Scope

This protocol is intentionally local and file-backed:

- no JSON-RPC server
- no daemon runtime
- no multi-client session coordination
- no SSE/Web reconnect transport

The goal is deterministic local recovery, not platform-grade remote orchestration.

## SSoT

- Producer entry: `scripts/sc/run_review_pipeline.py`
- Repo-scoped producer entry: `scripts/python/local_hard_checks_harness.py`
- Stable CLI entry for repo-scoped runs: `py -3 scripts/python/dev_cli.py run-local-hard-checks`
- Reviewer rebuild entry: `scripts/sc/agent_to_agent_review.py`
- Local inspect entry: `scripts/python/inspect_run.py`
- Task-scoped sidecar schemas: `sc-review-execution-context.schema.json`, `sc-review-repair-guide.schema.json`, `sc-review-latest-index.schema.json`
- Repo-scoped sidecar schemas: `sc-local-hard-checks-execution-context.schema.json`, `sc-local-hard-checks-repair-guide.schema.json`, `sc-local-hard-checks-latest-index.schema.json`
- Shared failure taxonomy: `scripts/sc/_failure_taxonomy.py`
- Run-event schema: `scripts/sc/schemas/sc-run-event.schema.json`
- Harness-capabilities schema: `scripts/sc/schemas/sc-harness-capabilities.schema.json`
- Repo-scoped local-hard-checks summary schema: `scripts/sc/schemas/sc-local-hard-checks-summary.schema.json`
- Example event stream: `docs/workflows/examples/sc-run-events.example.jsonl`

## Core Model

Conceptually, the harness uses these local concepts:

- `task scope`: `logs/ci/<date>/sc-review-pipeline-task-<task>/latest.json`
- `repo scope`: `logs/ci/<date>/local-hard-checks-latest.json`
- `run`: one artifact directory identified by `run_id`
- `turn`: one lifecycle transition such as `run_started`, `run_resumed`, `run_forked`, `run_completed`, or `run_aborted`
- `item`: one step transition, sidecar file, approval artifact, or reviewer artifact

This is protocolized local orchestration, not RPC.

## Artifact Layout

For one task-scoped review run, the producer writes:

- `logs/ci/<date>/sc-review-pipeline-task-<task>-<run_id>/summary.json`
- `logs/ci/<date>/sc-review-pipeline-task-<task>-<run_id>/execution-context.json`
- `logs/ci/<date>/sc-review-pipeline-task-<task>-<run_id>/repair-guide.json`
- `logs/ci/<date>/sc-review-pipeline-task-<task>-<run_id>/repair-guide.md`
- `logs/ci/<date>/sc-review-pipeline-task-<task>-<run_id>/marathon-state.json`
- `logs/ci/<date>/sc-review-pipeline-task-<task>-<run_id>/run-events.jsonl`
- `logs/ci/<date>/sc-review-pipeline-task-<task>-<run_id>/harness-capabilities.json`
- `logs/ci/<date>/sc-review-pipeline-task-<task>-<run_id>/run_id.txt`

For one repo-scoped local hard-check run, the producer writes:

- `logs/ci/<date>/local-hard-checks-<run_id>/summary.json`
- `logs/ci/<date>/local-hard-checks-<run_id>/execution-context.json`
- `logs/ci/<date>/local-hard-checks-<run_id>/repair-guide.json`
- `logs/ci/<date>/local-hard-checks-<run_id>/repair-guide.md`
- `logs/ci/<date>/local-hard-checks-<run_id>/run-events.jsonl`
- `logs/ci/<date>/local-hard-checks-<run_id>/harness-capabilities.json`
- `logs/ci/<date>/local-hard-checks-<run_id>/run_id.txt`
- `logs/ci/<date>/local-hard-checks-<run_id>/<step>.log`

Optional sidecars for task-scoped review runs:

- `approval-request.json`
- `approval-response.json`
- `agent-review.json`
- `agent-review.md`

Task-scoped pointer:

- `logs/ci/<date>/sc-review-pipeline-task-<task>/latest.json`

Repo-scoped pointer:

- `logs/ci/<date>/local-hard-checks-latest.json`

## Sidecar Roles

| Artifact | Owner | Role |
| --- | --- | --- |
| `summary.json` | producer pipeline | canonical run status and step list |
| `execution-context.json` | producer pipeline | git state, profile state, recovery pointers, latest reviewer recommendation snapshot |
| `repair-guide.json` | producer pipeline | machine-readable next repair action |
| `repair-guide.md` | producer pipeline | human-readable repair instructions |
| `marathon-state.json` | producer pipeline | checkpoint, retry, wall-time, refresh, fork metadata; task-scoped review runs only |
| `run-events.jsonl` | producer pipeline | append-only lifecycle and step timeline |
| `harness-capabilities.json` | producer pipeline | machine-readable protocol capabilities |
| `approval-request.json` | producer pipeline | soft approval request for risky fork/recovery flows; task-scoped review runs only |
| `approval-response.json` | operator or follow-up tool | soft approval response envelope; task-scoped review runs only |
| `agent-review.json` | reviewer sidecar | normalized reviewer verdict and recommended action; task-scoped review runs only |
| `agent-review.md` | reviewer sidecar | human-readable reviewer summary; task-scoped review runs only |
| `latest.json` | producer pipeline and reviewer sidecar | task-scoped pointer to newest run artifacts, including recovery-facing `reason`, `run_type`, `reuse_mode`, `artifact_integrity`, and selected diagnostics |
| `local-hard-checks-latest.json` | repo-scoped producer pipeline | repo-scoped pointer to newest local hard-check run artifacts |

## Consumer-Driven Sidecar Contract

- `scripts/sc/agent_to_agent_review.py` consumes and validates task-scoped `latest.json`, `execution-context.json`, and `repair-guide.json` before trusting reviewer-side recovery decisions.
- `scripts/python/_recovery_doc_scaffold.py` consumes and validates task-scoped `latest.json` before backfilling `execution-plans/` and `decision-logs/`.
- `scripts/python/inspect_run.py` consumes `latest.json`, `summary.json`, `execution-context.json`, and `repair-guide.json` for both task-scoped review runs and repo-scoped local hard checks.
- `scripts/python/resume_task.py` consumes `inspect_run.py` output plus `active-task` sidecars, and now derives a recovery-facing stop-loss note from `latest_summary_signals` / `chapter6_hints` before recommending another `6.7`.
- `summary.json` remains producer-owned. Consumer contracts should only require fields they actually read.
- New shared sidecar fields are not allowed unless a real consumer needs them and the executable schema plus regression coverage are updated in the same change.

## Event Stream Contract

`run-events.jsonl` is append-only. Each line must satisfy `scripts/sc/schemas/sc-run-event.schema.json`.

Required fields:

- `schema_version`
- `ts`
- `event`
- `task_id`
- `run_id`
- `delivery_profile`
- `security_profile`
- `step_name`
- `status`
- `details`

Field rules:

- `step_name` may be `null` for run-level events
- `status` may be `null` for run-level events
- `details` is always an object and may be empty
- `task_id` and `run_id` are strings, even when the task number is numeric

Common event names:

- `run_started`
- `run_resumed`
- `run_forked`
- `run_completed`
- `run_aborted`
- `wall_time_exceeded`
- `step_planned`
- `step_skipped`
- `step_completed`
- `step_failed`
- `approval_updated` when approval state changes

The protocol does not currently reserve a transport-level request id. Correlation happens through `task_id`, `run_id`, and artifact paths.

## Recovery Actions

`harness-capabilities.json` declares the currently supported recovery actions:

- `resume`
- `refresh`
- `fork`
- `abort`

Interpretation:

- `resume`: continue the same run artifact set
- `refresh`: same run intent, but context should be refreshed before continuing
- `fork`: create a clean continuation run, optionally gated by soft approval
- `abort`: mark the run as intentionally stopped

## Consumer Read Order

When recovering after context loss, read in this order:

1. `latest.json`
2. `summary.json`
3. `execution-context.json`
4. `repair-guide.json` or `repair-guide.md`
5. `agent-review.json` if present
6. `run-events.jsonl` if lifecycle sequencing is still unclear
7. approval files only when the recovery action is `fork`

Do not scrape console logs first if these files already exist.
Before deciding to reopen `6.7`, read `latest.json.reason`, `latest.json.run_type`, `latest.json.reuse_mode`, `latest.json.artifact_integrity`, and the stop-loss diagnostics that consumers surface as `latest_summary_signals` / `chapter6_hints`, especially:

- `rerun_guard`
- `llm_retry_stop_loss`
- `sc_test_retry_stop_loss`
- `waste_signals`
- `artifact_integrity`
- `recent_failure_summary`

If recovery already shows `run_type = planned-only`, `reason = planned_only_incomplete`, or `chapter6_hints.blocked_by = artifact_integrity`, treat that bundle as evidence only and fall back to the previous real producer run before reopening `6.7` or `6.8`.
If recovery readers also expose `recommended_action_why`, treat it as the shortest explanation of whether the next move is `inspect`, `resume`, or `needs-fix-fast`; `needs-fix-fast` means targeted closure should happen before any full rerun.

## Local Inspect Entry

Use `scripts/python/inspect_run.py` as the stable local replay/inspect entrypoint:

- Task-scoped latest pointer: `py -3 scripts/python/inspect_run.py --task-id <task-id>`
- Explicit task-scoped bundle: `py -3 scripts/python/inspect_run.py --latest logs/ci/<date>/sc-review-pipeline-task-<task-id>/latest.json`
- Explicit repo-scoped bundle: `py -3 scripts/python/inspect_run.py --kind local-hard-checks --latest logs/ci/<date>/local-hard-checks-latest.json`
- Persist one stable inspection payload: `py -3 scripts/python/inspect_run.py --task-id <task-id> --out-json logs/ci/<date>/inspect-task-<task-id>.json`

The command returns `0` only when the inspected run is fully usable for recovery. Any broken pointer, schema drift, or failed step returns non-zero and emits one stable JSON payload.
When `inspect_run.py --task-id <task-id>` resolves the latest task-scoped bundle automatically, it now skips both dry-run-only pointers and newer `planned-only` terminal bundles, then falls back to the newest real producer run.
For task-scoped review runs, that payload now also exposes:

- `latest_summary_signals.reason`
- `latest_summary_signals.run_type`
- `latest_summary_signals.reuse_mode`
- `latest_summary_signals.artifact_integrity`
- `latest_summary_signals.diagnostics_keys`
- `chapter6_hints.next_action`
- `chapter6_hints.blocked_by`
- `recent_failure_summary.latest_failure_family`
- `recent_failure_summary.same_family_count`
- `recent_failure_summary.stop_full_rerun_recommended`

## Failure Taxonomy

`inspect_run.py` normalizes run state into one of these codes:

- `ok`: the latest pointer and required sidecars are valid, and no blocking repair is required
- `step-failed`: the producer run failed at a concrete step
- `review-needs-fix`: the producer run completed but follow-up review work is still required
- `artifact-missing`: one or more required sidecars are missing
- `artifact-incomplete`: `latest.json` says `ok` but the producer bundle still has no `run_completed` event
- `planned-only-incomplete`: the newest recoverable pointer is only a planned-only terminal bundle and must not be used as a producer-run recovery baseline
- `schema-invalid`: a consumed sidecar drifted from the executable contract
- `stale-latest`: `latest.json` points to a moved or missing artifact directory
- `aborted`: the run was intentionally stopped

## Design Rules

- `summary.json` stays producer-owned and must not be rewritten by reviewer sidecars.
- Recovery metadata belongs in sidecars, not in git-tracked heartbeat files.
- `latest.json` is the task-scoped entry point; consumers should not guess the newest run by directory scanning first.
- Stop-loss semantics used by recovery (`rerun_guard`, `llm_retry_stop_loss`, `sc_test_retry_stop_loss`, `waste_signals`, `recent_failure_summary`, `artifact_integrity`, planned-only terminal bundle handling) must be migrated together across producer, consumer, schema fallback, and docs; do not update only one layer.
- Schemas under `scripts/sc/schemas/` are executable SSoT; docs explain them but do not duplicate them.

## Protocol Budget

- `additionalProperties: false` on shared sidecar schemas is intentional and must stay on.
- Do not add a new shared sidecar file or field unless the same change also adds a named consumer, a schema update under `scripts/sc/schemas/`, a fallback-validator update, and regression coverage under `scripts/sc/tests/`.
- If a producer-only field has no real consumer yet, keep it out of the shared sidecar contract.

## Minimal Validation

- Validate event lines against `scripts/sc/schemas/sc-run-event.schema.json`
- Validate capabilities against `scripts/sc/schemas/sc-harness-capabilities.schema.json`
- Validate consumed sidecars through `scripts/sc/_artifact_schema.py` in consumer paths such as `agent_to_agent_review.py`, `_recovery_doc_scaffold.py`, and `inspect_run.py`
- Keep `docs/workflows/examples/sc-run-events.example.jsonl` aligned with the executable schema
- Keep `scripts/sc/tests/test_pipeline_sidecar_protocol.py` green after protocol changes
- Keep `scripts/sc/tests/test_run_artifact_schema_and_inspect.py` green after sidecar contract changes
