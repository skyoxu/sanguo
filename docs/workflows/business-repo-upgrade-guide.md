# Business Repo Upgrade Guide

## Scope

- Base compare wave: `origin/main` (`125d7f1`) -> template migration wave rooted at `883f69e`
- Addendum wave: repo-health / dashboard / local-hard-checks prelude updates accumulated through the current template working tree on `2026-03-25`
- Goal: let sibling business repositories upgrade to the current template branch and gain the same environment, scripts, sidecar protocol, recovery assets, docs, and workflow-facing behavior.
- Durable protocol: `docs/workflows/template-upgrade-protocol.md` defines the stable migration rules; this file records the current cumulative migration surface a business repo must absorb to match the latest template behavior.

## Hard Facts First

1. There is **no direct `.github/workflows/**` diff** in this compare range.
2. There is **no package-manifest / project-file diff** in this compare range (`requirements*`, `pyproject*`, `package*.json`, `*.csproj`, `Directory.Packages.props`).
3. The upgrade is therefore mainly about:
   - new script bundles and their internal dependencies
   - new sidecar schemas and recovery artifacts
   - new task-view fields and template fallback rules
   - new docs, agent routing, and migration guidance
   - repo-health bootstrap commands, dashboard output, and local-hard-checks prelude wiring
4. If a business repo is older than `origin/main`, do **not** jump straight to this migration surface. First align that repo to current `main`, then apply this delta.

## What A Business Repo Gets After Full Migration

1. Persistent local harness runs with sidecars, latest pointers, replay/inspect support, and marathon recovery state.
2. Task-level TDD now has a lightweight `task_preflight` stage before the heavier analyze/context gates. It checks only the current task's overlay and `contractRefs` resolution so a business repo can fail fast on broken task-local metadata without running repo-wide hard gates.
3. Task-scoped review pipeline runs now write stable `active-task` sidecars under `logs/ci/active-tasks/`, and `resume_task.py` consumes them before falling back to deeper artifact inspection. This gives business repos a shorter recovery path after context reset without changing the canonical `resume-task` entrypoint.
4. Recovery consumers now surface explicit Chapter 6 stop-loss reasoning from task-scoped artifacts, including `rerun_guard`, `llm_retry_stop_loss`, `sc_test_retry_stop_loss`, and `waste_signals`, so operators can avoid paying for another wasteful full rerun.
5. Recovery readers should also surface `recommended_action_why`; when the resolved action is `needs-fix-fast`, business repos should prefer targeted closure instead of reopening a full rerun.
4. Docs and routing now distinguish between:
   - compare-range migration reports (`business-repo-upgrade-guide.md`),
   - stable migration protocol (`template-upgrade-protocol.md`),
   - directory responsibility routing (`docs/agents/16-directory-responsibilities.md`),
   - and exploration-vs-delivery separation (`docs/workflows/prototype-lane.md`, `docs/prototypes/`).
5. Prototype work now has an explicit pre-task lane. This is intentionally separate from `DELIVERY_PROFILE`; business repos should not use prototype artifacts as completed formal task output.
6. A repo-scoped hard-check entrypoint: `py -3 scripts/python/dev_cli.py run-local-hard-checks`.
7. A task-scoped unified review entrypoint with profile-aware review behavior: `py -3 scripts/sc/run_review_pipeline.py`.
8. Consumer-driven sidecar schemas for execution context, repair guide, latest pointer, harness capabilities, approval requests, and run events.
9. Delivery-profile-driven runtime behavior across `sc-test`, `tdd`, acceptance, run-review-pipeline, and LLM semantic gates.
10. Task-level `semantic_review_tier` hints in task views, with stop-loss escalation rules.
11. Unified low-priority technical debt sync into `docs/technical-debt.md`.
12. Strict acceptance test generation with red-first verification and deterministic C# conventions gate.
13. Split `sc-test` / `tdd` orchestration helpers and stronger task-ref resolution, including template fallback from `.taskmaster/tasks` to `examples/taskmaster`.
14. Overlay generation tooling for PRD -> Overlay 08 scaffold and repair flows.
15. Recovery-doc scaffolding and validation for `execution-plans/` and `decision-logs/`.
16. Repo-scoped health commands and a lightweight local dashboard: `detect-project-stage`, `doctor-project`, `check-directory-boundaries`, `project-health-scan`, and `serve-project-health`.
17. `run-local-hard-checks` now begins with a deterministic repo-health prelude and writes/refreshes `logs/ci/project-health/latest.json` plus `latest.html` before the hard validation chain.
18. A decomposed `AGENTS.md` plus `docs/agents/**` knowledge map instead of one oversized root instruction file.

## Migration Strategy

### Phase 0: Baseline And Identity

Do this before copying files:

