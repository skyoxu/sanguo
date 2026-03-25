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

- `logs/ci/project-health/server.json`
- `logs/ci/project-health/detect-project-stage.latest.json`
- `logs/ci/project-health/doctor-project.latest.json`
- `logs/ci/project-health/check-directory-boundaries.latest.json`
- `logs/ci/project-health/latest.json`
- `logs/ci/project-health/latest.html`

Historical snapshots are written under `logs/ci/<YYYY-MM-DD>/project-health/`.

## Visual Page

Open `logs/ci/project-health/latest.html` in a browser or VS Code preview.
The page auto-refreshes every 15 seconds, so it can stay open while you rerun health commands.
It is still a static local file: the content only changes when one of the commands writes a new latest record.

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
