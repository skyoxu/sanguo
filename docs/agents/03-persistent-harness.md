# Persistent Harness

The harness contract is local-file based. The producer pipeline owns the durable artifacts; later agents and sidecars consume them without mutating `summary.json`.

## Executable Contract
- Human-readable protocol: `docs/workflows/run-protocol.md`
- Boundary cutline: `docs/workflows/harness-boundary-matrix.md`
- Executable run-event schema: `scripts/sc/schemas/sc-run-event.schema.json`
- Executable harness-capabilities schema: `scripts/sc/schemas/sc-harness-capabilities.schema.json`

## Pipeline Outputs
`py -3 scripts/sc/run_review_pipeline.py --task-id <id>` writes and, unless `--dry-run`, `--skip-agent-review`, or the active delivery profile sets `agent_review.mode=skip`, also refreshes the reviewer sidecar:
- `summary.json`: pipeline status and step list.
- `execution-context.json`: git state, recovery pointers, delivery profile, security profile, marathon recovery snapshot, diff summary, and the latest agent-review recommendation snapshot.
- `repair-guide.json`: deterministic repair actions for the first failed step, wall-time/context-refresh stop, or isolated reviewer follow-up.
- `repair-guide.md`: human-readable version of the repair guide, including soft approval recovery status when `fork` requires operator review.
- `run_id.txt`: stable run id for the artifact directory.
- `marathon-state.json`: resumable step checkpoint state, attempt counters, wall-time stop markers, fork metadata, diff baseline/current/growth snapshot, category/axis summary, context-refresh flags, and the normalized agent-review action (`resume|refresh|fork`).
- `run-events.jsonl`: append-only event stream for `run_started`, `run_resumed`, `run_forked`, step transitions, `wall_time_exceeded`, `run_completed`, and `run_aborted`.
- `harness-capabilities.json`: stable machine-readable contract declaring protocol version, supported sidecars, supported recovery actions, and whether approval request/response files are supported.
- `latest.json`: task-scoped pointer to the newest pipeline run for the current day, including `marathon_state_path`, `run_events_path`, and `harness_capabilities_path`.

## Reviewer Sidecar Outputs
`py -3 scripts/sc/agent_to_agent_review.py --task-id <id>` can also be run standalone to rebuild reviewer artifacts from the latest producer outputs:
- `agent-review.json`: deterministic machine-readable reviewer contract, including `explain.recommended_action`, `explain.summary`, and `explain.reasons` for direct recovery guidance.
- `agent-review.md`: human-readable reviewer summary.
- `latest.json`: updated with `agent_review_json_path` and `agent_review_md_path`; the pipeline preserves those pointers for the same run id when it persists later sidecars.

## Approval Contract
Approval is still local-file based. The pipeline now auto-manages the soft approval contract for risky fork recovery paths:
- `approval-request.json`: auto-created or refreshed when the repair state recommends `fork` (for example agent-review `recommended_action=fork`, context refresh plus isolated continuation, wall-time stop-loss with fork available, or an explicit `--fork` run).
- `approval-response.json`: optional reviewer decision envelope (`approved|denied`) bound to `request_id`; when present, the pipeline indexes it into `execution-context.json` and `latest.json` but does not block the run.
- Missing response does not fail the pipeline. This is a soft gate for human-orchestrated recovery, not a hard CI stop.

## Design Rule
- Keep `summary.json` schema stable.
- Add recovery state and protocol metadata only as sidecar files.
- Agent-review verdicts must not overwrite producer status; they only influence `marathon-state.json`, `execution-context.json`, and `repair-guide.json/md`.
- Prefer `run-events.jsonl` and `latest.json` before scraping console text.
- Do not use git-tracked files for high-frequency heartbeat events.
- Use git-tracked files only for durable intent and decisions.
- Consume stable artifact paths before falling back to broader repo inspection.
