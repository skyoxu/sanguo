# Harness Run Protocol

## Purpose

This document defines the local file-protocol harness used by `scripts/sc/run_review_pipeline.py` and the repo-scoped `py -3 scripts/python/dev_cli.py run-local-hard-checks` wrapper.

It is the human-readable contract for durable local runs. The executable schemas remain under `scripts/sc/schemas/` and must not be duplicated into `docs/`.

Golden examples for these contracts are indexed in `docs/workflows/examples/README.md`.

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
- Stable local inspect entry: `py -3 scripts/python/dev_cli.py inspect-run --kind <kind>`
- Stable Chapter 6 route entry: `py -3 scripts/python/dev_cli.py chapter6-route --task-id <id> --recommendation-only`
- Underlying inspect implementation: `scripts/python/inspect_run.py`
- Task-scoped sidecar schemas: `sc-review-execution-context.schema.json`, `sc-review-repair-guide.schema.json`, `sc-review-latest-index.schema.json`, `sc-active-task.schema.json`
- Recovery compact schema: `scripts/sc/schemas/sc-recovery-compact.schema.json` for the shared `inspect-run --recommendation-only` / `resume-task --recommendation-only` JSON surface
- Project-health dashboard schema: `scripts/sc/schemas/sc-project-health-dashboard.schema.json` for `logs/ci/project-health/latest.json`
- Project-health report catalog schema: `scripts/sc/schemas/sc-project-health-report-catalog.schema.json` for `logs/ci/project-health/report-catalog.latest.json`
- Project-health server schema: `scripts/sc/schemas/sc-project-health-server.schema.json` for `logs/ci/project-health/server.json`
- Project-health latest-record schema: `scripts/sc/schemas/sc-project-health-record.schema.json` for `logs/ci/project-health/*.latest.json`
- Project-health aggregate schema: `scripts/sc/schemas/sc-project-health-scan.schema.json` for the `_project_health_checks.project_health_scan()` payload
- The persisted aggregate lives at `logs/ci/project-health/project-health-scan.latest.json`; repo-scoped consumers such as `local-hard-checks` should point `summary_file` at this artifact instead of the dashboard `latest.json`.
- Repo-scoped sidecar schemas: `sc-local-hard-checks-execution-context.schema.json`, `sc-local-hard-checks-repair-guide.schema.json`, `sc-local-hard-checks-latest-index.schema.json`
- Shared failure taxonomy: `scripts/sc/_failure_taxonomy.py`
- Run-event schema: `scripts/sc/schemas/sc-run-event.schema.json`
- Harness-capabilities schema: `scripts/sc/schemas/sc-harness-capabilities.schema.json`
- Repo-scoped local-hard-checks summary schema: `scripts/sc/schemas/sc-local-hard-checks-summary.schema.json`
- Example event stream: `docs/workflows/examples/sc-run-events.example.jsonl`
  - The example intentionally spans two turns and keeps a sidecar sync after `run_completed`, so consumers can test `previous_turn` / `turn_family_delta` logic and avoid assuming the terminal run event is the last line in the file.
