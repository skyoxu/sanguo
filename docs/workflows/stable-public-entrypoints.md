# Stable Public Entrypoints

This document lists the stable, recommended script entrypoints for day-to-day use.
Use it when you need to decide which command to run next.
Use `docs/workflows/script-entrypoints-index.md` when you need the full executable inventory, direct deps, transitive deps, or full argument scan.

## Selection Rules

- Prefer these entrypoints before reaching for lower-level helper scripts.
- If a script is not listed here, it is usually one of these:
  - a lower-level building block already wrapped by a stable entrypoint
  - a rare audit / migration / maintenance command
  - a one-off repair or template sync tool
- Do not manually stitch `scripts/sc/test.py + scripts/sc/acceptance_check.py + scripts/sc/llm_review.py` when `scripts/sc/run_review_pipeline.py` already covers the same task path.

## Repo Bootstrap And Recovery

### `py -3 scripts/python/dev_cli.py run-local-hard-checks`

Use when:
- first full validation after copying the template into a new repo
- before commit or before PR when you want the repo-level hard path
- reproducing the local order before debugging CI

Prerequisites:
- `py -3`
- `.NET 8 SDK`
- optional `--godot-bin` for GdUnit and strict smoke

Why this is stable:
- it is the repo-level hard-check entrypoint
- it writes sidecars and latest pointers
- it now refreshes `project-health` before the hard chain

### `py -3 scripts/python/dev_cli.py project-health-scan`

Use when:
- immediately after cloning or syncing template upgrades
- after renaming repo identity, paths, and project files
- when you want a deterministic repo-health snapshot before task work starts

Prerequisites:
- `py -3`

Why this is stable:
- it is the repo bootstrap stop-loss point
- it writes the canonical latest repo-health records

### `py -3 scripts/python/dev_cli.py serve-project-health`

Use when:
- you want a stable local browser URL for the project-health page
- you want the dashboard to stay open while rerunning repo-health commands

Prerequisites:
- local machine only; do not use in CI
- binds to `127.0.0.1`

Why this is stable:
- it is the recommended local serving entrypoint for `project-health`

### `py -3 scripts/python/dev_cli.py resume-task --task-id <id>`

Use when:
- resuming a task after context reset
- returning to a task after another session or another day
- you need the recommended recovery command set first, before deeper inspection

Prerequisites:
- task triplet available
- task-scoped sidecars exist if the task has already run through the pipeline

Why this is stable:
- it is the canonical task recovery entrypoint
- it consumes active-task sidecars, inspect output, and recovery docs

### `py -3 scripts/python/inspect_run.py --kind <kind> [--task-id <id>]`

Use when:
- `resume-task` is still not enough
- you need to inspect the latest pipeline or local-hard-checks sidecar set directly
- you are debugging run artifacts rather than continuing normal delivery

Prerequisites:
- existing sidecar outputs under `logs/ci/**`

Why this is stable:
- it is the canonical sidecar inspection entrypoint

## Task Delivery Loop

### `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile <profile>`

Use when:
- running the full task path for one task
- you want `sc-test`, acceptance, and LLM review under one run id
- you want repair guidance, active-task sidecars, and technical debt sync

Prerequisites:
- task triplet available
- `GODOT_BIN` for engine-side stages
- LLM runtime if you do not pass `--skip-llm-review`

Why this is stable:
- it is the default task-level main entrypoint
- it replaces manually stitching lower-level review commands together

### `py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify <mode>`

Use when:
- acceptance `Refs:` point to missing `.cs` or `.gd` tests
- you want strict red-first test creation before implementation
- you need ACC anchors inserted into generated tests

Prerequisites:
- task triplet available
- LLM runtime
- `--godot-bin` when verification includes Godot-side checks

Why this is stable:
- it is the recommended acceptance-to-test scaffold entrypoint
- it already includes deterministic naming and strict-red guards

### `py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify auto --execution-plan-policy <mode>`

Use when:
- generation looks complex before running `llm_generate_tests_from_acceptance_refs.py`
- the task mixes `.cs` and `.gd`, many missing refs, or many anchors
- you want to warn, draft, or require an `execution-plan` first

Prerequisites:
- task triplet available

Why this is stable:
- it is the preflight decision gate for long or mixed-surface TDD work

### `py -3 scripts/sc/build.py tdd --stage <red|green|refactor>`

Use when:
- you want the deterministic TDD orchestration path
- you are already inside an implementation loop and need stage-specific gating

Prerequisites:
- task triplet available for task-aware checks
- `.NET 8 SDK`
- `--godot-bin` if your stage triggers engine-side checks

Why this is stable:
- it is the main build-side TDD orchestrator, not a one-off helper

## Task Metadata And Architecture Integrity

### `py -3 scripts/python/task_links_validate.py`

Use when:
- validating ADR / Chapter / Overlay backlinks
- checking front matter and task semantic link integrity

### `py -3 scripts/python/check_tasks_all_refs.py`

Use when:
- validating refs completeness across task triplet views
- confirming task metadata and linked assets are coherent

### `py -3 scripts/python/validate_task_master_triplet.py`

Use when:
- validating triplet structural consistency
- auditing task mapping, link, layer, and dependency shape

### `py -3 scripts/python/validate_contracts.py`

Use when:
- validating domain contracts under the template rules
- checking naming, XML docs, namespace rules, and overlay backlinks

### `py -3 scripts/python/check_domain_contracts.py`

Use when:
- a business repo keeps extra domain-level contract checks outside the generic template validator
- you want the domain-specific contract stop-loss entrypoint

Stop-loss:
- this script may be a lighter or repo-specific supplement; do not treat it as a replacement for `validate_contracts.py`

### `py -3 scripts/python/sync_task_overlay_refs.py --prd-id <PRD-ID> --write`

Use when:
- task overlay refs drift from overlay docs
- you need to refresh triplet overlay linkage after overlay authoring or regeneration

Prerequisites:
- task triplet available
- real PRD / overlay roots
- write review after execution

Why this is stable:
- it is already part of the documented overlay/task maintenance path

### `py -3 scripts/sc/llm_generate_overlays_batch.py ...`

Use when:
- scaffolding or repairing Overlay 08 pages from PRD inputs
- migrating a business repo toward the current overlay authoring flow

Prerequisites:
- PRD inputs and business-local `PRD-ID`
- LLM runtime

Why this is stable:
- it is the batch overlay generation entrypoint referenced by the current upgrade docs and workflows

## Lower-Level But Still Public

These remain public and workflow-facing, but they are usually invoked through higher-level entrypoints first:

- `scripts/sc/acceptance_check.py`
- `scripts/sc/llm_review.py`
- `scripts/sc/test.py`
- `scripts/python/run_gate_bundle.py`
- `scripts/python/run_dotnet.py`
- `scripts/python/run_gdunit.py`
- `scripts/python/smoke_headless.py`
- `scripts/python/quality_gates.py`
- `scripts/python/ci_pipeline.py`

Use them directly when you are isolating one failing stage or intentionally bypassing the higher-level orchestrator for debugging.

## Relationship To Other Docs

- `workflow.md`
  - day-to-day operator sequence
- `workflow.example.md`
  - bootstrap example for a fresh business repo copied from the template
- `docs/workflows/script-entrypoints-index.md`
  - full recurring entrypoint inventory with direct deps, transitive deps, and argument scan
- `docs/workflows/local-hard-checks.md`
  - contract for the repo-level hard harness
- `docs/workflows/project-health-dashboard.md`
  - repo-health records and local dashboard behavior
- `scripts/sc/README.md`
  - deeper `sc-*` runtime behavior and examples
