# Script Entrypoints Index

Generated from source scan on `2026-03-25`. This document inventories recurring workflow-facing executable scripts under `scripts/python/**`, `scripts/sc/**`, and `scripts/sc/build/**`. Internal helper modules (`_*.py`), test files, and one-off maintenance utilities are intentionally excluded.

## Scope

- Goal: give operators and business repos one place to discover workflow-facing script names, paths, repo-local dependencies, and parameter prerequisites.
- Entry script rule: a file is treated as an entrypoint only if it contains a direct `__main__` block, lives under the workflow script roots above, and is not excluded by the stop-loss rules below.
- Dependency scope: only repo-local Python dependencies under `scripts/**` are listed. Standard library and third-party packages are intentionally not expanded here.
- Parameter prerequisite scope: this document records when a parameter family is meaningful. It does not replace each script's own `--help`.

## Exclusion Policy

- Exclude backup/encoding recovery utilities under `scripts/ci/**`.
- Exclude sibling-repo sync, one-off migration, and doc cleanup helpers that are not part of the recurring operator workflow.
- Keep recurring maintenance commands that are already referenced by `workflow.md`, `workflow.example.md`, `README.md`, or the upgrade protocol.

### Excluded One-Off Entrypoints

- `scripts/ci/convert_to_utf8.py`: Encoding recovery and backup scripts live here; they are maintenance utilities, not recurring workflow entrypoints.
- `scripts/ci/fix_encoding_from_backup.py`: Encoding recovery and backup scripts live here; they are maintenance utilities, not recurring workflow entrypoints.
- `scripts/ci/restore_from_backup.py`: Encoding recovery and backup scripts live here; they are maintenance utilities, not recurring workflow entrypoints.
- `scripts/ci/safe_utf8_conversion.py`: Encoding recovery and backup scripts live here; they are maintenance utilities, not recurring workflow entrypoints.
- `scripts/ci/smart_encoding_repair.py`: Encoding recovery and backup scripts live here; they are maintenance utilities, not recurring workflow entrypoints.
- `scripts/python/config_contract_sync_check.py`: Domain-specific consistency checker; not part of the template's recurring workflow.
- `scripts/python/decouple_task_semantics_docs.py`: One-off doc decoupling helper.
- `scripts/python/migrate_tests.py`: One-off test migration helper.
- `scripts/python/sanitize_docs_no_emoji.py`: One-off doc sanitation helper.
- `scripts/python/sanitize_legacy_stack_terms.py`: One-off terminology cleanup helper.
- `scripts/python/sync_acceptance_semantics_methodology.py`: Sibling/template sync helper, not a recurring operator entrypoint.
- `scripts/python/sync_adrs_0028_0030_from_sibling.py`: Sibling/template sync helper, not a recurring operator entrypoint.
- `scripts/python/sync_task_semantics_assets_from_sibling_repo.py`: Sibling/template sync helper, not a recurring operator entrypoint.

## Primary Entrypoints

### Repo bootstrap and recovery

- `scripts/python/dev_cli.py`
- `scripts/python/chapter6_route.py`
- `scripts/python/inspect_run.py`
- `scripts/python/project_health_scan.py`
- `scripts/python/serve_project_health.py`
- `scripts/python/resume_task.py`
- `scripts/python/run_single_task_chapter6_lane.py`

### Repo hard gates

- `scripts/python/run_gate_bundle.py`
- `scripts/python/run_dotnet.py`
- `scripts/python/run_gdunit.py`
- `scripts/python/smoke_headless.py`
- `scripts/python/quality_gates.py`
- `scripts/python/ci_pipeline.py`

### Task loop and TDD

- `scripts/sc/run_review_pipeline.py`
- `scripts/sc/acceptance_check.py`
- `scripts/sc/llm_review.py`
- `scripts/sc/test.py`
- `scripts/sc/build.py`
- `scripts/sc/build/tdd.py`
- `scripts/sc/check_tdd_execution_plan.py`
- `scripts/sc/llm_generate_tests_from_acceptance_refs.py`
- `scripts/python/run_single_task_light_lane_batch.py`
- `scripts/python/run_single_task_light_lane.py`
- `scripts/python/run_single_task_chapter6_lane.py`
- `scripts/python/merge_single_task_light_lane_summaries.py`

### Taskmaster / semantics / overlay

- `scripts/python/task_links_validate.py`
- `scripts/python/check_tasks_all_refs.py`
- `scripts/python/validate_task_master_triplet.py`
- `scripts/python/validate_contracts.py`
- `scripts/python/check_domain_contracts.py`
- `scripts/python/sync_task_overlay_refs.py`
- `scripts/sc/llm_generate_overlays_batch.py`

## Parameter Prerequisite Legend

- `Task triplet required`: any `--task-id` / `--task-file` flow assumes Taskmaster data. Template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
- `Godot runtime required`: any engine-side verification (`--godot-bin`, GdUnit, smoke, acceptance evidence, scene tests) needs a local Godot .NET console binary.
- `Dotnet required`: `.NET 8 SDK` and a valid auto-resolved `.sln` or explicit `.csproj` path must exist.
- `PRD / overlay input required`: PRD source files, overlay roots, and business-local `PRD-ID` values must be real.
- `LLM runtime required`: model-backed generation / review scripts require the repo's configured LLM runtime or CLI unless the script has an explicit deterministic-only mode.
- `Write flow`: commands with `--write` / `--apply` / `--in-place` or migration verbs mutate repo files and should be reviewed like code changes.
- `Local only`: server / browser helpers are for local `127.0.0.1` use, not CI.

## Family Index

### Deterministic audits and hard gates

- `scripts/python/audit_sc_llm_acceptance_assets.py`
- `scripts/python/audit_tests_godot_mirror_git_tracking.py`
- `scripts/python/check_a11y.py`
- `scripts/python/check_acceptance_stability_template.py`
- `scripts/python/check_architecture_boundary.py`
- `scripts/python/check_contract_interface_docs.py`
- `scripts/python/check_csharp_test_conventions.py`
- `scripts/python/check_directory_boundaries.py`
- `scripts/python/check_docs_utf8_integrity.py`
- `scripts/python/check_domain_contracts.py`
- `scripts/python/check_encoding.py`
- `scripts/python/check_gate_bundle_consistency.py`
- `scripts/python/check_no_hardcoded_core_events.py`
- `scripts/python/check_sc_internal_imports.py`
- `scripts/python/check_sentry_secrets.py`
- `scripts/python/check_test_naming.py`
- `scripts/python/check_workflow_gate_enforcement.py`
- `scripts/python/encoding_hard_gate.py`
- `scripts/python/ensure_gdunit_plugin.py`
- `scripts/python/ensure_tests_godot_junction.py`
- `scripts/python/forbid_manual_sc_triplet_examples.py`
- `scripts/python/forbid_mirror_path_refs.py`
- `scripts/python/scan_doc_stack_terms.py`
- `scripts/python/scan_garbled.py`
- `scripts/python/security_hard_audit_gate.py`
- `scripts/python/security_hard_path_gate.py`
- `scripts/python/security_hard_sql_gate.py`
- `scripts/python/security_soft_scan.py`
- `scripts/python/validate_acceptance_anchors.py`
- `scripts/python/validate_acceptance_execution_evidence.py`
- `scripts/python/validate_acceptance_refs.py`
- `scripts/python/validate_contracts.py`
- `scripts/python/validate_docs_utf8_no_bom.py`
- `scripts/python/validate_security_audit_execution_evidence.py`
- `scripts/python/validate_ui_event_json_guards.py`
- `scripts/python/validate_ui_event_source_verification.py`
- `scripts/sc/check_acceptance_garbled.py`

### LLM-assisted semantics and generation

- `scripts/sc/llm_align_acceptance_semantics.py`
- `scripts/sc/llm_check_subtasks_coverage.py`
- `scripts/sc/llm_fill_acceptance_refs.py`
- `scripts/sc/llm_semantic_gate_all.py`

### Obligations freeze and jitter toolkit

- `scripts/python/build_obligations_jitter_summary.py`
- `scripts/python/check_obligations_reuse_regression.py`
- `scripts/python/evaluate_obligations_freeze_whitelist.py`
- `scripts/python/generate_obligations_freeze_whitelist_draft.py`
- `scripts/python/promote_obligations_freeze_baseline.py`
- `scripts/python/refresh_obligations_jitter_summary_with_overrides.py`
- `scripts/python/rerun_obligations_hardgate_round3.py`
- `scripts/python/run_obligations_freeze_pipeline.py`
- `scripts/python/run_obligations_jitter_batch5x3.py`
- `scripts/sc/llm_extract_task_obligations.py`
- `scripts/sc/obligations_baseline_sync.py`

### Overlay, PRD, and authoring flows

