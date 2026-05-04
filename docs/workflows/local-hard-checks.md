# Local Hard Checks Workflow

This document defines the contract for `py -3 scripts/python/dev_cli.py run-local-hard-checks`.

## Goal

- Provide one stable local entrypoint for full hard validation.
- Avoid step drift caused by manually stitching commands together.
- Avoid re-running `run_gate_bundle.py --mode hard` and creating duplicate noise.
- Treat local hard validation as a first-class run object for recovery after context resets.

## When To Use It

- Run it before commit when you want the full local hard path.
- Run it before a PR when semantics, contracts, unit tests, and the small engine set all need confirmation.
- Run it to reproduce the repository-recommended local order before debugging a CI failure.
- Read its sidecars after a context reset to see where the local hard path stopped.

## Default Order

`run-local-hard-checks` executes these steps in order and stops at the first failing step:

1. `scripts/python/run_gate_bundle.py --mode hard`
2. `scripts/python/run_dotnet.py`
3. `scripts/python/run_gdunit.py` (Adapters/Config + Security hard set, only when `--godot-bin` is provided)
4. `scripts/python/smoke_headless.py --strict` (only when `--godot-bin` is provided)

Core rules:

- `run_gate_bundle.py` runs exactly once.
- `quality_gates.py all` is intentionally excluded from this chain to avoid re-triggering the hard bundle.
- Without `--godot-bin`, the run executes project health scan + gate bundle + dotnet.
- Every step writes events and a step log so recovery can start from artifacts instead of memory.

## Recommended Commands

```powershell
# Full local hard validation
py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin C:\Godot\Godot_v4.5.1-stable_mono_win64_console.exe

# No Godot runtime available: semantics, contracts, and dotnet only
py -3 scripts/python/dev_cli.py run-local-hard-checks

# Inspect the latest repo-scoped hard-check run after it stops
py -3 scripts/python/dev_cli.py inspect-run --kind local-hard-checks
```

## Main Parameters

- `--godot-bin <path>`: enables the GdUnit4 hard set and strict smoke.
- `--solution <path>`: forwarded to `run_dotnet.py`; auto-resolved when omitted.
- `--configuration <Debug|Release>`: forwarded to `run_dotnet.py`; default `Debug`.
- `--delivery-profile <profile>`: resolves the run-level delivery profile and default security profile.
- `--task-file <path>`: repeatable; overrides the default task views and is forwarded to the hard gate bundle.
- `--out-dir <path>`: overrides the harness run root; default is `logs/ci/<YYYY-MM-DD>/local-hard-checks-<run-id>/`.
- `--run-id <id>`: stable identity for the whole harness run and its nested hard bundle artifacts.
- `--timeout-sec <n>`: forwarded to strict smoke; default `5`.

Notes:
- For test-oriented commands, `--solution auto` prefers the repo's test-bearing solution when one exists; in a copied business repo, keep this auto-resolved instead of hardcoding a template or source-repo `.sln` name.

## Difference From Other Entrypoints

### `run-ci-basic`

- Goal: minimal hard gate entrypoint.
- Default behavior: only runs `run_gate_bundle.py --mode hard`.
- It only appends legacy `ci_pipeline.py` when `--legacy-preflight` is explicitly enabled.

### `run-quality-gates`

- Goal: wrap `quality_gates.py all`.
- Default behavior: run the hard gate bundle first and optionally append `--gdunit-hard` / `--smoke`.
- Useful for focused engine-side checks, but not the right primary entrypoint for full local hard validation because it can duplicate the hard bundle path.

### Manual Step Execution

Useful when isolating one failing step, but not the recommended day-to-day default.

## Artifacts And Logs

### Harness Root

Default root: `logs/ci/<YYYY-MM-DD>/local-hard-checks-<run-id>/`

This directory is now a first-class run object and writes at least:

- `summary.json`: canonical run status and step list
- `execution-context.json`: profile state, failed step, and sidecar pointers
- `repair-guide.json`: machine-readable repair guidance
- `repair-guide.md`: human-readable repair guidance
- `run-events.jsonl`: append-only lifecycle and step timeline with stable taxonomy fields (`turn_id`, `item_kind`, `item_id`, `event_family`)
- `harness-capabilities.json`: supported sidecars and recovery actions for this run type
- `run_id.txt`: stable run id
- `<step>.log`: one JSON log per step, for example `gate-bundle-hard.log`

