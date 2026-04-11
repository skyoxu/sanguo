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

Quick read variant: `py -3 scripts/python/dev_cli.py resume-task --task-id <id> --recommendation-only`
Automation variant: `py -3 scripts/python/dev_cli.py resume-task --task-id <id> --recommendation-only --recommendation-format json`
- Example compact JSON: `docs/workflows/examples/sc-resume-task-compact.example.json`
- Example compact stdout: `docs/workflows/examples/sc-resume-task-compact.stdout.example.txt`

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
- it is the first place to read `reason`, `run_type`, `reuse_mode`, `artifact_integrity`, and `diagnostics` before deciding between `6.7` and `6.8`
- it now surfaces `Chapter6 next action`, `Chapter6 can skip 6.7`, `Chapter6 can go to 6.8`, and `Chapter6 blocked by`
- `Chapter6 blocked by` now explicitly distinguishes `rerun_guard`, `llm_retry_stop_loss`, `sc_test_retry_stop_loss`, `waste_signals`, `recent_failure_summary`, and `artifact_integrity`, so recovery can choose between full-stop, narrow llm-only follow-up, known-unit-root-cause stop, repeated-failure-family stop-loss, stale-bundle fallback, or root-cause-first repair
- it now also emits a `Chapter6 stop-loss note`, so the recovery summary explains why a fresh full `6.7` would be wasteful
- it now surfaces approval contract fields (`Approval required action`, `Approval status`, `Approval decision`, `Approval reason`) so recovery can distinguish `pause`, `fork`, `resume`, and inspect-first approval failures without reopening the whole pipeline
- it also surfaces `recommended_action_why`, and `recommended_action = needs-fix-fast` is the cue to prefer targeted closure over another full rerun

### `py -3 scripts/python/dev_cli.py inspect-run --kind <kind> [--task-id <id>]`

Quick read variant: `py -3 scripts/python/dev_cli.py inspect-run --kind <kind> [--task-id <id>] --recommendation-only`
Automation variant: `py -3 scripts/python/dev_cli.py inspect-run --kind <kind> [--task-id <id>] --recommendation-only --recommendation-format json`

Use when:
- `resume-task` is still not enough
- you need to inspect the latest pipeline or local-hard-checks sidecar set directly
- you are debugging run artifacts rather than continuing normal delivery

Prerequisites:
- existing sidecar outputs under `logs/ci/**`

Why this is stable:
- it is the canonical sidecar inspection entrypoint
- it now exposes `latest_summary_signals` and `chapter6_hints` in one place for rerun/stop-loss decisions
- `chapter6_hints.blocked_by` now covers `rerun_guard`, `llm_retry_stop_loss`, `sc_test_retry_stop_loss`, `waste_signals`, `recent_failure_summary`, and `artifact_integrity`
- inspection is also where you confirm `planned_only_incomplete` / `artifact_integrity`, repeated same-family failures via `recent_failure_summary`, approval contract states (`pending|approved|denied|invalid|mismatched`), and whether the next move should be inspect-first instead of reopening `6.7`
- when automatic latest resolution sees a newer dry-run-only pipeline pointer, it now skips that candidate and falls back to the newest real recoverable run
- when automatic latest resolution sees a newer planned-only terminal bundle, it also skips that evidence-only candidate and falls back to the newest real producer run

### `py -3 scripts/python/dev_cli.py chapter6-route --task-id <id>`

Quick read variant: `py -3 scripts/python/dev_cli.py chapter6-route --task-id <id> --recommendation-only`
Automation variant: `py -3 scripts/python/dev_cli.py chapter6-route --task-id <id> --recommendation-only --recommendation-format json`
- Example compact JSON: `docs/workflows/examples/sc-chapter6-route-compact.example.json`
- Example compact stdout: `docs/workflows/examples/sc-chapter6-route-compact.stdout.example.txt`

Use when:
- you already have recovery artifacts and need a cheap go/no-go decision before reopening `6.7`
- you need to decide whether `6.8` is worth paying for this round
- you want a stable route for `repo-noise-stop`, `fix-deterministic`, `run-6.8`, `run-6.7`, or residual recording

Prerequisites:
- task-scoped recovery artifacts under `logs/ci/**`

Why this is stable:
- it reads recovery artifacts first, instead of relying on operator memory
- it classifies high-confidence `repo-noise` vs `task-issue` for the first failed `6.7` round
- it only recommends `6.8` when current edits hit the previous reviewer anchors
- it can record residual low-priority findings into `decision-logs/**` and `execution-plans/**` instead of paying for another same-shape rerun
- `scripts/sc/llm_review_needs_fix_fast.py` now consumes the same route preflight before spending deterministic / LLM budget when prior review artifacts exist; run `chapter6-route --recommendation-only` manually when you want the cheapest read-only go/no-go before touching 6.8.

