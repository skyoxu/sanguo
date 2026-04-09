# Template Upgrade Protocol

Purpose: define the **stable** migration protocol for moving a business repository onto newer template behavior.

This file is the durable protocol. Use `docs/workflows/business-repo-upgrade-guide.md` as the compare-range-specific report that tells you **what changed this time**.

## Inputs
1. Current target-repo state:
   - branch / git head
   - solution and project names
   - real `.taskmaster/tasks/*.json` presence
   - enabled workflows and secrets
2. Current template compare report:
   - `docs/workflows/business-repo-upgrade-guide.md`
3. Local business constraints:
   - product name / repo name
   - PRD-ID / overlay roots
   - domain contract locations
   - CI strictness and delivery profile defaults

## File Classes
- `safe-overwrite`
  - Template-generic scripts, schemas, docs, and tests with no project naming or domain binding.
- `merge-carefully`
  - Entry docs, AGENTS routing, CI workflows, README Quick Links, and any file already customized in the business repo.
- `localize-required`
  - Files containing repo name, solution name, product ID, PRD-ID, overlay root, export path, or project-specific runtime paths.
- `project-specific-do-not-copy`
  - Domain contracts, real gameplay overlays, real task triplet data, release identifiers, environment secrets, and store/platform metadata.
- `generated-or-ephemeral`
  - `logs/**`, temporary reports, replay outputs, generated baselines unless the protocol explicitly says to promote them.
- `recovery-sidecar-producers-and-consumers`
  - Treat task-scoped `latest.json`, `active-task`, `execution-context`, `repair-guide`, and their consumer scripts as one migration unit. Do not copy only the docs or only the reader script.
  - Recovery-facing stop-loss signals (`reason`, `reuse_mode`, `latest_summary_signals`, `chapter6_hints`, `rerun_guard`, `llm_retry_stop_loss`, `sc_test_retry_stop_loss`, `waste_signals`) must travel in the same batch.
  - If the upgraded template also exposes `recommended_action_why` or `needs-fix-fast`, migrate those reader-facing recovery hints in the same batch as the underlying stop-loss signals.
- `repo-health-foundation-bundle`
  - Treat `detect-project-stage`, `doctor-project`, `check-directory-boundaries`, `project-health-scan`, `serve-project-health`, their shared support modules, and the `run-local-hard-checks` prelude wiring as one migration unit. Do not copy only the dashboard doc or only the CLI entrypoints.
- `prototype-lane-docs`
  - `docs/workflows/prototype-lane.md`, `docs/prototypes/README.md`, and `docs/prototypes/TEMPLATE.md` are template-generic and can usually be copied as-is, but the business repo should still decide whether to activate the lane operationally.
- `entrypoint-routing-docs`
  - `docs/workflows/stable-public-entrypoints.md` and `docs/workflows/script-entrypoints-index.md` should travel with `README.md`, `AGENTS.md`, and `docs/PROJECT_DOCUMENTATION_INDEX.md` whenever the template updates the repo entry surface.

## Migration Order
1. Baseline and identity
   - Confirm the target repo already builds and that solution/project names are known.
   - Confirm whether `.taskmaster/tasks/*.json` are real or still template fallback.
2. Script/runtime foundation
   - Sync reusable `scripts/python/**`, `scripts/sc/**`, schemas, and helper tests.
   - Bring over any new dependencies referenced by those scripts in the same batch.
3. Repo-health bootstrap foundation
   - Sync `project-health` producers, `serve-project-health`, shared support modules, and the `dev_cli.py` / `local_hard_checks_support.py` prelude wiring in one batch.
   - Sync the companion docs and entry indexes (`docs/workflows/project-health-dashboard.md`, `docs/workflows/local-hard-checks.md`, `docs/workflows/stable-public-entrypoints.md`, `docs/workflows/script-entrypoints-index.md`, `README.md`, `AGENTS.md`, `docs/PROJECT_DOCUMENTATION_INDEX.md`) so operators can discover the new repo-level commands.
4. Recovery and sidecar protocol
   - Sync `latest.json` producers/consumers, `inspect_run.py`, `resume_task.py`, `active-task` behavior, marathon state, and repair-guide sidecars.
   - Keep stop-loss reasoning aligned across producer and consumer surfaces; do not migrate `run_review_pipeline.py` without the matching `inspect_run.py`, `resume_task.py`, `active-task`, and recovery docs.
5. Workflow and CI surface
   - Sync workflow changes only after local scripts are present.
   - Rebind paths, solution names, secrets, and delivery/security defaults.
6. Docs and routing
   - Update `AGENTS.md`, `README.md`, docs indexes, workflow docs, and the stable entrypoint docs so operators can discover the new behavior.
   - If the repo uses gate bundle docs, sync mirror-runtime gate docs together with the gate list.
7. Business-local adaptation
   - Rename project references, update overlay roots, adapt domain contract paths, and remove template fallback assumptions.
8. Validation and stop-loss
   - Run the minimum validation bundle before opening a PR.

## Required Localization Checklist
- Replace upstream source repository name with the business repo name.
- Replace solution / csproj names and runtime paths.
- If `Tests.Godot/Game.Godot` should point to a non-default runtime directory, localize the Junction target and workflow arguments together.
- Replace `PRD-Example` or template overlay roots with the business PRD IDs.
- Replace template fallback assumptions with real `.taskmaster/tasks/*.json` once the business repo has them.
- Re-check any script that references domain contracts, test roots, or project-relative resources.
- If the repo adopts the project-health dashboard, verify the repo-level diagnostics still reflect business-local paths, solution names, and runtime expectations after localization.

