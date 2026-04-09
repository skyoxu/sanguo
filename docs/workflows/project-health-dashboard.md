# Project Health Dashboard

This workflow exposes three repo-health records and one static dashboard page:

- `detect-project-stage`: tells you whether the repo is still in bootstrap, missing the real task triplet, or ready for the daily task loop.
- `doctor-project`: checks core bootstrap files, workflow entry docs, task-triplet availability, contracts baseline, and local `GODOT_BIN` readiness.
- `check-directory-boundaries`: enforces the highest-value directory rules such as `Game.Core`/`Game.Core/Contracts` staying free of `Godot.*` and `docs/architecture/base/` staying free of `PRD-*` leakage.

## Commands

Use the stable repo entrypoints:

```bash
py -3 scripts/python/dev_cli.py detect-project-stage
py -3 scripts/python/dev_cli.py doctor-project
py -3 scripts/python/dev_cli.py check-directory-boundaries
py -3 scripts/python/dev_cli.py project-health-scan
py -3 scripts/python/dev_cli.py serve-project-health
```

Direct script entrypoints are also available:

```bash
py -3 scripts/python/project_health_scan.py
py -3 scripts/python/project_health_scan.py --serve
py -3 scripts/python/serve_project_health.py
```

## Outputs

Every command refreshes the same stable latest records:

- `logs/ci/project-health/report-catalog.latest.json`
- `logs/ci/project-health/server.json`
- `logs/ci/project-health/detect-project-stage.latest.json`
- `logs/ci/project-health/doctor-project.latest.json`
- `logs/ci/project-health/check-directory-boundaries.latest.json`
- `logs/ci/project-health/latest.json`
- `logs/ci/project-health/latest.html`

Historical snapshots are written under `logs/ci/<YYYY-MM-DD>/project-health/`.

## Visual Page

Open `logs/ci/project-health/latest.html` in a browser or VS Code preview.
The dashboard now aggregates report-style JSON files under `logs/ci/**` and shows them in a collapsible table.
The page does not auto-refresh. Use the manual refresh button after rerunning health commands.
It keeps the same compatibility note in page output: `Auto-refresh is disabled`.
It is still a static local file: the content only changes when one of the commands writes a new latest record.
When a batch workflow summary exposes high-value fields such as `extract_family_recommended_actions`, `family_hotspots`, or `quarantine_ranges`, the page also renders a compact diagnostics excerpt above the full JSON table.
This lets operators see workflow 5.1 failure families and the recommended next action without opening the raw batch summary first.
The page now also summarizes the newest `logs/ci/active-tasks/task-*.active.json` sidecars, including `clean_state`, `recommended_action`, and whether a task is in the `deterministic_ok_llm_not_clean` state.
Use this section to spot tasks that should go straight to `needs-fix-fast` instead of paying for a fresh full `6.7`.
The active-task cards now also surface `latest_reason`, `latest_run_type`, `latest_reuse_mode`, `latest_diagnostics_keys`, `chapter6_*` hints, `rerun_forbidden`, `rerun_override_flag`, `artifact_integrity`, `latest_json`, `reported_latest_json`, `latest_json_mismatch`, `latest_json_repaired`, and a compact deterministic-bundle summary so you can decide between reopening `6.7`, narrowing to `6.8`, or stopping on rerun guards directly from the dashboard.
To reduce historical noise, the dashboard ignores non-canonical `active-task` pointers and stale clean sidecars whose `recommended_action=continue` has aged out past the local freshness window.
The clean-sidecar freshness window is controlled by `PROJECT_HEALTH_ACTIVE_TASK_CLEAN_MAX_AGE_DAYS` and defaults to `3`.
The active-task collection window is controlled by `PROJECT_HEALTH_ACTIVE_TASK_LIMIT` and defaults to `16`.
The number of active-task cards shown in the HTML page is controlled by `PROJECT_HEALTH_ACTIVE_TASK_TOP_RECORDS` and defaults to `8`.