## Task Delivery Loop

### `py -3 scripts/python/dev_cli.py run-single-task-chapter6 --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile <profile>`

Use when:
- you want one top-level Chapter 6 orchestrator instead of manually stitching `6.3 -> 6.9`
- you want recovery-first routing before paying for `6.7` or `6.8`
- you want profile-aware defaults where `playable-ea` defaults to `fix-through=P0` and `fast-ship` / `standard` default to `fix-through=P1`

Prerequisites:
- task triplet available
- `GODOT_BIN` for engine-side steps and repo-level hard checks

Why this is stable:
- it is the single-task Chapter 6 top-level entrypoint
- it always starts from `resume-task` and `chapter6-route` instead of assuming a fresh run
- it only jumps directly to `6.8` when recovery artifacts already prove that this is the cheapest valid lane
- by default it records residual `P2/P3` findings instead of repeatedly paying for the same-shape closure loop
- it keeps `6.9` behind the same orchestrator, so repo-level hard checks are still part of the normal closeout path

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
- it now carries rerun stop-loss signals so repeated full reruns are blocked when deterministic is already green or when recent `sc-test` failures share the same fingerprint
- it now consumes the same `chapter6-route` signal before a fresh full rerun, so `inspect-first`, `repo-noise-stop`, `fix-deterministic`, and `run-6.8` recommendations are enforced before refactor preflight and downstream cost
- `--resume` and `--fork` also enforce the approval sidecar contract before step execution: pending approval pauses recovery, approved approval redirects to `--fork`, denied approval redirects to `--resume`, and invalid or mismatched approval evidence forces inspection first
- when the same invocation already proved a known `sc-test` unit root cause, it records `diagnostics.sc_test_retry_stop_loss` and stops the same-run retry instead of paying that cost again
- exceptional overrides stay explicit: `--allow-full-rerun` and `--allow-repeat-deterministic-failures`
- a fresh run now inherits the latest task-scoped profile lock unless you explicitly pass `--reselect-profile`
- `--llm-base` now defaults to `origin/main`
- `--dry-run` still writes a local `summary.json` / `execution-context.json` / `repair-guide.*` in its own `out_dir`, but it no longer publishes `latest.json` or `active-task` sidecars, so it cannot pollute task recovery pointers
- producer runs that end as `planned-only` / `planned_only_incomplete` are not valid recovery baselines for reopening `6.7` or `6.8`; they are evidence only

### `py -3 scripts/python/run_single_task_light_lane_batch.py --task-id-start <start> --task-id-end <end> --delivery-profile <profile> --max-tasks-per-shard <n>`

Use when:
- you want to run workflow 5.1 across a long task range without manually splitting directories
- you want isolated shard `out-dir`s plus one coordinator summary and one merged summary
- you want to avoid `last_task_id` / resume pollution caused by reusing the same `out-dir` for overlapping reruns
- you want one preset like `stable-batch` or `long-batch` instead of manually restating every rolling/backoff flag

Prerequisites:
- task triplet available
- LLM runtime for semantics-related steps

Why this is stable:
- it is the top-level batch coordinator for workflow 5.1
- it wraps the existing light-lane runner instead of duplicating lower-level semantics logic
- merged/top-level summaries surface extract-failure signatures and failure families for faster batch triage
- it supports rolling `warn|degrade|stop` behavior when cumulative extract failure rate becomes untrustworthy
- it can also back off automatically after one shard times out heavily by increasing next-shard LLM timeout and reducing next-shard size
- it can warn or stop on repeated extract failure families and emits `family_hotspots` / `quarantine_ranges` for later targeted reruns

### `py -3 scripts/python/run_single_task_light_lane.py --task-ids <id> --delivery-profile <profile> [--no-align-apply]`

Use when:
- a task needs workflow 5.1 semantics stabilization but you do not want to hand-stitch the lower-level commands
- you want resilient execution with task resume, timeout retry, extract-failure skip policy, and optional batch extract-first mode
- you want one rolling summary/log directory for a single task or a small ad-hoc batch

Prerequisites:
- task triplet available
- LLM runtime for semantics-related steps

Why this is stable:
- it is the direct wrapper for workflow 5.1 single-task / small-batch runs
- it supports read-only lane mode (`--no-align-apply`), `extract-first` batch mode, and resume from `summary.json`

### `py -3 scripts/python/merge_single_task_light_lane_summaries.py --date <YYYY-MM-DD>`

Use when:
- you split a full workflow 5.1 run into multiple `single-task-light-lane-v2*` directories
- you want one merged summary with transparent per-task source mapping

Prerequisites:
- one or more light-lane summary files already exist

Why this is stable:
- it provides the post-batch merge/report entrypoint for split workflow 5.1 runs
- it writes transparent source metadata instead of a path-only source list
- it hard-fails when merged completeness validation detects untrusted input coverage

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