The same date directory also gets a repo-scoped pointer:

- `logs/ci/<YYYY-MM-DD>/local-hard-checks-latest.json`

### Repo Health Prelude

- The run now refreshes `logs/ci/project-health/latest.json` and `logs/ci/project-health/latest.html` before any hard validation step.
- `warn` from project health does not block the run.
- `fail` from project health blocks the run immediately because it indicates a repo-level stop-loss issue.

### Nested Step Artifacts

- Hard gate bundle: nested summary at `<run-out-dir>/hard/summary.json`
- Dotnet: `logs/unit/<YYYY-MM-DD>/`
- GdUnit4 hard set: `logs/e2e/dev-cli/local-hard-checks-gdunit-hard/`
- Strict smoke: `logs/ci/<YYYY-MM-DD>/smoke/<timestamp>/`

### Protocol Boundary

This run currently supports only the minimal recovery actions:

- `rerun`
- `inspect-failed-step`

It does not produce `approval-request.json`, `approval-response.json`, `marathon-state.json`, or `agent-review.json`. Those sidecars remain part of the task-scoped `run_review_pipeline.py` protocol.

## Recovery Reading Hints

Use local hard checks as a repo-scoped health run, not as a task-scoped Chapter 6 producer run.

- Inspect the latest repo-scoped run with `py -3 scripts/python/dev_cli.py inspect-run --kind local-hard-checks` before rerunning it.
- That inspect surface should only recommend repo-scoped commands such as `inspect-run --kind local-hard-checks` and `run-local-hard-checks`; if you need `resume`, `fork`, or `needs-fix-fast`, you are in the wrong lane and should switch to the task-scoped review pipeline.
- Read `summary.json`, `execution-context.json`, `repair-guide.md`, and `run-events.jsonl` together; they tell you which step failed and whether the next action is rerun or inspect.
- If the repo-scoped run failed in `project-health`, `run_gate_bundle`, or `run_dotnet`, fix that root cause first instead of paying for another full hard pass.
- If you actually need task recovery semantics such as `reason`, `run_type`, `reuse_mode`, `artifact_integrity`, `planned-only`, `planned_only_incomplete`, `llm_retry_stop_loss`, `sc_test_retry_stop_loss`, `recommended_action_why`, `chapter6_route_lane`, `repo_noise_reason`, or `recommended_action = needs-fix-fast`, switch to the task-scoped recovery chain: `resume-task`, `dev_cli.py chapter6-route --recommendation-only`, `dev_cli.py inspect-run --kind pipeline`, `active-task`, and `run_review_pipeline.py`.
- Do not treat `local-hard-checks-latest.json` as evidence that a task can reopen Chapter 6. Task-scoped rerun decisions must come from the pipeline sidecars, not from repo-scoped hard-check artifacts.

## Stop-Loss Rules

- If you only want semantics and contract gates, use `run-ci-basic` instead.
- If you only want GdUnit4 hard or smoke, use `run-quality-gates` or the dedicated subcommands instead.
- If this entrypoint needs more steps later, do not push command composition back into `dev_cli.py`; extend `scripts/python/local_hard_checks_harness.py` and `scripts/python/dev_cli_builders.py` instead.
- If future work needs approvals, marathon checkpoints, or reviewer sidecars, decide first whether the feature still belongs to a repo-scoped run or should move into the task-scoped review pipeline.

## Protocol Examples

- `docs/workflows/examples/sc-local-hard-checks-latest-index.example.json`
- `docs/workflows/examples/sc-local-hard-checks-execution-context.example.json`
- `docs/workflows/examples/sc-local-hard-checks-repair-guide.example.json`
- `docs/workflows/examples/sc-local-hard-checks-repair-guide.example.md`
- `docs/workflows/examples/sc-local-hard-checks-inspect.example.json`
- `docs/workflows/examples/sc-local-hard-checks-compact.example.json`
- `docs/workflows/examples/sc-local-hard-checks-inspect.stdout.example.txt`
- `docs/workflows/examples/sc-local-hard-checks-compact.stdout.example.txt`

## Related Docs

- `docs/testing-framework.md`
- `docs/workflows/gate-bundle.md`
- `docs/workflows/run-protocol.md`
- `docs/workflows/project-health-dashboard.md`
- `docs/agents/01-session-recovery.md`
- `DELIVERY_PROFILE.md`