- `scripts/python/check_prd_gdd_semantic_consistency.py`
- `scripts/python/generate_contracts_catalog.py`
- `scripts/python/generate_task_contract_test_matrix.py`
- `scripts/python/guard_archived_overlays.py`
- `scripts/python/patch_tasks_back_overlay_refs.py`
- `scripts/python/prd_coverage_report.py`
- `scripts/python/remind_overlay_task_drift.py`
- `scripts/python/sync_task_overlay_refs.py`
- `scripts/python/validate_overlay_execution.py`
- `scripts/python/validate_overlay_test_refs.py`
- `scripts/python/validate_task_overlays.py`
- `scripts/sc/llm_generate_overlays_batch.py`
- `scripts/sc/llm_generate_overlays_from_prd.py`

### Repo orchestration and runtime gates

- `scripts/python/ci_pipeline.py`
- `scripts/python/detect_project_stage.py`
- `scripts/python/dev_cli.py`
- `scripts/python/doctor_project.py`
- `scripts/python/godot_selfcheck.py`
- `scripts/python/inspect_run.py`
- `scripts/python/new_decision_log.py`
- `scripts/python/new_execution_plan.py`
- `scripts/python/preflight.py`
- `scripts/python/prepare_gd_tests.py`
- `scripts/python/project_health_scan.py`
- `scripts/python/quality_gates.py`
- `scripts/python/resume_task.py`
- `scripts/python/run_single_task_chapter6_lane.py`
- `scripts/python/run_dotnet.py`
- `scripts/python/run_gate_bundle.py`
- `scripts/python/run_gdunit.py`
- `scripts/python/serve_project_health.py`
- `scripts/python/smoke_headless.py`
- `scripts/python/validate_recovery_docs.py`

### Task loop, review, and TDD

- `scripts/sc/acceptance_check.py`
- `scripts/sc/agent_to_agent_review.py`
- `scripts/sc/analyze.py`
- `scripts/sc/backfill_task_test_refs.py`
- `scripts/sc/build.py`
- `scripts/sc/build/tdd.py`
- `scripts/sc/check_tdd_execution_plan.py`
- `scripts/sc/git.py`
- `scripts/sc/llm_generate_red_test.py`
- `scripts/sc/llm_generate_tests_from_acceptance_refs.py`
- `scripts/python/run_single_task_light_lane.py`
- `scripts/python/run_single_task_chapter6_lane.py`
- `scripts/sc/llm_review.py`
- `scripts/sc/llm_review_needs_fix_fast.py`
- `scripts/sc/run_review_pipeline.py`
- `scripts/sc/test.py`

### Taskmaster triplet and refs maintenance

- `scripts/python/audit_task_triplet_delivery.py`
- `scripts/python/backfill_semantic_review_tier.py`
- `scripts/python/build_taskmaster_tasks.py`
- `scripts/python/check_task_contract_refs.py`
- `scripts/python/check_tasks_all_refs.py`
- `scripts/python/check_tasks_back_references.py`
- `scripts/python/migrate_task_optional_hints_to_views.py`
- `scripts/python/task_links_validate.py`
- `scripts/python/update_task_test_refs.py`
- `scripts/python/update_task_test_refs_from_acceptance_refs.py`
- `scripts/python/validate_semantic_review_tier.py`
- `scripts/python/validate_task_context_required_fields.py`
- `scripts/python/validate_task_master_triplet.py`
- `scripts/python/validate_task_test_refs.py`
- `scripts/python/verify_task_mapping.py`

### Utilities and maintenance entrypoints

- `scripts/python/backfill_acceptance_anchors_in_tests.py`
- `scripts/python/db_schema_dump.py`
- `scripts/python/update_testing_framework_from_fragments.py`
- `scripts/python/warn_whitelist_expiry.py`

## Full Inventory

### Deterministic audits and hard gates

#### `scripts/python/audit_sc_llm_acceptance_assets.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: None.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/audit_tests_godot_mirror_git_tracking.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--root`, `--mirror-prefix`, `--primary-prefix`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Tests.Godot mirror checks only apply to repos that use the `Tests.Godot` -> `Game.Godot` Junction pattern.

#### `scripts/python/check_a11y.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/check_acceptance_stability_template.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-files`, `--targets-file`, `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/check_architecture_boundary.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/check_contract_interface_docs.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--interfaces-dir`, `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/check_csharp_test_conventions.py`

- Direct local deps: `scripts/python/_csharp_test_conventions.py`
- Transitive local deps: `scripts/python/_csharp_test_conventions.py`
- Subcommands: None.
- Declared args: `--task-id`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/check_directory_boundaries.py`

- Direct local deps: `scripts/python/_project_health_support.py`
- Transitive local deps: `scripts/python/_project_health_checks.py`, `scripts/python/_project_health_common.py`, `scripts/python/_project_health_support.py`
- Subcommands: None.
- Declared args: `--repo-root`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/check_docs_utf8_integrity.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--roots`, `--out`, `--max-print`, `--allow`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/check_domain_contracts.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--contracts-dir`, `--domain-prefix`, `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/check_encoding.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--since-today`, `--since`, `--files`, `--root`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/check_gate_bundle_consistency.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/check_no_hardcoded_core_events.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/check_sc_internal_imports.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/check_sentry_secrets.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: None.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Sentry checks only become meaningful when `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, and `SENTRY_PROJECT` are available.

#### `scripts/python/check_test_naming.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--style`, `--scope`, `--task-id`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/check_workflow_gate_enforcement.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--allowlist`, `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/encoding_hard_gate.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--target`, `--out-dir`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/ensure_gdunit_plugin.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--project`, `--version`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/ensure_tests_godot_junction.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--root`, `--tests-project`, `--link-name`, `--target-rel`, `--create-if-missing`, `--fix-wrong-target`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Tests.Godot mirror checks only apply to repos that use the `Tests.Godot` -> `Game.Godot` Junction pattern.

#### `scripts/python/forbid_manual_sc_triplet_examples.py`

- Direct local deps: `scripts/python/_whitelist_metadata.py`
- Transitive local deps: `scripts/python/_whitelist_metadata.py`
- Subcommands: None.
- Declared args: `--root`, `--mode`, `--whitelist`, `--whitelist-metadata`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/forbid_mirror_path_refs.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--root`, `--roots`, `--exts`, `--max-hits`, `--max-hits-per-file`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Tests.Godot mirror checks only apply to repos that use the `Tests.Godot` -> `Game.Godot` Junction pattern.

#### `scripts/python/scan_doc_stack_terms.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--root`, `--out-dir`, `--fail-on-hits`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/scan_garbled.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--root`, `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/security_hard_audit_gate.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/security_hard_path_gate.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/security_hard_sql_gate.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/security_soft_scan.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/validate_acceptance_anchors.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-id`, `--stage`, `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/validate_acceptance_execution_evidence.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-id`, `--run-id`, `--out`, `--date`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/validate_acceptance_refs.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-id`, `--stage`, `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/validate_contracts.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--root`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/validate_docs_utf8_no_bom.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--roots`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/validate_security_audit_execution_evidence.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--run-id`, `--out`, `--date`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/validate_ui_event_json_guards.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/validate_ui_event_source_verification.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/sc/check_acceptance_garbled.py`

- Direct local deps: `scripts/sc/_garbled_gate.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_garbled_gate.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--task-ids`, `--max-sample-chars`, `--max-print-hits`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

### LLM-assisted semantics and generation

#### `scripts/sc/llm_align_acceptance_semantics.py`

- Direct local deps: `scripts/sc/_acceptance_semantics_align.py`, `scripts/sc/_acceptance_semantics_runtime.py`, `scripts/sc/_delivery_profile.py`, `scripts/sc/_garbled_gate.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_acceptance_semantics_align.py`, `scripts/sc/_acceptance_semantics_runtime.py`, `scripts/sc/_delivery_profile.py`, `scripts/sc/_garbled_gate.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--delivery-profile`, `--llm-backend`, `--scope`, `--task-ids`, `--fail-on-missing-task-ids`, `--fail-on-missing-views`, `--strict-task-selection`, `--apply`, `--preflight-migrate-optional-hints`, `--skip-preflight-migrate-optional-hints`, `--structural-for-not-done`, `--append-only-for-done`, `--align-view-descriptions-to-master`, `--semantic-findings-json`, `--timeout-sec`, `--max-failures`, `--garbled-gate`, `--self-check`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI or an API backend; `--llm-backend openai-api` now uses the shared backend seam, while `--self-check` remains deterministic.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/sc/llm_check_subtasks_coverage.py`

- Direct local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_llm_backend.py`, `scripts/sc/_obligations_extract_helpers.py`, `scripts/sc/_subtasks_coverage_garbled.py`, `scripts/sc/_subtasks_coverage_llm.py`, `scripts/sc/_subtasks_coverage_schema.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_garbled_gate.py`, `scripts/sc/_llm_backend.py`, `scripts/sc/_obligations_extract_helpers.py`, `scripts/sc/_subtasks_coverage_garbled.py`, `scripts/sc/_subtasks_coverage_llm.py`, `scripts/sc/_subtasks_coverage_schema.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--task-id`, `--delivery-profile`, `--llm-backend`, `--timeout-sec`, `--max-prompt-chars`, `--consensus-runs`, `--strict-view-selection`, `--garbled-gate`, `--max-schema-errors`, `--round-id`, `--self-check`
- Behavior notes: `--llm-backend codex-cli|openai-api` now routes semantic coverage rounds through the shared backend seam; `--self-check` stays deterministic.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI or an API backend; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