1. Confirm the target business repo is already aligned to current template `main` behavior.
2. Confirm the repo has a real Taskmaster triplet under `.taskmaster/tasks/`.
3. Decide the default delivery posture in `scripts/sc/config/delivery_profiles.json`.
4. Decide whether the repo wants full parity, or only the mandatory bundles below.

Mandatory business-repo adaptations after file copy:

1. Replace template fallback assumptions with real `.taskmaster/tasks/tasks.json`, `.taskmaster/tasks/tasks_back.json`, `.taskmaster/tasks/tasks_gameplay.json`.
2. Move `semantic_review_tier` examples into the real `tasks_back.json` / `tasks_gameplay.json`, not `examples/taskmaster/**`.
3. Rename any upstream source repository names, PRD examples, and project identity strings in `AGENTS.md`, `docs/agents/**`, `README.md`, and bootstrap docs.
4. Keep `docs/technical-debt.md` in-repo, because the review pipeline now writes to it.

### Phase 1: Recovery Assets And Agent Routing

Copy these first as one bundle:

1. `AGENTS.md`
2. `docs/agents/**`
3. `execution-plans/**`
4. `decision-logs/**`
5. `scripts/python/_recovery_doc_scaffold.py`
6. `scripts/python/new_execution_plan.py`
7. `scripts/python/new_decision_log.py`
8. `scripts/python/validate_recovery_docs.py`

Reason:

- Without these files, the later harness and review-pipeline sidecars exist, but the repository still lacks a recovery model and durable session restart docs.

### Phase 2: Repo-Scoped Local Hard Checks Harness

Copy this bundle together:

1. `scripts/python/dev_cli.py`
2. `scripts/python/dev_cli_builders.py`
3. `scripts/python/local_hard_checks_harness.py`
4. `scripts/python/local_hard_checks_support.py`
5. `scripts/python/quality_gates.py`
6. `scripts/python/quality_gates_builders.py`
7. `scripts/python/run_gate_bundle.py`
8. `scripts/python/inspect_run.py`
9. `scripts/sc/_artifact_schema.py`
10. `scripts/sc/_artifact_schema_fallback.py`
11. `scripts/sc/_sidecar_schema.py`
12. `scripts/sc/_summary_schema.py`
13. `scripts/sc/_summary_schema_fallback.py`
14. `scripts/sc/_summary_schema_local_hard_checks.py`
15. `scripts/sc/_failure_taxonomy.py`
16. `scripts/sc/_harness_capabilities.py`
17. `scripts/sc/schemas/sc-local-hard-checks-*.schema.json`
18. `scripts/sc/schemas/sc-harness-capabilities.schema.json`
19. `scripts/sc/schemas/sc-run-event.schema.json`
20. `docs/workflows/local-hard-checks.md`
21. `docs/workflows/run-protocol.md`
22. `docs/workflows/harness-boundary-matrix.md`
23. `docs/workflows/examples/sc-run-events.example.jsonl`

Reason:

- `dev_cli.py run-local-hard-checks` is no longer just a shell wrapper. It writes sidecars, latest pointers, repair guides, and replayable run events.
- If you copy the producer but miss the schemas, later schema validation and replay tooling will drift.
- This harness phase is no longer self-contained: in the latest template it depends on the repo-health prelude bundle below.

### Phase 2A: Repo-Health Dashboard And Bootstrap Stop-Loss

Copy this bundle in the same migration wave as Phase 2:

1. `scripts/python/_project_health_common.py`
2. `scripts/python/_project_health_checks.py`
3. `scripts/python/_project_health_support.py`
4. `scripts/python/_project_health_server.py`
5. `scripts/python/detect_project_stage.py`
6. `scripts/python/doctor_project.py`
7. `scripts/python/check_directory_boundaries.py`
8. `scripts/python/project_health_scan.py`
9. `scripts/python/serve_project_health.py`
10. `scripts/python/dev_cli.py`
11. `scripts/python/dev_cli_builders.py`
12. `scripts/python/local_hard_checks_support.py`
13. `scripts/sc/_summary_schema_local_hard_checks.py`
14. `scripts/sc/schemas/sc-local-hard-checks-summary.schema.json`
15. `scripts/sc/tests/test_dev_cli_project_health_commands.py`
16. `scripts/sc/tests/test_project_health_support.py`
17. `scripts/sc/tests/test_project_health_server.py`
18. `scripts/sc/tests/test_local_hard_checks_harness.py`
19. `docs/workflows/project-health-dashboard.md`
20. `docs/workflows/local-hard-checks.md`
21. `docs/workflows/stable-public-entrypoints.md`
22. `docs/workflows/script-entrypoints-index.md`
23. `README.md`
24. `AGENTS.md`
25. `docs/PROJECT_DOCUMENTATION_INDEX.md`