- Example approval request: `docs/workflows/examples/sc-approval-request.example.json`
- Example approval response: `docs/workflows/examples/sc-approval-response.example.json`
- Example compact recovery output: `docs/workflows/examples/sc-recovery-compact.example.json`
- Example resume-task compact recommendation: `docs/workflows/examples/sc-resume-task-compact.example.json`
- Example resume-task compact stdout: `docs/workflows/examples/sc-resume-task-compact.stdout.example.txt`
- Example Chapter 6 route compact recommendation: `docs/workflows/examples/sc-chapter6-route-compact.example.json`
- Example Chapter 6 route compact stdout: `docs/workflows/examples/sc-chapter6-route-compact.stdout.example.txt`
- Example pipeline inspect output: `docs/workflows/examples/sc-pipeline-inspect.example.json`
- Example pipeline compact recommendation: `docs/workflows/examples/sc-pipeline-compact.example.json`
- Example pipeline CLI stdout: `docs/workflows/examples/sc-pipeline-inspect.stdout.example.txt`
- Example pipeline compact stdout: `docs/workflows/examples/sc-pipeline-compact.stdout.example.txt`
- Example active-task sidecar: `docs/workflows/examples/sc-active-task.example.json`
- Example active-task markdown: `docs/workflows/examples/sc-active-task.example.md`
- Example project-health server sidecar: `docs/workflows/examples/sc-project-health-server.example.json`
- Example project-health latest markdown: `docs/workflows/examples/sc-project-health-record.example.md`
- Example project-health latest JSON records: `docs/workflows/examples/sc-project-health-detect-project-stage.example.json`, `docs/workflows/examples/sc-project-health-doctor-project.example.json`, `docs/workflows/examples/sc-project-health-check-directory-boundaries.example.json`
- Example project-health scan aggregate: `docs/workflows/examples/sc-project-health-scan.example.json`
- Example project-health CLI stdout: `docs/workflows/examples/sc-project-health-scan.stdout.example.txt`, `docs/workflows/examples/sc-project-health-scan-ci-fail.stdout.example.txt`, `docs/workflows/examples/sc-project-health-server.stdout.example.txt`, `docs/workflows/examples/sc-project-health-server-ci-fail.stdout.example.txt`
- Example repo-scoped local-hard-checks latest index: `docs/workflows/examples/sc-local-hard-checks-latest-index.example.json`
- Example repo-scoped local-hard-checks execution context: `docs/workflows/examples/sc-local-hard-checks-execution-context.example.json`
- Example repo-scoped local-hard-checks repair guide: `docs/workflows/examples/sc-local-hard-checks-repair-guide.example.json`
- Example repo-scoped local-hard-checks repair markdown: `docs/workflows/examples/sc-local-hard-checks-repair-guide.example.md`
- Example repo-scoped local-hard-checks inspect output: `docs/workflows/examples/sc-local-hard-checks-inspect.example.json`
- Example repo-scoped local-hard-checks compact recommendation: `docs/workflows/examples/sc-local-hard-checks-compact.example.json`
- Example repo-scoped local-hard-checks CLI stdout: `docs/workflows/examples/sc-local-hard-checks-inspect.stdout.example.txt`
- Example repo-scoped local-hard-checks compact stdout: `docs/workflows/examples/sc-local-hard-checks-compact.stdout.example.txt`

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
| `approval-request.json` | producer pipeline | soft approval request for risky fork/recovery flows; pending fork requests also carry an explicit recovery contract (`recommended_action = pause`, plus `allowed_actions` / `blocked_actions`); task-scoped review runs only |
| `approval-response.json` | operator or follow-up tool | approval decision envelope; approved or denied fork responses may also carry `recommended_action` / `allowed_actions` / `blocked_actions`, and recovery consumers validate that contract against the current request before allowing `resume` / `fork`; task-scoped review runs only |
| `agent-review.json` | reviewer sidecar | normalized reviewer verdict and recommended action; task-scoped review runs only |
| `agent-review.md` | reviewer sidecar | human-readable reviewer summary; task-scoped review runs only |
| `latest.json` | producer pipeline and reviewer sidecar | task-scoped pointer to newest run artifacts, including recovery-facing `reason`, `run_type`, `reuse_mode`, `artifact_integrity`, and selected diagnostics |
| `local-hard-checks-latest.json` | repo-scoped producer pipeline | repo-scoped pointer to newest local hard-check run artifacts |

## Consumer-Driven Sidecar Contract

- Approval consumers (`inspect_run.py`, `resume_task.py`, and `run_review_pipeline.py`) now treat `pending`, `approved`, `denied`, `invalid`, and `mismatched` as executable recovery states rather than soft hints only.
- `approval-request.json` now carries the pending-side recovery contract (`pause`, `allowed_actions`, `blocked_actions`) so a paused fork request is protocolized before any response file exists.
- `approval-response.json` may now carry an explicit recovery contract (`recommended_action`, `allowed_actions`, `blocked_actions`) for approved or denied fork requests; consumers validate that contract instead of treating the response as a free-form note.
- `scripts/sc/agent_to_agent_review.py` consumes and validates task-scoped `latest.json`, `execution-context.json`, and `repair-guide.json` before trusting reviewer-side recovery decisions.
- `scripts/python/_recovery_doc_scaffold.py` consumes and validates task-scoped `latest.json` before backfilling `execution-plans/` and `decision-logs/`.
- `py -3 scripts/python/dev_cli.py inspect-run --kind <kind>` wraps `scripts/python/inspect_run.py` and consumes `latest.json`, `summary.json`, `execution-context.json`, and `repair-guide.json` for both task-scoped review runs and repo-scoped local hard checks.
- The compact `inspect-run --recommendation-only` surface is no longer limited to action text: it now exposes the latest run turn (`latest_turn`, `turn_count`) and the resolved approval route (`approval_recommended_action`, `approval_allowed_actions`, `approval_blocked_actions`) so consumers can make a safe go/no-go decision without printing the full payload.
- `resume-task --recommendation-only` intentionally reuses the same compact recovery field set as `inspect-run --recommendation-only`; the short CLI surfaces are expected to stay schema-aligned even though one is inspection-only and the other is recovery-oriented.
- `scripts/python/resume_task.py` consumes `inspect_run.py` output plus `active-task` sidecars, and now derives a recovery-facing stop-loss note from `latest_summary_signals` / `chapter6_hints` before recommending another `6.7`.
- `logs/ci/active-tasks/task-<id>.active.{json,md}` and project-health now consume the canonical `run-events` taxonomy (`turn_id`, `turn_seq`, `item_kind`, `item_id`, `event_family`) plus the resolved approval contract from `execution-context.json`, so the shortest recovery surfaces expose the same `pause` / `fork` / `resume` routing state as the heavier inspection entrypoints.
- Those same consumers also compare the latest two turns when `turn_count >= 2`, surfacing `previous_turn`, `turn_family_delta`, `new_reviewers`, `new_sidecars`, and `approval_changed` so rerun and stop-loss decisions depend on protocol movement, not only on the latest flattened status line.
- `scripts/python/chapter6_route.py` consumes the same recovery artifacts and classifies `run-6.7`, `run-6.8`, `fix-deterministic`, `inspect-first`, `repo-noise-stop`, or residual-recording paths before a fresh rerun pays deterministic or LLM cost.
- `summary.json` remains producer-owned. Consumer contracts should only require fields they actually read.
- New shared sidecar fields are not allowed unless a real consumer needs them and the executable schema plus regression coverage are updated in the same change.