#### `scripts/sc/llm_fill_acceptance_refs.py`

- Direct local deps: `scripts/sc/_acceptance_refs_contract.py`, `scripts/sc/_acceptance_refs_helpers.py`, `scripts/sc/_acceptance_refs_prompt.py`, `scripts/sc/_llm_backend.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_acceptance_refs_contract.py`, `scripts/sc/_acceptance_refs_helpers.py`, `scripts/sc/_acceptance_refs_prompt.py`, `scripts/sc/_llm_backend.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--all`, `--task-id`, `--llm-backend`, `--write`, `--overwrite-existing`, `--rewrite-placeholders`, `--timeout-sec`, `--max-refs-per-item`, `--candidate-limit`, `--max-tasks`, `--consensus-runs`, `--self-check`
- Behavior notes: `--llm-backend codex-cli|openai-api` now routes the per-task consensus mapping call through the shared backend seam; `--self-check` stays deterministic.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI or an API backend; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/sc/llm_semantic_gate_all.py`

- Direct local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_garbled_gate.py`, `scripts/sc/_llm_backend.py`, `scripts/sc/_semantic_gate_all_contract.py`, `scripts/sc/_semantic_gate_all_runtime.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_garbled_gate.py`, `scripts/sc/_llm_backend.py`, `scripts/sc/_semantic_gate_all_contract.py`, `scripts/sc/_semantic_gate_all_runtime.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--delivery-profile`, `--llm-backend`, `--task-ids`, `--batch-size`, `--timeout-sec`, `--consensus-runs`, `--model-reasoning-effort`, `--max-acceptance-items`, `--max-prompt-chars`, `--max-tasks`, `--max-needs-fix`, `--max-unknown`, `--garbled-gate`, `--self-check`
- Behavior notes: `--llm-backend codex-cli|openai-api` now routes batch semantic gate calls through the shared backend seam; `--model-reasoning-effort` is still preserved through that transport layer.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI or an API backend; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

### Obligations freeze and jitter toolkit

#### `scripts/python/build_obligations_jitter_summary.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--raw`, `--out-summary`, `--out-report`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/check_obligations_reuse_regression.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-id`, `--task-files`, `--round-prefix`, `--timeout-sec`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/evaluate_obligations_freeze_whitelist.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--whitelist`, `--summary`, `--out-dir`, `--allow-draft`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/generate_obligations_freeze_whitelist_draft.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--summary`, `--out-json`, `--out-md`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/promote_obligations_freeze_baseline.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--draft`, `--baseline-dir`, `--baseline-date`, `--baseline-tag`, `--current`, `--report`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/refresh_obligations_jitter_summary_with_overrides.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--base-summary`, `--override-rerun`, `--out-summary`, `--out-report`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/rerun_obligations_hardgate_round3.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-ids`, `--tasks-file`, `--max-tasks`, `--rounds`, `--timeout-sec`, `--delivery-profile`, `--security-profile`, `--out-dir`, `--out-json`, `--out-md`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/run_obligations_freeze_pipeline.py`

- Direct local deps: `scripts/python/_obligations_freeze_pipeline_steps.py`, `scripts/python/_obligations_freeze_runtime.py`
- Transitive local deps: `scripts/python/_obligations_freeze_pipeline_steps.py`, `scripts/python/_obligations_freeze_runtime.py`
- Subcommands: None.
- Declared args: `--out-dir`, `--skip-jitter`, `--raw`, `--task-ids`, `--tasks-file`, `--batch-size`, `--rounds`, `--start-group`, `--end-group`, `--timeout-sec`, `--round-id-prefix`, `--delivery-profile`, `--security-profile`, `--consensus-runs`, `--min-obligations`, `--garbled-gate`, `--auto-escalate`, `--escalate-max-runs`, `--max-schema-errors`, `--reuse-last-ok`, `--explain-reuse-miss`, `--override-rerun`, `--draft-json`, `--draft-md`, `--eval-dir`, `--allow-draft-eval`, `--no-allow-draft-eval`, `--require-judgable`, `--require-freeze-pass`, `--approve-promote`, `--baseline-dir`, `--baseline-date`, `--baseline-tag`, `--current-baseline`, `--promote-report`, `--jitter-timeout-sec`, `--step-timeout-sec`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/run_obligations_jitter_batch5x3.py`

- Direct local deps: `scripts/python/_obligations_freeze_runtime.py`
- Transitive local deps: `scripts/python/_obligations_freeze_runtime.py`
- Subcommands: None.
- Declared args: `--task-ids`, `--tasks-file`, `--batch-size`, `--rounds`, `--start-group`, `--end-group`, `--timeout-sec`, `--round-id-prefix`, `--out-raw`, `--delivery-profile`, `--security-profile`, `--consensus-runs`, `--min-obligations`, `--garbled-gate`, `--auto-escalate`, `--escalate-max-runs`, `--max-schema-errors`, `--reuse-last-ok`, `--explain-reuse-miss`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/sc/llm_extract_task_obligations.py`

- Direct local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_garbled_gate.py`, `scripts/sc/_obligations_artifacts.py`, `scripts/sc/_obligations_code_fingerprint.py`, `scripts/sc/_obligations_extract_helpers.py`, `scripts/sc/_obligations_guard.py`, `scripts/sc/_obligations_input_fingerprint.py`, `scripts/sc/_obligations_main_flow.py`, `scripts/sc/_obligations_prompt_acceptance.py`, `scripts/sc/_obligations_reuse_explain.py`, `scripts/sc/_obligations_reuse_index.py`, `scripts/sc/_obligations_runtime_helpers.py`, `scripts/sc/_obligations_self_check.py`, `scripts/sc/_security_profile.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_garbled_gate.py`, `scripts/sc/_obligations_artifacts.py`, `scripts/sc/_obligations_code_fingerprint.py`, `scripts/sc/_obligations_extract_helpers.py`, `scripts/sc/_obligations_guard.py`, `scripts/sc/_obligations_input_fingerprint.py`, `scripts/sc/_obligations_main_flow.py`, `scripts/sc/_obligations_output_contract.py`, `scripts/sc/_obligations_prompt_acceptance.py`, `scripts/sc/_obligations_reuse_explain.py`, `scripts/sc/_obligations_reuse_index.py`, `scripts/sc/_obligations_runtime_helpers.py`, `scripts/sc/_obligations_self_check.py`, `scripts/sc/_obligations_text_rules.py`, `scripts/sc/_security_profile.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--task-id`, `--delivery-profile`, `--llm-backend`, `--timeout-sec`, `--max-prompt-chars`, `--consensus-runs`, `--min-obligations`, `--round-id`, `--security-profile`, `--garbled-gate`, `--auto-escalate`, `--escalate-max-runs`, `--escalate-task-ids`, `--max-schema-errors`, `--reuse-last-ok`, `--explain-reuse-miss`, `--dry-run-fingerprint`, `--self-check`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

#### `scripts/sc/obligations_baseline_sync.py`

- Direct local deps: `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--task-ids`, `--baseline-file`, `--refresh-baseline`, `--apply`, `--verify`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.
  - Write/apply flows mutate repository files; review diffs before and after execution.

### Overlay, PRD, and authoring flows

#### `scripts/python/check_prd_gdd_semantic_consistency.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--config`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/generate_contracts_catalog.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--prd-id`, `--domain-prefix`, `--contracts-dir`, `--tasks-back`, `--tasks-gameplay`, `--out-md`, `--out-json`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - PRD/overlay parameters require real PRD sources, overlay roots, and business-local `PRD-ID` values.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/generate_task_contract_test_matrix.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-views`, `--contracts-root`, `--tests-root`, `--out-json`, `--out-md`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - PRD/overlay parameters require real PRD sources, overlay roots, and business-local `PRD-ID` values.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/guard_archived_overlays.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--strict-git`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - PRD/overlay parameters require real PRD sources, overlay roots, and business-local `PRD-ID` values.

#### `scripts/python/patch_tasks_back_overlay_refs.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-file`, `--dry-run`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - PRD/overlay parameters require real PRD sources, overlay roots, and business-local `PRD-ID` values.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/prd_coverage_report.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: None.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - PRD/overlay parameters require real PRD sources, overlay roots, and business-local `PRD-ID` values.