The active-task aggregate counters also track Chapter 6 KPI-style fields such as:
- `rerun_forbidden`
- `artifact_integrity_blocked`
- `artifact_integrity_planned_only_incomplete`
- `deterministic_bundle_available`
- `next_action_needs_fix_fast`
- `next_action_inspect`
- `next_action_resume`
- `next_action_continue`
The active-task summary row now also counts `llm_retry_stop_loss_blocked`, `sc_test_retry_stop_loss_blocked`, `artifact_integrity_blocked`, `recent_failure_summary_blocked`, `latest_json_mismatch`, and `latest_json_repaired`, so repeated timeout-driven waste, known unit-root-cause retries, stale/incomplete recovery bundles, repeated same-family failure stop-loss signals, and repaired latest-pointer drift are visible without opening raw artifacts.
Each active-task card now prints `recommended_action_why`, `chapter6_stop_loss_note`, plus explicit diagnostic rows for `llm_retry_stop_loss`, `sc_test_retry_stop_loss`, `recent_failure_summary`, and `artifact_integrity` when those stop-loss or recovery-integrity signals are present.
When the latest pointer is only a planned-only terminal bundle, the card also emits `planned_only_terminal_bundle: true` so operators can distinguish stale planning artifacts from real completed producer runs at a glance.

## Recovery Reading Hints

Use the active-task cards as a recovery decision aid, not as a rerun trigger by themselves. Read these fields together before reopening Chapter 6:

- `latest_reason` tells you why the newest pointer was produced.
- `latest_run_type` tells you whether the newest pointer came from a real producer run or only from a planning / dry path.
- `artifact_integrity` tells you whether the latest bundle is structurally safe to trust for resume decisions.
- `planned_only_terminal_bundle: true` means the newest pointer is evidence-only; it is not a valid base for reopening `6.7` or `6.8`.
- `recommended_action_why` is the shortest explanation for why the dashboard recommends `inspect`, `resume`, `continue`, or `needs-fix-fast`.
- After reading the card, switch to `py -3 scripts/python/dev_cli.py resume-task --task-id <id>` when you need the canonical task-scoped recovery summary and command suggestion.

Interpretation rules:

- If `latest_run_type = planned-only` or `latest_reason = planned_only_incomplete`, treat the newest bundle as evidence only. Read it, but recover from the previous real producer bundle instead.
- If `artifact_integrity` is present or the active-task card shows `artifact_integrity_blocked`, stop before rerunning Chapter 6. First locate the last real deterministic / producer bundle and recover from that pointer.
- If stop-loss rows such as `llm_retry_stop_loss` or `sc_test_retry_stop_loss` are present, prefer the narrow follow-up path instead of paying for another full `6.7`.
- If `recommended_action = needs-fix-fast`, go straight to the targeted closure path; do not spend another full rerun just to rediscover the same deterministic evidence.

## Template-Specific Interpretation

In this template repo, `triplet-missing` is a valid warning state when only `examples/taskmaster/` exists and the real `.taskmaster/tasks/*.json` has not been created yet.
That warning should stay visible until a copied business repo creates its real task triplet.

## Recommended Use

- After cloning or syncing template upgrades: run `py -3 scripts/python/dev_cli.py project-health-scan`.
- Before task-scoped automation in a business repo: make sure `detect-project-stage` is no longer `triplet-missing`.
- If the dashboard shows a boundary failure: fix the repo layout before continuing feature work.

## Serving The Page

Use one of these when you want a stable browser URL on `127.0.0.1`:

```bash
py -3 scripts/python/serve_project_health.py
py -3 scripts/python/dev_cli.py serve-project-health
py -3 scripts/python/project_health_scan.py --serve
```

Behavior:

- The server binds to `127.0.0.1` only.
- If this repo already has a live project-health server, the script reuses it.
- If no live server exists, the script picks the first free port in `8765-8799` unless `--port` is explicitly provided.
- The chosen URL and PID are written to `logs/ci/project-health/server.json`.
- `--serve` is rejected in CI.

## New Repo First-Run Timing

For a fresh repo copied from the template, the recommended first full run is:

1. Rename the repo, project, paths, and old template leftovers.
2. Repair the entry indexes (`README.md`, `AGENTS.md`, `docs/PROJECT_DOCUMENTATION_INDEX.md`).
3. Run `py -3 scripts/python/dev_cli.py run-local-hard-checks` immediately.
4. If `GODOT_BIN` is already available, rerun with `--godot-bin`.

This first run is not just a pre-commit check. It is the repo bootstrap stop-loss point where project-health warnings become visible before task work starts.