## Event Stream Contract

`run-events.jsonl` is append-only. Each line must satisfy `scripts/sc/schemas/sc-run-event.schema.json`.

Required fields:

- `schema_version`
- `ts`
- `event`
- `event_family`
- `task_id`
- `run_id`
- `turn_id`
- `turn_seq`
- `delivery_profile`
- `security_profile`
- `item_kind`
- `item_id`
- `step_name`
- `status`
- `details`

Field rules:

- `turn_seq` is the monotonically increasing turn number inside one `run_id`; fresh runs start at `1`, resumptions publish higher values
- `turn_id` is the stable lifecycle identity for this run turn; the canonical format is `<run_id>:turn-<turn_seq>`
- `item_kind` identifies the current target object of the event; built-in values are `run`, `task`, `step`, `approval`, `reviewer`, and `sidecar`
- `item_id` is the stable identifier for that target object; run-level events use the `run_id`, step-level events use the step name, approval events prefer `request_id`
- `event_family` is a stable event taxonomy bucket derived from `event`; built-in families include `run`, `step`, `approval`, `reviewer`, `sidecar`, `acceptance-preflight`, `recovery`, `runtime-guard`, and `custom`
- `step_name` may be `null` for non-step events
- `status` may be `null` for non-step events
- `details` is always an object and may be empty
- `task_id`, `run_id`, `turn_id`, and `item_id` are strings, even when the logical ids are numeric
- consumers must not assume `run_completed` is the last line; final sidecar sync events may be appended afterwards in the same turn

Common event names:

- `run_started`
- `run_resumed`
- `run_forked`
- `run_completed`
- `run_aborted`
- `wall_time_exceeded`
- `step_planned`
- `step_skipped`
- `step_started`
- `step_finished`
- `step_completed`
- `step_failed`
- `approval_request_written` when approval state changes
- `reviewer_completed`
- `sidecar_harness_capabilities_synced`
- `sidecar_execution_context_synced`
- `sidecar_repair_guide_synced`
- `sidecar_latest_index_synced`
- `sidecar_active_task_synced`
- `acceptance_preflight_skipped`
- `acceptance_preflight_completed`

The protocol does not currently reserve a transport-level request id. Correlation happens through `task_id`, `run_id`, `turn_id`, `item_kind`, `item_id`, and artifact paths.

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
- `pause`: not a producer command, but a valid consumer recommendation when approval is pending and no recovery command should run yet

## Consumer Read Order

When recovering after context loss, read in this order:

1. `latest.json`
2. `summary.json`
3. `execution-context.json`
4. `repair-guide.json` or `repair-guide.md`
5. `agent-review.json` if present
6. `run-events.jsonl` if lifecycle sequencing is still unclear
7. approval files when the recovery action is `fork`, `pause`, or `inspect` due to `approval_*` blocking

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
If the same recovery surface also exposes `chapter6_route_lane` or `repo_noise_reason` through project-health or `active-task`, treat them as dashboard-level hints that should agree with the canonical `chapter6-route` result, not as a replacement for the task-scoped route command itself.

## Local Inspect Entry

Use `py -3 scripts/python/dev_cli.py inspect-run` as the stable local replay/inspect entrypoint:

- Task-scoped latest pointer: `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id <task-id>`
- Quick task-scoped recommendation-only read: `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id <task-id> --recommendation-only`
- Explicit task-scoped bundle: `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --latest logs/ci/<date>/sc-review-pipeline-task-<task-id>/latest.json`
- Explicit repo-scoped bundle: `py -3 scripts/python/dev_cli.py inspect-run --kind local-hard-checks --latest logs/ci/<date>/local-hard-checks-latest.json`
- Persist one stable inspection payload: `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id <task-id> --out-json logs/ci/<date>/inspect-task-<task-id>.json`

The command returns `0` only when the inspected run is fully usable for recovery. Any broken pointer, schema drift, or failed step returns non-zero and emits one stable JSON payload.
When `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id <task-id>` resolves the latest task-scoped bundle automatically, it now skips both dry-run-only pointers and newer `planned-only` terminal bundles, then falls back to the newest real producer run.
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