#### `scripts/python/remind_overlay_task_drift.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--write`, `--overlay-index`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - PRD/overlay parameters require real PRD sources, overlay roots, and business-local `PRD-ID` values.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/sync_task_overlay_refs.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--write`, `--dry-run`, `--prd-id`, `--tasks-dir`, `--skip-done`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - PRD/overlay parameters require real PRD sources, overlay roots, and business-local `PRD-ID` values.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/validate_overlay_execution.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--prd-id`, `--overlay-dir`, `--require-heading`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - PRD/overlay parameters require real PRD sources, overlay roots, and business-local `PRD-ID` values.

#### `scripts/python/validate_overlay_test_refs.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--overlay`, `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - PRD/overlay parameters require real PRD sources, overlay roots, and business-local `PRD-ID` values.

#### `scripts/python/validate_task_overlays.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-file`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - PRD/overlay parameters require real PRD sources, overlay roots, and business-local `PRD-ID` values.

#### `scripts/sc/llm_generate_overlays_batch.py`

- Direct local deps: `scripts/sc/_overlay_generator_batch.py`, `scripts/sc/_overlay_generator_support.py`, `scripts/sc/_util.py`, `scripts/sc/llm_generate_overlays_from_prd.py`
- Transitive local deps: `scripts/sc/_overlay_generator_batch.py`, `scripts/sc/_overlay_generator_contract.py`, `scripts/sc/_overlay_generator_diff.py`, `scripts/sc/_overlay_generator_markdown_patch.py`, `scripts/sc/_overlay_generator_model.py`, `scripts/sc/_overlay_generator_patch.py`, `scripts/sc/_overlay_generator_prompting.py`, `scripts/sc/_overlay_generator_runtime.py`, `scripts/sc/_overlay_generator_scaffold.py`, `scripts/sc/_overlay_generator_scaffold_prompting.py`, `scripts/sc/_overlay_generator_support.py`, `scripts/sc/_util.py`, `scripts/sc/llm_generate_overlays_from_prd.py`
- Subcommands: None.
- Declared args: `--prd`, `--prd-id`, `--prd-docs`, `--pages`, `--page-family`, `--page-mode`, `--timeout-sec`, `--dry-run`, `--apply`, `--batch-suffix`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - PRD/overlay parameters require real PRD sources, overlay roots, and business-local `PRD-ID` values.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/sc/llm_generate_overlays_from_prd.py`

- Direct local deps: `scripts/sc/_overlay_generator_diff.py`, `scripts/sc/_overlay_generator_markdown_patch.py`, `scripts/sc/_overlay_generator_patch.py`, `scripts/sc/_overlay_generator_prompting.py`, `scripts/sc/_overlay_generator_runtime.py`, `scripts/sc/_overlay_generator_scaffold.py`, `scripts/sc/_overlay_generator_scaffold_prompting.py`, `scripts/sc/_overlay_generator_support.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_overlay_generator_contract.py`, `scripts/sc/_overlay_generator_diff.py`, `scripts/sc/_overlay_generator_markdown_patch.py`, `scripts/sc/_overlay_generator_model.py`, `scripts/sc/_overlay_generator_patch.py`, `scripts/sc/_overlay_generator_prompting.py`, `scripts/sc/_overlay_generator_runtime.py`, `scripts/sc/_overlay_generator_scaffold.py`, `scripts/sc/_overlay_generator_scaffold_prompting.py`, `scripts/sc/_overlay_generator_support.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--prd`, `--prd-id`, `--prd-docs`, `--timeout-sec`, `--dry-run`, `--apply`, `--page-filter`, `--page-family`, `--page-mode`, `--run-suffix`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - PRD/overlay parameters require real PRD sources, overlay roots, and business-local `PRD-ID` values.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.
  - Write/apply flows mutate repository files; review diffs before and after execution.

### Repo orchestration and runtime gates

#### `scripts/python/ci_pipeline.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: `all`
- Declared args: `--solution`, `--configuration`, `--godot-bin`, `--project`, `--build-solutions`, `--dotnet-stage-timeout-ms`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.
  - Dotnet-related options require `.NET 8 SDK` and valid solution/project paths (default usually `auto`, which resolves to the project-preferred `.sln`).

#### `scripts/python/detect_project_stage.py`

- Direct local deps: `scripts/python/_project_health_support.py`
- Transitive local deps: `scripts/python/_project_health_checks.py`, `scripts/python/_project_health_common.py`, `scripts/python/_project_health_support.py`
- Subcommands: None.
- Declared args: `--repo-root`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/dev_cli.py`

- Direct local deps: `scripts/python/dev_cli_builders.py`, `scripts/python/local_hard_checks_harness.py`
- Transitive local deps: `scripts/python/dev_cli_builders.py`, `scripts/python/local_hard_checks_harness.py`, `scripts/python/local_hard_checks_support.py`
- Subcommands: `run-ci-basic`, `run-quality-gates`, `run-local-hard-checks`, `run-local-hard-checks-preflight`, `run-gdunit-hard`, `run-gdunit-full`, `run-preflight`, `run-acceptance-preflight`, `run-smoke-strict`, `run-prototype-tdd`, `new-execution-plan`, `new-decision-log`, `resume-task`, `inspect-run`, `chapter6-route`, `run-single-task-chapter6`, `detect-project-stage`, `doctor-project`, `check-directory-boundaries`, `project-health-scan`, `serve-project-health`
- Declared args: `--solution`, `--configuration`, `--godot-bin`, `--delivery-profile`, `--security-profile`, `--fix-through`, `--task-file`, `--out-dir`, `--run-id`, `--legacy-preflight`, `--build-solutions`, `--gdunit-hard`, `--smoke`, `--timeout-sec`, `--test-project`, `--slug`, `--expect`, `--prototype-dir`, `--record-path`, `--skip-record`, `--owner`, `--related-task-id`, `--hypothesis`, `--scope-in`, `--scope-out`, `--success-criteria`, `--evidence`, `--next-step`, `--create-record-only`, `--dotnet-target`, `--filter`, `--gdunit-path`, `--title`, `--status`, `--goal`, `--scope`, `--current-step`, `--stop-loss`, `--next-action`, `--exit-criteria`, `--adr`, `--decision-log`, `--task-id`, `--stage`, `--latest-json`, `--output`, `--why-now`, `--context`, `--decision`, `--consequences`, `--recovery-impact`, `--validation`, `--supersedes`, `--superseded-by`, `--execution-plan`, `--repo-root`, `--latest`, `--kind`, `--record-residual`, `--out-json`, `--out-md`, `--recommendation-only`, `--recommendation-format`, `--serve`, `--port`, `--self-check`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Dotnet-related options require `.NET 8 SDK` and valid solution/project paths (default usually `auto`, which resolves to the project-preferred `.sln`).
  - Serving parameters are local-only: use on `127.0.0.1`, not in CI.
  - `run-acceptance-preflight` is the stable lightweight wrapper for `validate_acceptance_refs.py + validate_acceptance_anchors.py`; default stage is `refactor`.

#### `scripts/python/doctor_project.py`

- Direct local deps: `scripts/python/_project_health_support.py`
- Transitive local deps: `scripts/python/_project_health_checks.py`, `scripts/python/_project_health_common.py`, `scripts/python/_project_health_support.py`
- Subcommands: None.
- Declared args: `--repo-root`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/godot_selfcheck.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: `fix-autoload`, `run`
- Declared args: `--project`, `--godot-bin`, `--build-solutions`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.

#### `scripts/python/inspect_run.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--repo-root`, `--latest`, `--kind`, `--task-id`, `--run-id`, `--out-json`, `--recommendation-only`
- Behavior notes: pipeline inspection now extracts `latest_summary_signals` (`reason`, `run_type`, `reuse_mode`, `artifact_integrity`, `diagnostics_keys`) and derived `chapter6_hints` (`next_action`, `can_skip_6_7`, `can_go_to_6_8`, `blocked_by`).
- Behavior notes: `--recommendation-only` prints the compact recovery block instead of the full JSON payload, which is useful when only the next stop-loss / rerun decision is needed.
- Behavior notes: `chapter6_hints.blocked_by` now also covers `llm_retry_stop_loss`, `sc_test_retry_stop_loss`, and `waste_signals`, not only generic rerun guard states.
- Behavior notes: if inspection resolves `run_type = planned-only`, `reason = planned_only_incomplete`, or `blocked_by = artifact_integrity`, the bundle must be treated as evidence-only rather than a resumable producer run.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/chapter6_route.py`