Reason:

- `project-health-scan` is now the repo bootstrap stop-loss point. A business repo that skips this bundle can still run older hard checks, but it will not match the latest template behavior.
- `run-local-hard-checks` now refreshes project-health records before the hard gate chain. If you copy only the docs or only the Python entrypoints, operators lose discoverability or the harness silently diverges.
- `serve-project-health` is intentionally local-only. Do not wire it into CI, but do copy the script and doc so developers get the stable `127.0.0.1` dashboard entrypoint.
- The updated `README.md`, `AGENTS.md`, `docs/PROJECT_DOCUMENTATION_INDEX.md`, `docs/workflows/stable-public-entrypoints.md`, and `docs/workflows/script-entrypoints-index.md` are part of the migration surface because they expose the new repo-level commands and stable script entrypoints to humans and agents.

### Phase 3: Task-Scoped Review Pipeline, Repair Guidance, And Marathon Recovery

- New in the current template wave:
  - `scripts/sc/_active_task_sidecar.py`
  - `logs/ci/active-tasks/task-<id>.active.json`
  - `logs/ci/active-tasks/task-<id>.active.md`
- Migration impact:
  - Copy the producer (`run_review_pipeline.py`, `_pipeline_session.py`, `_active_task_sidecar.py`) and the consumer (`scripts/python/resume_task.py`) in the same batch.
  - Do not copy only the docs or only the consumer; the value depends on producer and consumer both existing.
  - If the target repo wants full Chapter 6 parity, also copy the stop-loss readers (`scripts/python/inspect_run.py`) and the docs that explain those signals (`workflow.md`, `docs/agents/00-index.md`, `docs/agents/01-session-recovery.md`, `docs/workflows/stable-public-entrypoints.md`, `docs/workflows/run-protocol.md`).
  - The task recovery default command remains `py -3 scripts/python/dev_cli.py resume-task --task-id <id>`.
  - `active-task` is a shorter summary sidecar, not a replacement for the canonical recovery entrypoint.

Copy this bundle together:

1. `scripts/sc/run_review_pipeline.py`
2. `scripts/sc/_pipeline_approval.py`
3. `scripts/sc/_pipeline_events.py`
4. `scripts/sc/_pipeline_helpers.py`
5. `scripts/sc/_pipeline_plan.py`
6. `scripts/sc/_pipeline_session.py`
7. `scripts/sc/_pipeline_support.py`
8. `scripts/sc/_repair_approval.py`
9. `scripts/sc/_repair_guidance.py`
10. `scripts/sc/_repair_recommendations.py`
11. `scripts/sc/_agent_review_contract.py`
12. `scripts/sc/_agent_review_policy.py`
13. `scripts/sc/_approval_contract.py`
14. `scripts/sc/agent_to_agent_review.py`
15. `scripts/sc/_marathon_policy.py`
16. `scripts/sc/_marathon_state.py`
17. `scripts/sc/_llm_review_tier.py`
18. `scripts/sc/_technical_debt.py`
19. `scripts/sc/schemas/sc-review-*.schema.json`
20. `scripts/sc/schemas/sc-approval-*.schema.json`
21. `docs/technical-debt.md`
22. `scripts/sc/tests/test_pipeline_sidecar_protocol.py`
23. `scripts/sc/tests/test_repair_guidance.py`
24. `scripts/sc/tests/test_run_artifact_schema_and_inspect.py`
25. `scripts/sc/tests/test_run_review_pipeline_delivery_profile.py`
26. `scripts/sc/tests/test_run_review_pipeline_marathon.py`
27. `scripts/sc/tests/test_agent_review_contract.py`
28. `scripts/sc/tests/test_agent_review_policy.py`
29. `scripts/sc/tests/test_agent_to_agent_review.py`
30. `scripts/sc/tests/test_llm_review_tier.py`
31. `scripts/sc/tests/test_review_technical_debt.py`

Reason:

- This is the main new harness capability in the branch.
- The pipeline now produces `execution-context.json`, `repair-guide.json`, `repair-guide.md`, `run-events.jsonl`, `harness-capabilities.json`, approval sidecars, and marathon state.
- The pipeline also writes `P2/P3/P4` findings into `docs/technical-debt.md` and reads `semantic_review_tier` from task views.

### Phase 4: `sc-test`, TDD, Acceptance-Test Generation, And C# Conventions Hard Gate

- New in the current template wave:
  - `scripts/sc/build/tdd.py` now calls a task-local `task_preflight` stage.
  - `scripts/sc/build/_tdd_steps.py` now resolves and checks `master.overlay`, `overlay_refs`, and path-like `contractRefs` before the heavier context gates.