## Tests.Godot Single-Source Runtime Protocol
Problem:
- If `Tests.Godot/Game.Godot` becomes a normal copied directory instead of a Junction to the real `Game.Godot`, tests can silently read stale scripts/resources.
- This usually passes in long-lived local clones but fails or drifts in clean CI checkouts.
- Text references to `Tests.Godot/Game.Godot/**` are also dangerous because they encode the alias path instead of the real source of truth.

Durable solution:
1. Mirror path must stay ignored by git.
   - Keep `.gitignore` entries for `Tests.Godot/Game.Godot/` and `Tests.Godot/Game.Godot/**`.
2. `Tests.Godot/Game.Godot` must be a Junction to the real runtime directory.
   - Standard template target is `<repo>/Game.Godot`.
   - If the business repo uses another runtime directory name, localize the target but keep the single-source rule.
3. `scripts/python/run_gdunit.py` must hard-fail before Godot invocation when the Junction is missing or points to the wrong target.
   - Copy the matching helper script in the same batch: `ensure_tests_godot_junction.py` or `ensure_tests_project_junction.py`, depending on the repo generation.
4. CI should prepare the Junction before GdUnit runs.
   - Use `scripts/ci/prepare_gd_tests.ps1` where the workflow still has an explicit prepare step.
   - Even if the workflow prepares it, keep the `run_gdunit.py` hard check as the final stop-loss.
5. Add both hard gates when the repo uses gate bundle style checks.
   - `scripts/python/forbid_mirror_path_refs.py` blocks source text that points to `Tests.Godot/Game.Godot/**`.
   - `scripts/python/audit_tests_godot_mirror_git_tracking.py` blocks git-tracked mirror files that would re-create a copied directory in clean clones.
6. Update workflow and docs together.
   - If the repo uses `scripts/python/run_gate_bundle.py`, wire both mirror-related gates into the hard gate list.
   - Update `docs/workflows/gate-bundle.md` so script and doc order stay consistent.

Minimum validation:
- `py -3 scripts/python/ensure_tests_godot_junction.py --root . --tests-project Tests.Godot --link-name Game.Godot --target-rel Game.Godot`
- `py -3 scripts/python/audit_tests_godot_mirror_git_tracking.py --root .`
- `py -3 scripts/python/run_gdunit.py --prewarm --godot-bin $env:GODOT_BIN --project Tests.Godot`
## Validation Sequence
1. Repo-health bootstrap parity
   - `py -3 scripts/python/dev_cli.py project-health-scan`
   - `py -3 scripts/python/dev_cli.py serve-project-health`
   - Verify `logs/ci/project-health/latest.json`, `latest.html`, and `server.json` match the documented outputs.
2. Deterministic local checks
   - `py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin $env:GODOT_BIN`
3. Task-scoped review pipeline on at least one real task
   - `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin $env:GODOT_BIN`
4. Task metadata / overlay / contract integrity
   - `py -3 scripts/python/validate_task_master_triplet.py`
   - `py -3 scripts/python/check_tasks_all_refs.py`
   - `py -3 scripts/python/validate_contracts.py`
5. Delivery-profile-sensitive checks when enabled
   - `py -3 scripts/python/run_gate_bundle.py --mode hard`
6. Tests.Godot single-source runtime checks when the repo uses `Tests.Godot` + `Game.Godot`
   - `py -3 scripts/python/ensure_tests_godot_junction.py --root . --tests-project Tests.Godot --link-name Game.Godot --target-rel Game.Godot`
   - `py -3 scripts/python/audit_tests_godot_mirror_git_tracking.py --root .`
7. Task-local TDD preflight when the repo uses `scripts/sc/build/tdd.py`
   - `py -3 -m unittest scripts.sc.tests.test_build_tdd_orchestration scripts.sc.tests.test_build_tdd_task_preflight`
8. Recovery sidecar regression when the repo uses task-scoped review pipeline
   - `py -3 -m unittest scripts.sc.tests.test_pipeline_sidecar_protocol scripts.sc.tests.test_resume_task`

## Stop-Loss Rules
- Do not copy compare-specific conclusions into stable docs without extracting the durable rule first.
- Do not overwrite business task triplet files with template examples.
- Do not copy project names, PRD IDs, or solution paths blindly.
- Do not wire new workflows until all referenced local scripts exist.
- If a copied script introduces a new dependency, copy or adapt that dependency in the same migration step.
- Do not treat repo-health docs as sufficient migration by themselves; copy the shared support modules, tests, `run-local-hard-checks` prelude wiring, and the stable entrypoint docs in the same batch.
- Do not wire `serve-project-health` into CI; it is a local operator entrypoint only.
- Do not copy `README.md` Quick Links or agent routing changes without also copying `docs/workflows/stable-public-entrypoints.md` and `docs/workflows/script-entrypoints-index.md` when those links are referenced.
- Do not treat `active-task` as a replacement for `resume-task`; it is a short recovery pointer layered above the canonical recovery entrypoint.
- Do not migrate new recovery stop-loss signals in code only. If `rerun_guard`, `llm_retry_stop_loss`, `sc_test_retry_stop_loss`, or `waste_signals` semantics change, sync the producer, consumer, docs, and regression tests together.
- Do not move prototype work into formal task triplet completion without an explicit promotion step.
- Do not enable task-local TDD preflight blindly if the business repo's `contractRefs` semantics intentionally differ from the template's path-aware rule.
- Do not treat a copied `Tests.Godot/Game.Godot` directory as acceptable technical debt; if git tracks mirror files, fix the index and restore the Junction before trusting GdUnit results.

## Relationship To Compare Reports
- `template-upgrade-protocol.md`
  - Stable SSoT for **how** to upgrade.
- `business-repo-upgrade-guide.md`
  - Time-bound record of **what changed in one compare range**.