- Direct local deps: `scripts/python/resume_task.py`, `scripts/python/_recovery_doc_scaffold.py`
- Transitive local deps: `scripts/python/inspect_run.py`, `scripts/python/resume_task.py`, `scripts/python/_recovery_doc_scaffold.py`, `scripts/sc/llm_review_needs_fix_fast.py`
- Subcommands: None.
- Declared args: `--repo-root`, `--task-id`, `--run-id`, `--latest`, `--record-residual`, `--out-json`, `--out-md`, `--recommendation-only`, `--recommendation-format`
- Behavior notes: reads recovery artifacts first, then routes Chapter 6 to `run-6.7`, `run-6.8`, `fix-deterministic`, `repo-noise-stop`, `record-residual`, or `inspect-first`.
- Behavior notes: `6.8` is only recommended when current edits hit the previous reviewer anchors.
- Behavior notes: `--record-residual` writes `decision-logs/**` and `execution-plans/**` when only low-priority findings remain.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require real recovery artifacts under `logs/ci/**`.

#### `scripts/python/run_single_task_chapter6_lane.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-id`, `--godot-bin`, `--delivery-profile`, `--security-profile`, `--fix-through`, `--out-dir`, `--self-check`
- Behavior notes: starts from `resume-task` and `chapter6-route`, then routes to either the full `6.3 -> 6.9` path or the narrower `6.8` closure path based on recovery artifacts.
- Behavior notes: default policy is `playable-ea -> fix-through P0`, `fast-ship -> fix-through P1`, `standard -> fix-through P1`; residual `P2/P3` findings are recorded by default instead of being auto-reopened.
- Behavior notes: `--self-check` writes the resolved command plan without executing the Chapter 6 tools.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet and normal Chapter 6 entrypoint availability.
  - `--godot-bin` is strongly recommended because the lane includes repo-level hard checks and may need engine-side verification.

#### `scripts/python/run_prototype_tdd.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--slug`, `--stage`, `--expect`, `--prototype-dir`, `--record-path`, `--skip-record`, `--owner`, `--related-task-id`, `--hypothesis`, `--scope-in`, `--scope-out`, `--success-criteria`, `--evidence`, `--next-step`, `--create-record-only`, `--dotnet-target`, `--filter`, `--configuration`, `--godot-bin`, `--gdunit-path`, `--timeout-sec`, `--out-dir`
- Behavior notes: lightweight prototype-lane TDD entry; writes notes under `docs/prototypes/**` and evidence under `logs/ci/**` without publishing formal task recovery pointers.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - `--godot-bin` is required when `--gdunit-path` is used.
  - `--create-record-only` is valid when you only want the prototype note scaffold without executing verification.

#### `scripts/python/new_decision_log.py`

- Direct local deps: `scripts/python/_recovery_doc_scaffold.py`
- Transitive local deps: `scripts/python/_recovery_doc_scaffold.py`
- Subcommands: None.
- Declared args: `--title`, `--status`, `--why-now`, `--context`, `--decision`, `--consequences`, `--recovery-impact`, `--validation`, `--supersedes`, `--superseded-by`, `--adr`, `--execution-plan`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/new_execution_plan.py`

- Direct local deps: `scripts/python/_recovery_doc_scaffold.py`
- Transitive local deps: `scripts/python/_recovery_doc_scaffold.py`
- Subcommands: None.
- Declared args: `--title`, `--status`, `--goal`, `--scope`, `--current-step`, `--stop-loss`, `--next-action`, `--exit-criteria`, `--adr`, `--decision-log`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/preflight.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--test-project`, `--configuration`, `--out-dir`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Dotnet-related options require `.NET 8 SDK` and valid solution/project paths (default usually `auto`, which resolves to the project-preferred `.sln`).

#### `scripts/python/prepare_gd_tests.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--project`, `--runtime`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Tests.Godot mirror checks only apply to repos that use the `Tests.Godot` -> `Game.Godot` Junction pattern.

#### `scripts/python/project_health_scan.py`

- Direct local deps: `scripts/python/_project_health_server.py`, `scripts/python/_project_health_support.py`
- Transitive local deps: `scripts/python/_project_health_checks.py`, `scripts/python/_project_health_common.py`, `scripts/python/_project_health_server.py`, `scripts/python/_project_health_support.py`
- Subcommands: None.
- Declared args: `--repo-root`, `--serve`, `--port`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Serving parameters are local-only: use on `127.0.0.1`, not in CI.

#### `scripts/python/quality_gates.py`

- Direct local deps: `scripts/python/quality_gates_builders.py`
- Transitive local deps: `scripts/python/quality_gates_builders.py`
- Subcommands: `all`
- Declared args: `--solution`, `--configuration`, `--build-solutions`, `--godot-bin`, `--delivery-profile`, `--task-file`, `--out-dir`, `--run-id`, `--gdunit-hard`, `--smoke`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Dotnet-related options require `.NET 8 SDK` and valid solution/project paths (default usually `auto`, which resolves to the project-preferred `.sln`).

#### `scripts/python/resume_task.py`

- Direct local deps: `scripts/python/inspect_run.py`, `scripts/python/validate_recovery_docs.py`
- Transitive local deps: `scripts/python/inspect_run.py`, `scripts/python/validate_recovery_docs.py`
- Subcommands: None.
- Declared args: `--repo-root`, `--task-id`, `--run-id`, `--latest`, `--out-json`, `--out-md`, `--recommendation-only`
- Behavior notes: recovery summaries now surface `latest_summary_signals`, `chapter6_hints`, and a derived `Chapter6 stop-loss note` so operators can see why another full `6.7` would be wasteful; this includes `run_type`, `artifact_integrity`, and planned-only terminal bundle handling.
- Behavior notes: `--recommendation-only` prints the compact recovery recommendation and skips the default JSON/Markdown writes unless explicit output paths are requested.
- Behavior notes: recovery outputs also surface `recommended_action_why`; when the resolved action is `needs-fix-fast`, operators should prefer targeted closure instead of another full rerun.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/run_dotnet.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--solution`, `--configuration`, `--filter`, `--out-dir`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Dotnet-related options require `.NET 8 SDK` and valid solution/project paths (default usually `auto`, which resolves to the project-preferred `.sln`).

#### `scripts/python/run_gate_bundle.py`

- Direct local deps: `scripts/python/gate_bundle_retention.py`
- Transitive local deps: `scripts/python/gate_bundle_retention.py`
- Subcommands: None.
- Declared args: `--mode`, `--strict-soft`, `--delivery-profile`, `--task-links-max-warnings`, `--stability-template-hard`, `--task-files`, `--out-dir`, `--run-id`, `--retention-days`, `--max-runs-per-day`, `--skip-prune-runs`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/run_gdunit.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--godot-bin`, `--project`, `--add`, `--timeout-sec`, `--prewarm`, `--rd`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.

#### `scripts/python/serve_project_health.py`

- Direct local deps: `scripts/python/_project_health_server.py`
- Transitive local deps: `scripts/python/_project_health_common.py`, `scripts/python/_project_health_server.py`
- Subcommands: None.
- Declared args: `--repo-root`, `--port`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Serving parameters are local-only: use on `127.0.0.1`, not in CI.

#### `scripts/python/smoke_headless.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--godot-bin`, `--project-path`, `--scene`, `--timeout-sec`, `--strict`, `--task-id`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/validate_recovery_docs.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--dir`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

### Task loop, review, and TDD

#### `scripts/sc/acceptance_check.py`

- Direct local deps: `scripts/sc/_acceptance_orchestration.py`, `scripts/sc/_acceptance_report.py`, `scripts/sc/_acceptance_runtime.py`, `scripts/sc/_acceptance_steps.py`, `scripts/sc/_acceptance_task_requirements.py`, `scripts/sc/_risk_summary.py`, `scripts/sc/_security_profile.py`, `scripts/sc/_summary_schema.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_unit_metrics.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_acceptance_evidence_steps.py`, `scripts/sc/_acceptance_orchestration.py`, `scripts/sc/_acceptance_report.py`, `scripts/sc/_acceptance_runtime.py`, `scripts/sc/_acceptance_steps.py`, `scripts/sc/_acceptance_steps_quality.py`, `scripts/sc/_acceptance_steps_runner.py`, `scripts/sc/_acceptance_steps_security.py`, `scripts/sc/_acceptance_task_requirements.py`, `scripts/sc/_delivery_profile.py`, `scripts/sc/_env_evidence_helpers.py`, `scripts/sc/_env_evidence_preflight.py`, `scripts/sc/_post_evidence_config.py`, `scripts/sc/_quality_rules.py`, `scripts/sc/_repo_targets.py`, `scripts/sc/_risk_summary.py`, `scripts/sc/_security_profile.py`, `scripts/sc/_step_result.py`, `scripts/sc/_subtasks_coverage_step.py`, `scripts/sc/_summary_schema.py`, `scripts/sc/_summary_schema_fallback.py`, `scripts/sc/_summary_schema_local_hard_checks.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_test_quality.py`, `scripts/sc/_unit_metrics.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: None.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

#### `scripts/sc/agent_to_agent_review.py`

- Direct local deps: `scripts/sc/_agent_review_contract.py`, `scripts/sc/_agent_review_policy.py`, `scripts/sc/_artifact_schema.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_agent_review_contract.py`, `scripts/sc/_agent_review_policy.py`, `scripts/sc/_artifact_schema.py`, `scripts/sc/_artifact_schema_fallback.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--pipeline-out-dir`, `--task-id`, `--run-id`, `--reviewer`, `--strict`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

#### `scripts/sc/analyze.py`

- Direct local deps: `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `target`, `--task-id`, `--tasks-json-path`, `--tasks-back-path`, `--tasks-gameplay-path`, `--taskdoc-dir`, `--focus`, `--depth`, `--format`, `--max-pattern-hits`, `--strict`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/sc/backfill_task_test_refs.py`

- Direct local deps: `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--statuses`, `--all-tasks`, `--task-id`, `--write`, `--timeout-sec`, `--verify`, `--godot-bin`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/sc/build.py`

