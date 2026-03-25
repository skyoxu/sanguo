# Local Hard Checks Workflow

This document defines the contract for py -3 scripts/python/dev_cli.py run-local-hard-checks.

## Goal

- Provide one stable local entrypoint for full hard validation.
- Avoid step drift caused by manually stitching commands together.
- Avoid re-running 
un_gate_bundle.py --mode hard and creating duplicate noise.
- Treat local hard validation as a first-class run object for recovery after context resets.

## When To Use It

- Run it before commit when you want the full local hard path.
- Run it before a PR when semantics, contracts, unit tests, and the small engine set all need confirmation.
- Run it to reproduce the repository-recommended local order before debugging a CI failure.
- Read its sidecars after a context reset to see where the local hard path stopped.

## Default Order


un-local-hard-checks executes these steps in order and stops at the first failing step:

1. scripts/python/run_gate_bundle.py --mode hard
2. scripts/python/run_dotnet.py
3. scripts/python/run_gdunit.py (Adapters/Config + Security hard set, only when --godot-bin is provided)
4. scripts/python/smoke_headless.py --strict (only when --godot-bin is provided)

Core rules:

- 
un_gate_bundle.py runs exactly once.
- quality_gates.py all is intentionally excluded from this chain to avoid re-triggering the hard bundle.
- Without --godot-bin, the run executes project health scan + gate bundle + dotnet.
- Every step writes events and a step log so recovery can start from artifacts instead of memory.

## Recommended Commands

`powershell
# Full local hard validation
py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin C:\Godot\Godot_v4.5.1-stable_mono_win64_console.exe

# No Godot runtime available: semantics, contracts, and dotnet only
py -3 scripts/python/dev_cli.py run-local-hard-checks
`

## Main Parameters

- --godot-bin <path>: enables the GdUnit4 hard set and strict smoke.
- --solution <path>: forwarded to 
un_dotnet.py; default Game.sln.
- --configuration <Debug|Release>: forwarded to 
un_dotnet.py; default Debug.
- --delivery-profile <profile>: resolves the run-level delivery profile and default security profile.
- --task-file <path>: repeatable; overrides the default task views and is forwarded to the hard gate bundle.
- --out-dir <path>: overrides the harness run root; default is logs/ci/<YYYY-MM-DD>/local-hard-checks-<run-id>/.
- --run-id <id>: stable identity for the whole harness run and its nested hard bundle artifacts.
- --timeout-sec <n>: forwarded to strict smoke; default 5.

## Difference From Other Entrypoints

### 
un-ci-basic

- Goal: minimal hard gate entrypoint.
- Default behavior: only runs 
un_gate_bundle.py --mode hard.
- It only appends legacy ci_pipeline.py when --legacy-preflight is explicitly enabled.

### 
un-quality-gates

- Goal: wrap quality_gates.py all.
- Default behavior: run the hard gate bundle first and optionally append --gdunit-hard / --smoke.
- Useful for focused engine-side checks, but not the right primary entrypoint for full local hard validation because it can duplicate the hard bundle path.

### Manual Step Execution

Useful when isolating one failing step, but not the recommended day-to-day default.

## Artifacts And Logs

### Harness Root

Default root: logs/ci/<YYYY-MM-DD>/local-hard-checks-<run-id>/

This directory is now a first-class run object and writes at least:

- summary.json: canonical run status and step list
- execution-context.json: profile state, failed step, and sidecar pointers
- 
epair-guide.json: machine-readable repair guidance
- 
epair-guide.md: human-readable repair guidance
- 
un-events.jsonl: append-only lifecycle and step timeline
- harness-capabilities.json: supported sidecars and recovery actions for this run type
- 
un_id.txt: stable run id
- <step>.log: one JSON log per step, for example gate-bundle-hard.log

The same date directory also gets a repo-scoped pointer:

- logs/ci/<YYYY-MM-DD>/local-hard-checks-latest.json

### Repo Health Prelude

- The run now refreshes `logs/ci/project-health/latest.json` and `logs/ci/project-health/latest.html` before any hard validation step.
- `warn` from project health does not block the run.
- `fail` from project health blocks the run immediately because it indicates a repo-level stop-loss issue.

### Nested Step Artifacts

- Hard gate bundle: nested summary at <run-out-dir>/hard/summary.json
- Dotnet: logs/unit/<YYYY-MM-DD>/
- GdUnit4 hard set: logs/e2e/dev-cli/local-hard-checks-gdunit-hard/
- Strict smoke: logs/ci/<YYYY-MM-DD>/smoke/<timestamp>/

### Protocol Boundary

This run currently supports only the minimal recovery actions:

- 
erun
- inspect-failed-step

It does not produce approval-request.json, approval-response.json, marathon-state.json, or agent-review.json. Those sidecars remain part of the task-scoped 
un_review_pipeline.py protocol.

## Stop-Loss Rules

- If you only want semantics and contract gates, use 
un-ci-basic instead.
- If you only want GdUnit4 hard or smoke, use 
un-quality-gates or the dedicated subcommands instead.
- If this entrypoint needs more steps later, do not push command composition back into dev_cli.py; extend scripts/python/local_hard_checks_harness.py and scripts/python/dev_cli_builders.py instead.
- If future work needs approvals, marathon checkpoints, or reviewer sidecars, decide first whether the feature still belongs to a repo-scoped run or should move into the task-scoped review pipeline.

## Related Docs

- docs/testing-framework.md
- docs/workflows/gate-bundle.md
- docs/workflows/run-protocol.md
- DELIVERY_PROFILE.md