- Migration impact:
  - Copy both the orchestrator and helper in the same batch.
  - Copy the matching tests so future drift is visible.
  - If the business repo uses non-path `contractRefs` semantics only, review the path-detection rule before enabling the same behavior unchanged.

- New in the current template wave (Tests.Godot single-source runtime hardening):
  - `scripts/python/audit_tests_godot_mirror_git_tracking.py` is now part of the mirror-runtime stop-loss set.
  - The durable rule is: `Tests.Godot/Game.Godot` must stay a Junction to the real `Game.Godot`, not a copied mirror directory.
- Migration impact:
  - If the business repo already has `forbid_mirror_path_refs.py`, do not stop there; also copy and wire `audit_tests_godot_mirror_git_tracking.py`.
  - If the business repo already has `run_gdunit.py` Junction enforcement, that only protects runtime resolution; the new audit gate protects git index hygiene in fresh clones.
  - If the business repo uses `run_gate_bundle.py`, add the audit script to hard gates and update `docs/workflows/gate-bundle.md` in the same batch.
  - If the business repo does not use gate bundle yet, wire the audit script directly into the deterministic CI stage until gate bundle becomes the canonical path.

Copy this bundle together:

1. `scripts/sc/test.py`
2. `scripts/sc/_sc_test_refs.py`
3. `scripts/sc/_sc_test_steps.py`
4. `scripts/sc/build/tdd.py`
5. `scripts/sc/build/_tdd_steps.py`
6. `scripts/python/_csharp_test_conventions.py`
7. `scripts/python/check_csharp_test_conventions.py`
8. `scripts/sc/llm_generate_tests_from_acceptance_refs.py`
9. `scripts/sc/_acceptance_testgen_flow.py`
10. `scripts/sc/_acceptance_testgen_llm.py`
11. `scripts/sc/_acceptance_testgen_quality.py`
12. `scripts/sc/_acceptance_testgen_red.py`
13. `scripts/sc/_acceptance_testgen_refs.py`
14. `scripts/sc/tests/test_build_tdd_orchestration.py`
15. `scripts/sc/tests/test_sc_test_orchestration.py`
16. `scripts/sc/tests/test_sc_test_refs.py`
17. `scripts/sc/tests/test_check_csharp_test_conventions.py`
18. `scripts/sc/tests/test_generate_tests_from_acceptance_refs.py`
19. `scripts/sc/tests/test_acceptance_testgen_quality.py`
20. `scripts/sc/tests/test_acceptance_testgen_red.py`
21. `docs/testing-framework.md`
22. `docs/migration/Phase-10-Unit-Tests.md`

Also copy this mirror-runtime hardening bundle when the business repo uses `Tests.Godot` + `Game.Godot`:

1. `scripts/python/audit_tests_godot_mirror_git_tracking.py`
2. `scripts/python/forbid_mirror_path_refs.py`
3. `scripts/python/run_gdunit.py`
4. `scripts/python/ensure_tests_godot_junction.py` (or the older `ensure_tests_project_junction.py` in earlier repo generations)
5. `scripts/ci/prepare_gd_tests.ps1`
6. `docs/workflows/gate-bundle.md`

Reason:

- `llm_generate_tests_from_acceptance_refs.py` is no longer a loose scaffold helper. It enforces red-first behavior, anchor placement, task-scoped verification, and deterministic C# naming/content rules.
- `scripts/sc/test.py` now depends on helper modules and task-view resolution logic, including template fallback.

### Phase 5: Overlay Generation Toolchain

Copy this bundle together:

1. `scripts/sc/llm_generate_overlays_batch.py`
2. `scripts/sc/llm_generate_overlays_from_prd.py`
3. `scripts/sc/_overlay_generator_batch.py`
4. `scripts/sc/_overlay_generator_contract.py`
5. `scripts/sc/_overlay_generator_diff.py`
6. `scripts/sc/_overlay_generator_markdown_patch.py`
7. `scripts/sc/_overlay_generator_model.py`
8. `scripts/sc/_overlay_generator_patch.py`
9. `scripts/sc/_overlay_generator_prompting.py`
10. `scripts/sc/_overlay_generator_runtime.py`
11. `scripts/sc/_overlay_generator_scaffold.py`
12. `scripts/sc/_overlay_generator_scaffold_prompting.py`
13. `scripts/sc/_overlay_generator_support.py`
14. `scripts/python/sync_task_overlay_refs.py`
15. `scripts/python/validate_overlay_execution.py`
16. `docs/workflows/overlay-generation-quickstart.md`
17. `docs/workflows/overlay-generation-sop.md`
18. `docs/workflows/overlays-authoring-guide.md`

Reason:

- This is the branch's biggest new authoring workflow outside the harness itself.
- Business repos with active PRD waves can now dry-run, simulate, repair, diff, and apply overlay pages in a controlled sequence.