- Direct local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_repo_targets.py`, `scripts/sc/_security_profile.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_repo_targets.py`, `scripts/sc/_security_profile.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `target`, `--type`, `--clean`, `--optimize`, `--verbose`, `--delivery-profile`, `--security-profile`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/sc/build/tdd.py`

- Direct local deps: `scripts/sc/build.py`, `scripts/sc/build/_tdd_shared.py`, `scripts/sc/build/_tdd_steps.py`
- Transitive local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_repo_targets.py`, `scripts/sc/_security_profile.py`, `scripts/sc/_util.py`, `scripts/sc/build.py`, `scripts/sc/build/_tdd_shared.py`, `scripts/sc/build/_tdd_steps.py`
- Subcommands: None.
- Declared args: `--stage`, `--task-id`, `--solution`, `--configuration`, `--delivery-profile`, `--security-profile`, `--generate-red-test`, `--no-coverage-gate`, `--allow-contract-changes`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Dotnet-related options require `.NET 8 SDK` and valid solution/project paths (default usually `auto`, which resolves to the project-preferred `.sln`).

#### `scripts/sc/check_tdd_execution_plan.py`

- Direct local deps: `scripts/sc/_execution_plan_policy.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_acceptance_testgen_refs.py`, `scripts/sc/_execution_plan_policy.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--task-id`, `--tdd-stage`, `--verify`, `--execution-plan-policy`, `--latest-json`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/sc/git.py`

- Direct local deps: `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `operation`, `args`, `--smart-commit`, `--interactive`, `--yes`, `--task-id`, `--task-ref`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/sc/llm_generate_red_test.py`

- Direct local deps: `scripts/sc/_llm_backend.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_llm_backend.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--task-id`, `--llm-backend`, `--timeout-sec`, `--verify-red`
- Behavior notes: `--llm-backend codex-cli|openai-api` now routes red-test drafting through the shared backend seam; `--verify-red` remains the deterministic follow-up after file write.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI or an API backend; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

#### `scripts/sc/llm_generate_tests_from_acceptance_refs.py`

- Direct local deps: `scripts/sc/_acceptance_testgen_flow.py`, `scripts/sc/_acceptance_testgen_llm.py`, `scripts/sc/_acceptance_testgen_quality.py`, `scripts/sc/_acceptance_testgen_red.py`, `scripts/sc/_acceptance_testgen_refs.py`, `scripts/sc/_llm_backend.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_acceptance_testgen_flow.py`, `scripts/sc/_acceptance_testgen_llm.py`, `scripts/sc/_acceptance_testgen_quality.py`, `scripts/sc/_acceptance_testgen_red.py`, `scripts/sc/_acceptance_testgen_refs.py`, `scripts/sc/_llm_backend.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--task-id`, `--llm-backend`, `--timeout-sec`, `--select-timeout-sec`, `--tdd-stage`, `--verify`, `--godot-bin`, `--include-prd-context`, `--prd-context-path`
- Behavior notes: `--llm-backend codex-cli|openai-api` now routes both primary-ref selection and per-file acceptance-test generation calls through the shared backend seam.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI or an API backend; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

#### `scripts/python/merge_single_task_light_lane_summaries.py`

Purpose:
- merge split workflow 5.1 summaries into one transparent merged summary
- preserve per-task winning source, candidate source list, and overridden task ids

Important parameters:
- `--date`: logs date folder under `logs/ci/YYYY-MM-DD`
- `--logs-root`: override logs root if you are merging from a custom folder
- `--input`: explicit summary paths, repeatable
- `--out-dir`: merged output directory

Prerequisites:
- one or more `single-task-light-lane-v2*/summary.json` files already exist
- source summaries should be from the same repo and same logical batch family

Notes:
- default discovery ignores `*-merged` outputs
- later/newer source summaries win for overlapping `task_id`
- output adds `task_source_map`, `task_source_candidates`, and `overridden_task_ids`
- output also adds `validation`; hard issues make the command fail, warnings keep merge success but flag partial/overlapping inputs

#### `scripts/python/run_single_task_light_lane_batch.py`

Purpose:
- coordinate workflow 5.1 across isolated shards instead of reusing one batch `out-dir`
- run the existing light-lane wrapper once per shard, then auto-merge shard summaries
- keep one top-level `summary.json` for batch monitoring and one `merged/summary.json` for merged task results

Important parameters:
- `--batch-preset`: recommended bundle such as `stable-batch` or `long-batch`; explicit flags still win
- `--task-ids` / `--task-id-start` / `--task-id-end` / `--max-tasks`: select the task range using the same selection semantics as the direct light-lane wrapper
- `--max-tasks-per-shard`: shard size for one batch coordinator run
- `--out-dir`: coordinator output root; shard summaries go under `shards/`, merged report goes under `merged/`
- `--batch-lane`, `--fill-refs-mode`, `--downstream-on-extract-fail`, `--resume-failed-task-from`: pass-through shard behavior
- `--rolling-extract-policy`, `--rolling-extract-rate-threshold`, `--rolling-extract-min-observed-tasks`: rolling early-stop / degrade guard for long ranges
- `--rolling-family-policy`, `--rolling-family-streak-threshold`: repeated extract failure family stop-loss and quarantine-range generation
- `--rolling-timeout-backoff-threshold`, `--rolling-timeout-backoff-min-observed-tasks`, `--rolling-timeout-backoff-sec`, `--rolling-timeout-backoff-max-llm-timeout-sec`, `--rolling-shard-reduction-factor`: shard-local timeout backoff for the next shard
- `--self-check`: write the resolved shard plan without executing shards

Prerequisites:
- task triplet available; template fallback can read `examples/taskmaster/tasks.json` when real `.taskmaster/tasks/tasks.json` is absent
- model-backed semantics steps require the repo's LLM runtime/CLI
- use this entrypoint for long ranges; keep the direct wrapper for one task or a small ad-hoc batch

Notes:
- shard runs use isolated subdirectories, so overlapping reruns do not mutate another shard's `last_task_id`
- coordinator `summary.json` tracks shard-level status while `merged/summary.json` tracks task-level merged results
- coordinator `summary.json` now also emits `preferred_lane`, `recommended_action`, `recommended_command`, `forbidden_commands`, `latest_reason`, and `recommended_action_why`
- timeout/model/soft-step reruns now recommend batch-aware commands over failed task ids, instead of pointing operators back to the single-task wrapper
- merge-validation failures and rolling stop-loss cutovers route to `inspect-first` or `split-batch` for safer recovery
- merged output reuses the transparent source mapping from `merge_single_task_light_lane_summaries.py`
- top-level and merged summaries surface both `extract_fail_signature_*` and `extract_fail_family_*`; prefer families for grouped extract triage and signatures for exact evidence

#### `scripts/python/run_single_task_light_lane.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-ids`, `--task-id-start`, `--task-id-end`, `--max-tasks`, `--timeout-sec`, `--llm-timeout-sec`, `--out-dir`, `--no-resume`, `--fill-refs-after-extract-fail`, `--fill-refs-mode`, `--downstream-on-extract-fail`, `--batch-lane`, `--resume-failed-task-from`, `--stop-on-step-failure`, `--no-align-apply`, `--delivery-profile`, `--self-check`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/tasks.json` when real `.taskmaster/tasks/tasks.json` is absent.
  - Model-backed steps require the repo's LLM runtime/CLI for semantics-related stages.
  - Write/apply flow is controlled by `--no-align-apply`; default behavior includes `align --apply`.
  - Multi-task runs can resolve `--batch-lane auto` to `extract-first` and `--fill-refs-mode auto` to `none`.
- Summary outputs now also expose `preferred_lane`, `recommended_action`, `recommended_command`, `forbidden_commands`, `latest_reason`, and `recommended_action_why` so recovery tooling can consume one stable route contract.

#### `scripts/sc/llm_review.py`