### Phase 6: Delivery Profile And Documentation Surface

- New in the current template wave:
  - `docs/agents/16-directory-responsibilities.md`
  - `docs/workflows/template-upgrade-protocol.md`
  - `docs/workflows/prototype-lane.md`
  - `docs/prototypes/README.md`
  - `docs/prototypes/TEMPLATE.md`
- Migration impact:
  - Sync the new docs and update `AGENTS.md`, `README.md`, the documentation indexes, and the stable entrypoint docs in the same batch.
  - `business-repo-upgrade-guide.md` should continue to record compare-specific changes; `template-upgrade-protocol.md` is the long-lived protocol SSoT.
  - Prototype lane docs are recommended even for business repos that currently do not use the lane, because they prevent future confusion between exploration work and formal delivery profiles.

Copy these files together:

1. `README.md`
2. `DELIVERY_PROFILE.md`
3. `scripts/sc/config/delivery_profiles.json`
4. `scripts/sc/README.md`
5. `docs/PROJECT_DOCUMENTATION_INDEX.md`
6. `docs/PROJECT_CAPABILITIES_STATUS.md`
7. `docs/workflows/stable-public-entrypoints.md`
8. `docs/workflows/script-entrypoints-index.md`
9. `docs/workflows/template-bootstrap-checklist.md`
10. `docs/workflows/gate-bundle.md`
11. `docs/architecture/base/07-dev-build-and-gates-v2.md`
12. `docs/migration/Phase-13-Quality-Gates-Backlog.md`
13. `docs/migration/Phase-13-Quality-Gates-Script.md`

Reason:

- These files explain the new runtime control plane and how the rest of the scripts should be consumed.
- The branch formalizes `playable-ea`, `fast-ship`, and `standard` as real execution profiles, not just docs language.

### Phase 7: Optional / Project-Specific Bundles

These files are in the diff and are safe to copy, but they should be enabled intentionally:

1. Obligations / semantic freeze tooling:
   - `scripts/python/_obligations_freeze_pipeline_common.py`
   - `scripts/python/_obligations_freeze_pipeline_runner.py`
   - `scripts/python/rerun_obligations_hardgate_round3.py`
   - `scripts/sc/_obligations_main_flow.py`
   - `scripts/sc/_obligations_text_rules.py`
   - `scripts/sc/_subtasks_coverage_llm.py`
   - modified `scripts/sc/llm_extract_task_obligations.py`
   - modified `scripts/sc/llm_check_subtasks_coverage.py`
   - modified `scripts/sc/_obligations_guard.py`
2. Domain / repo-shape guards:
   - `scripts/python/config_contract_sync_check.py`
   - `scripts/python/guard_archived_overlays.py`
3. Encoding / docs hard checks:
   - `scripts/python/validate_docs_utf8_no_bom.py`

Reason:

- These are valuable, but they depend more on the target repo's domain model, archived overlay policy, and tolerance for extra local hard gates.

## Workflow Impact

There is no YAML diff under `.github/workflows/**` in this compare range.

That does **not** mean "no workflow impact". It means the impact is indirect:

1. Existing CI entrypoints now point to richer script behavior.
2. Delivery-profile docs expect workflow inputs and Step Summary lines to exist.
3. Business repos that diverged from template `main` should first backport the current `main` workflows, then apply this branch delta.

Practical rule:

1. If a business repo already matches current template `main` workflows, no extra workflow copy is required for this branch delta.
2. If it does not, align workflows first, or the new script surface will exist without the same CI entry behavior.

## External Dependencies And Runtime Assumptions

No new package manifests changed in this compare range.

The new capabilities still assume the repo already has:

1. `py -3` on Windows.
2. `git` available on PATH.
3. `.NET 8 SDK` for `dotnet`-backed gates.
4. a Godot .NET console binary when running GdUnit or strict smoke locally.
5. the repo's existing LLM runtime / CLI setup if you want to use `llm_*` scripts.

New persistent in-repo data dependencies introduced by this branch:

1. `docs/technical-debt.md`
2. `execution-plans/**`
3. `decision-logs/**`
4. `logs/ci/**` sidecars written by `run_review_pipeline.py` and `run-local-hard-checks`
5. `scripts/sc/schemas/**` as executable schema SSoT for sidecars

## Business-Repo Validation Checklist After Migration

Run these on Windows after copying and adapting the files:

1. Recovery docs scaffold and validation:
   - `py -3 scripts/python/dev_cli.py new-execution-plan --slug migration-smoke`
   - `py -3 scripts/python/dev_cli.py new-decision-log --slug migration-smoke`
   - `py -3 scripts/python/validate_recovery_docs.py --dir all`
2. Encoding/doc surface:
   - `py -3 scripts/python/validate_docs_utf8_no_bom.py`
3. Repo-scoped hard checks:
   - `py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin C:\Godot\Godot_v4.5.1-stable_mono_win64_console.exe`
   - `py -3 scripts/python/inspect_run.py --kind local-hard-checks`
4. Task-scoped review pipeline:
   - `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --skip-llm-review`
   - `py -3 scripts/python/inspect_run.py --kind pipeline --task-id <id>`
5. Acceptance-test generation and C# conventions:
   - `py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify auto --godot-bin "$env:GODOT_BIN"`
   - `py -3 scripts/python/check_csharp_test_conventions.py --task-id <id>`
6. Overlay generation dry-run:
   - `py -3 scripts/sc/llm_generate_overlays_batch.py --prd <path> --prd-id <PRD-ID> --prd-docs <csv> --page-family core --page-mode scaffold --timeout-sec 1200 --dry-run --batch-suffix migration-smoke`
7. Repo-health bootstrap parity:
   - `py -3 scripts/python/dev_cli.py project-health-scan`
   - `py -3 scripts/python/dev_cli.py serve-project-health`
   - Verify `logs/ci/project-health/latest.json`, `latest.html`, and `server.json` are produced as documented.

## Commit Clusters In This Compare Range

Use these commit subjects as a sanity check when reviewing whether the target repo already absorbed some bundles:

- `defb3d6 docs(sc): align delivery profile guidance`
- `688e99f feat(sc): harden acceptance test generation flow`
- `9419912 feat(sc): add review tier and technical debt sync`
- `dc34638 feat(sc): add csharp test conventions hard gate`
- `b07138d feat(overlay): add templateized overlay generation toolchain`
- `131a692 docs(harness): templateize task-id placeholders`
- `731cec8 feat(harness): add sidecar inspect and consumer contracts`
- `ee018ea feat(dev-cli): protocolize local hard checks harness`
- `2428703 feat(dev-cli): add local hard checks workflow`
- `0e0dfff docs(harness): add boundary matrix for template cutline`
- `304505b feat(dev-cli): expose recovery doc scaffold commands`
- `fce1370 feat(recovery): scaffold execution plans and decision logs`
- ... and 20 more commits in this compare range

## File Inventory Summary