- Direct local deps: `scripts/sc/_llm_review_engine.py`
- Transitive local deps: `scripts/sc/_acceptance_artifacts.py`, `scripts/sc/_delivery_profile.py`, `scripts/sc/_deterministic_review.py`, `scripts/sc/_llm_backend.py`, `scripts/sc/_llm_review_acceptance.py`, `scripts/sc/_llm_review_cli.py`, `scripts/sc/_llm_review_engine.py`, `scripts/sc/_llm_review_exec.py`, `scripts/sc/_llm_review_models.py`, `scripts/sc/_llm_review_prompting.py`, `scripts/sc/_security_profile.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: see engine-managed CLI in `scripts/sc/_llm_review_cli.py`; key runtime knobs include `--delivery-profile`, `--task-id`, `--agents`, `--diff-mode`, `--timeout-sec`, `--agent-timeout-sec`, `--semantic-gate`, `--prompt-budget-gate`, and `--llm-backend codex-cli|openai-api`.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI or an API backend. `--llm-backend openai-api` now validates package/key readiness during self-check and dry-run, and can execute through the minimal Responses API path when explicitly selected.

#### `scripts/sc/llm_review_needs_fix_fast.py`

- Direct local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--task-id`, `--delivery-profile`, `--security-profile`, `--agents`, `--review-template`, `--base`, `--diff-mode`, `--llm-backend`, `--max-rounds`, `--rerun-failing-only`, `--no-rerun-failing-only`, `--time-budget-min`, `--llm-timeout-sec`, `--agent-timeout-sec`, `--step-timeout-sec`, `--min-llm-budget-min`, `--final-pass`, `--skip-sc-test`, `--python`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.
  - First round reviewer selection can auto-shrink from the previous task run's `agent-review.json` or `sc-llm-review` summary when those artifacts exist and are stable.
  - Deterministic reuse can scan recent same-task pipeline artifacts across dates; git snapshot or security-profile mismatch still disables reuse.
  - `--final-pass` disables deterministic shortcuts and reviewer auto-shrink, forces a full reviewer set, and is intended for the last closure run before handoff/PR.
- Behavior notes: round summaries now record `timeout_agents`; when `rc=124` and no child summary was produced, `failure_kind` becomes `timeout-no-summary` so timeout-only rounds are not misread as clean.
- Behavior notes: `--llm-backend codex-cli|openai-api` now passes through to the nested `run_review_pipeline.py -> llm_review.py` call chain, so transport piloting does not require a custom wrapper.
- Behavior notes: before paying for deterministic / LLM work, the script now consumes `chapter6-route` when a recoverable prior run already has `agent-review.json`; only `preferred_lane = run-6.8` may continue, while `inspect-first` / `repo-noise-stop` / `fix-deterministic` / `run-6.7` become controlled stop-loss exits and `record-residual` can auto-write follow-up docs.

#### `scripts/sc/run_review_pipeline.py`

- Direct local deps: `scripts/sc/_active_task_sidecar.py`, `scripts/sc/_agent_review_policy.py`, `scripts/sc/_delivery_profile.py`, `scripts/sc/_harness_capabilities.py`, `scripts/sc/_llm_review_tier.py`, `scripts/sc/_marathon_policy.py`, `scripts/sc/_marathon_state.py`, `scripts/sc/_pipeline_approval.py`, `scripts/sc/_pipeline_events.py`, `scripts/sc/_pipeline_helpers.py`, `scripts/sc/_pipeline_plan.py`, `scripts/sc/_pipeline_session.py`, `scripts/sc/_pipeline_support.py`, `scripts/sc/_repair_guidance.py`, `scripts/sc/_summary_schema.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_technical_debt.py`, `scripts/sc/_util.py`, `scripts/sc/agent_to_agent_review.py`
- Transitive local deps: `scripts/sc/_active_task_sidecar.py`, `scripts/sc/_agent_review_contract.py`, `scripts/sc/_agent_review_policy.py`, `scripts/sc/_approval_contract.py`, `scripts/sc/_artifact_schema.py`, `scripts/sc/_artifact_schema_fallback.py`, `scripts/sc/_delivery_profile.py`, `scripts/sc/_harness_capabilities.py`, `scripts/sc/_llm_review_tier.py`, `scripts/sc/_marathon_policy.py`, `scripts/sc/_marathon_state.py`, `scripts/sc/_pipeline_approval.py`, `scripts/sc/_pipeline_events.py`, `scripts/sc/_pipeline_helpers.py`, `scripts/sc/_pipeline_plan.py`, `scripts/sc/_pipeline_session.py`, `scripts/sc/_pipeline_support.py`, `scripts/sc/_repair_approval.py`, `scripts/sc/_repair_guidance.py`, `scripts/sc/_repair_recommendations.py`, `scripts/sc/_sidecar_schema.py`, `scripts/sc/_summary_schema.py`, `scripts/sc/_summary_schema_fallback.py`, `scripts/sc/_summary_schema_local_hard_checks.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_technical_debt.py`, `scripts/sc/_util.py`, `scripts/sc/agent_to_agent_review.py`
- Subcommands: None.
- Declared args: `--task-id`, `--run-id`, `--fork-from-run-id`, `--godot-bin`, `--delivery-profile`, `--security-profile`, `--reselect-profile`, `--skip-test`, `--skip-acceptance`, `--skip-llm-review`, `--skip-agent-review`, `--allow-full-rerun`, `--allow-repeat-deterministic-failures`, `--allow-full-unit-fallback`, `--llm-agents`, `--llm-backend`, `--llm-timeout-sec`, `--llm-agent-timeout-sec`, `--llm-agent-timeouts`, `--llm-semantic-gate`, `--llm-base`, `--llm-diff-mode`, `--llm-no-uncommitted`, `--llm-strict`, `--review-template`, `--resume`, `--abort`, `--fork`, `--max-step-retries`, `--max-wall-time-sec`, `--context-refresh-after-failures`, `--context-refresh-after-resumes`, `--context-refresh-after-diff-lines`, `--context-refresh-after-diff-categories`, `--dry-run`, `--allow-overwrite`, `--force-new-run-id`.
- Behavior notes: task-scoped previous timeout evidence can inject targeted `--agent-timeouts` for timed-out reviewers only; this is automatic and profile-aware.
- Behavior notes: `--llm-agent-timeouts` is mainly for orchestration layers such as `llm_review_needs_fix_fast.py`; explicit values override auto-derived reviewer timeout bumps.
- Behavior notes: `--llm-backend codex-cli|openai-api` now propagates into the internal `llm_review.py` invocation, so backend pilots can stay on the main task-level orchestration path.
- Behavior notes: fresh non-resume runs inherit the latest same-task `delivery/security profile` lock; switching away from that lock requires explicit `--reselect-profile`.
- Behavior notes: when deterministic is already green in the same invocation and `sc-llm-review` hits a first long timeout, the pipeline records `diagnostics.llm_retry_stop_loss` and skips a second long wait in that round.
- Behavior notes: when the same invocation already proves a known `sc-test` unit failure, the pipeline records `diagnostics.sc_test_retry_stop_loss` and stops the same-run retry instead of paying for another identical attempt.
- Behavior notes: bundles ending as `run_type = planned-only` / `reason = planned_only_incomplete` are evidence-only and must not be reused as producer-run recovery baselines.
- Behavior notes: before a fresh full rerun pays refactor preflight or deterministic cost, the script now consumes `chapter6-route`; recoverable tasks route-block to `inspect-first`, `repo-noise-stop`, `fix-deterministic`, or `run-6.8` instead of blindly reopening 6.7.
- Behavior notes: `--llm-base` defaults to `origin/main`.
- Behavior notes: `--allow-full-unit-fallback` only affects the internal `sc-test` call when task-scoped unit coverage fails at `0.0%`; default delivery profiles keep this off to avoid accidental repo-wide retries.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

#### `scripts/sc/test.py`

- Direct local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_sc_test_refs.py`, `scripts/sc/_sc_test_steps.py`, `scripts/sc/_security_profile.py`, `scripts/sc/_summary_schema.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_sc_test_refs.py`, `scripts/sc/_sc_test_steps.py`, `scripts/sc/_security_profile.py`, `scripts/sc/_summary_schema.py`, `scripts/sc/_summary_schema_fallback.py`, `scripts/sc/_summary_schema_local_hard_checks.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--type`, `--task-id`, `--solution`, `--configuration`, `--delivery-profile`, `--security-profile`, `--godot-bin`, `--run-id`, `--smoke-scene`, `--timeout-sec`, `--skip-smoke`, `--no-coverage-gate`, `--no-coverage-report`, `--allow-full-unit-fallback`
- Behavior notes: when task-scoped unit coverage fails at `0.0%`, the default behavior is fail-fast; `--allow-full-unit-fallback` opts into one explicit retry without the task filter.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Dotnet-related options require `.NET 8 SDK` and valid solution/project paths (default usually `auto`, which resolves to the project-preferred `.sln`).

### Taskmaster triplet and refs maintenance

#### `scripts/python/audit_task_triplet_delivery.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-id`, `--task-ids`, `--require-non-empty-test-refs`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/backfill_semantic_review_tier.py`