- Root / Top-Level Docs: 3 files in the original compare wave, plus updated entry docs in the repo-health addendum wave
- docs/**: original compare-wave docs plus repo-health dashboard / routing refresh docs
- decision-logs/**: 4 files
- execution-plans/**: 4 files
- examples/taskmaster/**: 2 files
- scripts/python/**: original compare-wave script bundle plus repo-health support / dashboard scripts
- scripts/sc/**: original compare-wave bundle plus updated local-hard-checks harness schema wiring
- scripts/sc/build/**: 2 files
- scripts/sc/schemas/**: original compare-wave schemas plus updated local-hard-checks summary schema
- scripts/sc/tests/**: original compare-wave tests plus repo-health regression tests

## Addendum: Repo-Health Wave After The Original Compare Range

```text
M AGENTS.md
M README.md
M docs/PROJECT_DOCUMENTATION_INDEX.md
A docs/workflows/project-health-dashboard.md
M docs/workflows/local-hard-checks.md
M scripts/python/dev_cli.py
M scripts/python/dev_cli_builders.py
M scripts/python/local_hard_checks_support.py
A scripts/python/_project_health_common.py
A scripts/python/_project_health_checks.py
A scripts/python/_project_health_support.py
A scripts/python/_project_health_server.py
A scripts/python/detect_project_stage.py
A scripts/python/doctor_project.py
A scripts/python/check_directory_boundaries.py
A scripts/python/project_health_scan.py
A scripts/python/serve_project_health.py
M scripts/sc/_summary_schema_local_hard_checks.py
M scripts/sc/schemas/sc-local-hard-checks-summary.schema.json
M scripts/sc/tests/test_local_hard_checks_harness.py
A scripts/sc/tests/test_dev_cli_project_health_commands.py
A scripts/sc/tests/test_project_health_support.py
A scripts/sc/tests/test_project_health_server.py
```

## Appendix: Root / Top-Level Docs

```text
M AGENTS.md
M DELIVERY_PROFILE.md
M README.md
```

## Appendix: docs/**

```text
M docs/PROJECT_CAPABILITIES_STATUS.md
M docs/PROJECT_DOCUMENTATION_INDEX.md
A docs/agents/00-index.md
A docs/agents/01-session-recovery.md
A docs/agents/02-repo-map.md
A docs/agents/03-persistent-harness.md
A docs/agents/04-closed-loop-testing.md
A docs/agents/05-architecture-guardrails.md
A docs/agents/06-harness-marathon.md
A docs/agents/07-agent-to-agent-review.md
A docs/agents/08-project-basics.md
A docs/agents/09-quality-gates-and-done.md
A docs/agents/10-template-customization.md
A docs/agents/11-agents-construction-principles.md
A docs/agents/12-execution-rules.md
A docs/agents/13-rag-sources-and-session-ssot.md
A docs/agents/14-startup-stack-and-template-structure.md
A docs/agents/15-security-release-health-and-runtime-ops.md
M docs/architecture/base/07-dev-build-and-gates-v2.md
M docs/migration/Phase-10-Unit-Tests.md
M docs/migration/Phase-13-Quality-Gates-Backlog.md
M docs/migration/Phase-13-Quality-Gates-Script.md
A docs/technical-debt.md
M docs/testing-framework.md
A docs/workflows/examples/sc-run-events.example.jsonl
M docs/workflows/gate-bundle.md
A docs/workflows/harness-boundary-matrix.md
A docs/workflows/local-hard-checks.md
A docs/workflows/overlay-generation-quickstart.md
A docs/workflows/overlay-generation-sop.md
M docs/workflows/overlays-authoring-guide.md
A docs/workflows/run-protocol.md
A docs/workflows/template-bootstrap-checklist.md
```

## Appendix: decision-logs/**

```text
A decision-logs/2026-03-19-agent-review-sidecar-contract.md
A decision-logs/2026-03-19-agents-index-and-persistent-harness.md
A decision-logs/README.md
A decision-logs/TEMPLATE.md
```

## Appendix: execution-plans/**

```text
A execution-plans/2026-03-19-phase1-agent-harness-foundation.md
A execution-plans/2026-03-19-phase2-agent-review-sidecar.md
A execution-plans/README.md
A execution-plans/TEMPLATE.md
```

## Appendix: examples/taskmaster/**

```text
M examples/taskmaster/tasks_back.json
M examples/taskmaster/tasks_gameplay.json
```

## Appendix: scripts/python/**

```text
A scripts/python/_csharp_test_conventions.py
A scripts/python/_obligations_freeze_pipeline_common.py
A scripts/python/_obligations_freeze_pipeline_runner.py
A scripts/python/_recovery_doc_scaffold.py
A scripts/python/check_csharp_test_conventions.py
A scripts/python/config_contract_sync_check.py
M scripts/python/dev_cli.py
A scripts/python/dev_cli_builders.py
A scripts/python/guard_archived_overlays.py
A scripts/python/inspect_run.py
A scripts/python/local_hard_checks_harness.py
A scripts/python/local_hard_checks_support.py
A scripts/python/new_decision_log.py
A scripts/python/new_execution_plan.py
M scripts/python/quality_gates.py
A scripts/python/quality_gates_builders.py
A scripts/python/rerun_obligations_hardgate_round3.py
M scripts/python/run_gate_bundle.py
A scripts/python/sync_task_overlay_refs.py
A scripts/python/validate_docs_utf8_no_bom.py
A scripts/python/validate_overlay_execution.py
A scripts/python/validate_recovery_docs.py
```

## Appendix: scripts/sc/**

```text
M scripts/sc/README.md
A scripts/sc/_acceptance_testgen_flow.py
A scripts/sc/_acceptance_testgen_llm.py
A scripts/sc/_acceptance_testgen_quality.py
A scripts/sc/_acceptance_testgen_red.py
A scripts/sc/_acceptance_testgen_refs.py
A scripts/sc/_agent_review_contract.py
A scripts/sc/_agent_review_policy.py
A scripts/sc/_approval_contract.py
A scripts/sc/_artifact_schema.py
A scripts/sc/_artifact_schema_fallback.py
M scripts/sc/_delivery_profile.py
A scripts/sc/_env_evidence_helpers.py
M scripts/sc/_env_evidence_preflight.py
A scripts/sc/_failure_taxonomy.py
A scripts/sc/_harness_capabilities.py
A scripts/sc/_llm_review_tier.py
A scripts/sc/_marathon_policy.py
A scripts/sc/_marathon_state.py
M scripts/sc/_obligations_guard.py
A scripts/sc/_obligations_main_flow.py
A scripts/sc/_obligations_text_rules.py
A scripts/sc/_overlay_generator_batch.py
A scripts/sc/_overlay_generator_contract.py
A scripts/sc/_overlay_generator_diff.py
A scripts/sc/_overlay_generator_markdown_patch.py
A scripts/sc/_overlay_generator_model.py
A scripts/sc/_overlay_generator_patch.py
A scripts/sc/_overlay_generator_prompting.py
A scripts/sc/_overlay_generator_runtime.py
A scripts/sc/_overlay_generator_scaffold.py
A scripts/sc/_overlay_generator_scaffold_prompting.py
A scripts/sc/_overlay_generator_support.py
A scripts/sc/_pipeline_approval.py
A scripts/sc/_pipeline_events.py
A scripts/sc/_pipeline_helpers.py
A scripts/sc/_pipeline_plan.py
A scripts/sc/_pipeline_session.py
A scripts/sc/_pipeline_support.py
A scripts/sc/_repair_approval.py
A scripts/sc/_repair_guidance.py
A scripts/sc/_repair_recommendations.py
A scripts/sc/_sc_test_refs.py
A scripts/sc/_sc_test_steps.py
A scripts/sc/_sidecar_schema.py
A scripts/sc/_subtasks_coverage_llm.py
M scripts/sc/_summary_schema.py
M scripts/sc/_summary_schema_fallback.py
A scripts/sc/_summary_schema_local_hard_checks.py
A scripts/sc/_technical_debt.py
A scripts/sc/agent_to_agent_review.py
M scripts/sc/config/delivery_profiles.json
M scripts/sc/llm_check_subtasks_coverage.py
M scripts/sc/llm_extract_task_obligations.py
A scripts/sc/llm_generate_overlays_batch.py
A scripts/sc/llm_generate_overlays_from_prd.py
M scripts/sc/llm_generate_tests_from_acceptance_refs.py
M scripts/sc/run_review_pipeline.py
M scripts/sc/test.py
```

## Appendix: scripts/sc/build/**

```text
A scripts/sc/build/_tdd_steps.py
M scripts/sc/build/tdd.py
```

## Appendix: scripts/sc/schemas/**

```text
A scripts/sc/schemas/sc-approval-request.schema.json
A scripts/sc/schemas/sc-approval-response.schema.json
A scripts/sc/schemas/sc-harness-capabilities.schema.json
A scripts/sc/schemas/sc-local-hard-checks-execution-context.schema.json
A scripts/sc/schemas/sc-local-hard-checks-latest-index.schema.json
A scripts/sc/schemas/sc-local-hard-checks-repair-guide.schema.json
A scripts/sc/schemas/sc-local-hard-checks-summary.schema.json
A scripts/sc/schemas/sc-review-execution-context.schema.json
A scripts/sc/schemas/sc-review-latest-index.schema.json
A scripts/sc/schemas/sc-review-repair-guide.schema.json
A scripts/sc/schemas/sc-run-event.schema.json
```

## Appendix: scripts/sc/tests/**

```text
A scripts/sc/tests/test_acceptance_testgen_quality.py
A scripts/sc/tests/test_acceptance_testgen_red.py
A scripts/sc/tests/test_agent_review_contract.py
A scripts/sc/tests/test_agent_review_policy.py
A scripts/sc/tests/test_agent_to_agent_review.py
A scripts/sc/tests/test_build_tdd_orchestration.py
A scripts/sc/tests/test_check_csharp_test_conventions.py
A scripts/sc/tests/test_dev_cli_ci_entrypoints.py
A scripts/sc/tests/test_dev_cli_recovery_commands.py
M scripts/sc/tests/test_env_evidence_preflight.py
M scripts/sc/tests/test_gate_bundle_template.py
A scripts/sc/tests/test_generate_tests_from_acceptance_refs.py
A scripts/sc/tests/test_llm_review_tier.py
A scripts/sc/tests/test_local_hard_checks_harness.py
A scripts/sc/tests/test_marathon_policy.py
A scripts/sc/tests/test_overlay_generator_batch.py
A scripts/sc/tests/test_overlay_generator_diff.py
A scripts/sc/tests/test_overlay_generator_flow.py
A scripts/sc/tests/test_overlay_generator_markdown_patch.py
A scripts/sc/tests/test_overlay_generator_model.py
A scripts/sc/tests/test_overlay_generator_patch.py
A scripts/sc/tests/test_overlay_generator_prompting.py
A scripts/sc/tests/test_overlay_generator_scaffold.py
A scripts/sc/tests/test_overlay_generator_scaffold_prompting.py
A scripts/sc/tests/test_overlay_generator_support.py
A scripts/sc/tests/test_pipeline_sidecar_protocol.py
A scripts/sc/tests/test_quality_gates_entrypoint.py
A scripts/sc/tests/test_recovery_doc_scaffold.py
A scripts/sc/tests/test_repair_guidance.py
A scripts/sc/tests/test_review_technical_debt.py
A scripts/sc/tests/test_run_artifact_schema_and_inspect.py
M scripts/sc/tests/test_run_review_pipeline_delivery_profile.py
A scripts/sc/tests/test_run_review_pipeline_marathon.py
A scripts/sc/tests/test_sc_test_orchestration.py
A scripts/sc/tests/test_sc_test_refs.py
```