- Direct local deps: `scripts/python/_semantic_review_tier_support.py`
- Transitive local deps: `scripts/python/_semantic_review_tier_support.py`
- Subcommands: None.
- Declared args: `--tasks-json-path`, `--tasks-back-path`, `--tasks-gameplay-path`, `--delivery-profile`, `--mode`, `--task-ids`, `--write`, `--rewrite-existing`, `--summary-path`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/build_taskmaster_tasks.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--tag`, `--tasks-file`, `--ids`, `--ids-file`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/check_task_contract_refs.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-files`, `--consistency-whitelist`, `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/check_tasks_all_refs.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--max-warnings`, `--summary-out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/check_tasks_back_references.py`

- Direct local deps: `scripts/python/check_tasks_all_refs.py`
- Transitive local deps: `scripts/python/check_tasks_all_refs.py`
- Subcommands: None.
- Declared args: None.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/migrate_task_optional_hints_to_views.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-ids`, `--write`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/task_links_validate.py`

- Direct local deps: `scripts/python/check_tasks_all_refs.py`, `scripts/python/check_tasks_back_references.py`
- Transitive local deps: `scripts/python/check_tasks_all_refs.py`, `scripts/python/check_tasks_back_references.py`
- Subcommands: None.
- Declared args: `--mode`, `--max-warnings`, `--summary-out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/update_task_test_refs.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-id`, `--add`, `--auto`, `--write`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/update_task_test_refs_from_acceptance_refs.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-id`, `--mode`, `--write`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/validate_semantic_review_tier.py`

- Direct local deps: `scripts/python/_semantic_review_tier_support.py`
- Transitive local deps: `scripts/python/_semantic_review_tier_support.py`
- Subcommands: None.
- Declared args: `--tasks-json-path`, `--tasks-back-path`, `--tasks-gameplay-path`, `--delivery-profile`, `--mode`, `--task-ids`, `--allow-missing`, `--summary-path`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/validate_task_context_required_fields.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-id`, `--stage`, `--context`, `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/validate_task_master_triplet.py`

- Direct local deps: `scripts/python/check_tasks_all_refs.py`
- Transitive local deps: `scripts/python/check_tasks_all_refs.py`
- Subcommands: None.
- Declared args: None.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/validate_task_test_refs.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-id`, `--out`, `--require-non-empty`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

#### `scripts/python/verify_task_mapping.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: None.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

### Utilities and maintenance entrypoints

#### `scripts/python/backfill_acceptance_anchors_in_tests.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--task-ids`, `--all-done`, `--write`, `--migration`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/db_schema_dump.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: `--glob`, `--db`, `--out`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

#### `scripts/python/update_testing_framework_from_fragments.py`

- Direct local deps: None.
- Transitive local deps: None.
- Subcommands: None.
- Declared args: None.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/python/warn_whitelist_expiry.py`

- Direct local deps: `scripts/python/_whitelist_metadata.py`
- Transitive local deps: `scripts/python/_whitelist_metadata.py`
- Subcommands: None.
- Declared args: `--root`, `--whitelist`, `--warn-days`, `--fail-on-expired`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.

## Reverse Dependency Index

Helper modules below are referenced directly by at least two included entry scripts. This section helps migration work avoid copying only the command wrapper and forgetting the shared implementation module.

### `scripts/python/_obligations_freeze_runtime.py`

- `scripts/python/run_obligations_freeze_pipeline.py`
- `scripts/python/run_obligations_jitter_batch5x3.py`

### `scripts/python/_project_health_server.py`

- `scripts/python/project_health_scan.py`
- `scripts/python/serve_project_health.py`

### `scripts/python/_project_health_support.py`

- `scripts/python/check_directory_boundaries.py`
- `scripts/python/detect_project_stage.py`
- `scripts/python/doctor_project.py`
- `scripts/python/project_health_scan.py`

### `scripts/python/_recovery_doc_scaffold.py`

- `scripts/python/new_decision_log.py`
- `scripts/python/new_execution_plan.py`

### `scripts/python/_semantic_review_tier_support.py`

- `scripts/python/backfill_semantic_review_tier.py`
- `scripts/python/validate_semantic_review_tier.py`

### `scripts/python/_whitelist_metadata.py`

- `scripts/python/forbid_manual_sc_triplet_examples.py`
- `scripts/python/warn_whitelist_expiry.py`

### `scripts/python/check_tasks_all_refs.py`

- `scripts/python/check_tasks_back_references.py`
- `scripts/python/task_links_validate.py`
- `scripts/python/validate_task_master_triplet.py`

### `scripts/sc/_agent_review_policy.py`

- `scripts/sc/agent_to_agent_review.py`
- `scripts/sc/run_review_pipeline.py`

### `scripts/sc/_delivery_profile.py`

- `scripts/sc/build.py`
- `scripts/sc/llm_align_acceptance_semantics.py`
- `scripts/sc/llm_check_subtasks_coverage.py`
- `scripts/sc/llm_extract_task_obligations.py`
- `scripts/sc/llm_semantic_gate_all.py`
- `scripts/sc/run_review_pipeline.py`
- `scripts/sc/test.py`

### `scripts/sc/_garbled_gate.py`

- `scripts/sc/check_acceptance_garbled.py`
- `scripts/sc/llm_align_acceptance_semantics.py`
- `scripts/sc/llm_extract_task_obligations.py`
- `scripts/sc/llm_semantic_gate_all.py`

### `scripts/sc/_obligations_extract_helpers.py`

- `scripts/sc/llm_check_subtasks_coverage.py`
- `scripts/sc/llm_extract_task_obligations.py`

### `scripts/sc/_overlay_generator_support.py`

- `scripts/sc/llm_generate_overlays_batch.py`
- `scripts/sc/llm_generate_overlays_from_prd.py`

### `scripts/sc/_security_profile.py`

- `scripts/sc/acceptance_check.py`
- `scripts/sc/build.py`
- `scripts/sc/llm_extract_task_obligations.py`
- `scripts/sc/test.py`

### `scripts/sc/_summary_schema.py`

- `scripts/sc/acceptance_check.py`
- `scripts/sc/run_review_pipeline.py`
- `scripts/sc/test.py`

### `scripts/sc/_taskmaster.py`

- `scripts/sc/acceptance_check.py`
- `scripts/sc/analyze.py`
- `scripts/sc/backfill_task_test_refs.py`
- `scripts/sc/check_tdd_execution_plan.py`
- `scripts/sc/git.py`
- `scripts/sc/llm_align_acceptance_semantics.py`
- `scripts/sc/llm_check_subtasks_coverage.py`
- `scripts/sc/llm_extract_task_obligations.py`
- `scripts/sc/llm_fill_acceptance_refs.py`
- `scripts/sc/llm_generate_red_test.py`
- `scripts/sc/llm_generate_tests_from_acceptance_refs.py`
- `scripts/sc/obligations_baseline_sync.py`
- `scripts/sc/run_review_pipeline.py`

### `scripts/sc/_util.py`

- `scripts/sc/acceptance_check.py`
- `scripts/sc/agent_to_agent_review.py`
- `scripts/sc/analyze.py`
- `scripts/sc/backfill_task_test_refs.py`
- `scripts/sc/build.py`
- `scripts/sc/check_acceptance_garbled.py`
- `scripts/sc/check_tdd_execution_plan.py`
- `scripts/sc/git.py`
- `scripts/sc/llm_align_acceptance_semantics.py`
- `scripts/sc/llm_check_subtasks_coverage.py`
- `scripts/sc/llm_extract_task_obligations.py`
- `scripts/sc/llm_fill_acceptance_refs.py`
- `scripts/sc/llm_generate_overlays_batch.py`
- `scripts/sc/llm_generate_overlays_from_prd.py`
- `scripts/sc/llm_generate_red_test.py`
- `scripts/sc/llm_generate_tests_from_acceptance_refs.py`
- `scripts/sc/llm_review_needs_fix_fast.py`
- `scripts/sc/llm_semantic_gate_all.py`
- `scripts/sc/obligations_baseline_sync.py`
- `scripts/sc/run_review_pipeline.py`
- `scripts/sc/test.py`

## Maintenance Rule

- When adding or deleting a workflow-facing entrypoint, update this document in the same change set as the script.
- If a business repo copies entrypoints from this template, copy the listed direct and transitive local deps in the same migration batch.
- Do not re-add one-off migration or sibling-sync scripts unless they graduate into a recurring workflow and are documented elsewhere first.
