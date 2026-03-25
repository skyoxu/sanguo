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
- `scripts/python/inspect_run.py`
- `scripts/python/project_health_scan.py`
- `scripts/python/serve_project_health.py`
- `scripts/python/resume_task.py`

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
- `Dotnet required`: `.NET 8 SDK` and valid `Game.sln` / `.csproj` paths must exist.
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
- Declared args: `--delivery-profile`, `--scope`, `--task-ids`, `--fail-on-missing-task-ids`, `--fail-on-missing-views`, `--strict-task-selection`, `--apply`, `--preflight-migrate-optional-hints`, `--skip-preflight-migrate-optional-hints`, `--structural-for-not-done`, `--append-only-for-done`, `--align-view-descriptions-to-master`, `--semantic-findings-json`, `--timeout-sec`, `--max-failures`, `--garbled-gate`, `--self-check`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/sc/llm_check_subtasks_coverage.py`

- Direct local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_obligations_extract_helpers.py`, `scripts/sc/_subtasks_coverage_garbled.py`, `scripts/sc/_subtasks_coverage_llm.py`, `scripts/sc/_subtasks_coverage_schema.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_garbled_gate.py`, `scripts/sc/_obligations_extract_helpers.py`, `scripts/sc/_subtasks_coverage_garbled.py`, `scripts/sc/_subtasks_coverage_llm.py`, `scripts/sc/_subtasks_coverage_schema.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--task-id`, `--delivery-profile`, `--timeout-sec`, `--max-prompt-chars`, `--consensus-runs`, `--strict-view-selection`, `--garbled-gate`, `--max-schema-errors`, `--round-id`, `--self-check`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

#### `scripts/sc/llm_fill_acceptance_refs.py`

- Direct local deps: `scripts/sc/_acceptance_refs_contract.py`, `scripts/sc/_acceptance_refs_helpers.py`, `scripts/sc/_acceptance_refs_prompt.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_acceptance_refs_contract.py`, `scripts/sc/_acceptance_refs_helpers.py`, `scripts/sc/_acceptance_refs_prompt.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--all`, `--task-id`, `--write`, `--overwrite-existing`, `--rewrite-placeholders`, `--timeout-sec`, `--max-refs-per-item`, `--candidate-limit`, `--max-tasks`, `--consensus-runs`, `--self-check`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.
  - Write/apply flows mutate repository files; review diffs before and after execution.

#### `scripts/sc/llm_semantic_gate_all.py`

- Direct local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_garbled_gate.py`, `scripts/sc/_semantic_gate_all_contract.py`, `scripts/sc/_semantic_gate_all_runtime.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_garbled_gate.py`, `scripts/sc/_semantic_gate_all_contract.py`, `scripts/sc/_semantic_gate_all_runtime.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--delivery-profile`, `--task-ids`, `--batch-size`, `--timeout-sec`, `--consensus-runs`, `--model-reasoning-effort`, `--max-acceptance-items`, `--max-prompt-chars`, `--max-tasks`, `--max-needs-fix`, `--max-unknown`, `--garbled-gate`, `--self-check`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

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
- Declared args: `--task-id`, `--delivery-profile`, `--timeout-sec`, `--max-prompt-chars`, `--consensus-runs`, `--min-obligations`, `--round-id`, `--security-profile`, `--garbled-gate`, `--auto-escalate`, `--escalate-max-runs`, `--escalate-task-ids`, `--max-schema-errors`, `--reuse-last-ok`, `--explain-reuse-miss`, `--dry-run-fingerprint`, `--self-check`
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
- Declared args: `--write`, `--dry-run`, `--prd-id`, `--tasks-dir`
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
  - Dotnet-related options require `.NET 8 SDK` and valid solution/project paths (default usually `Game.sln`).

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
- Subcommands: `run-ci-basic`, `run-quality-gates`, `run-local-hard-checks`, `run-gdunit-hard`, `run-gdunit-full`, `run-preflight`, `run-smoke-strict`, `new-execution-plan`, `new-decision-log`, `resume-task`, `detect-project-stage`, `doctor-project`, `check-directory-boundaries`, `project-health-scan`, `serve-project-health`
- Declared args: `--solution`, `--configuration`, `--godot-bin`, `--delivery-profile`, `--task-file`, `--out-dir`, `--run-id`, `--legacy-preflight`, `--build-solutions`, `--gdunit-hard`, `--smoke`, `--timeout-sec`, `--test-project`, `--title`, `--status`, `--goal`, `--scope`, `--current-step`, `--stop-loss`, `--next-action`, `--exit-criteria`, `--adr`, `--decision-log`, `--task-id`, `--latest-json`, `--output`, `--why-now`, `--context`, `--decision`, `--consequences`, `--recovery-impact`, `--validation`, `--supersedes`, `--superseded-by`, `--execution-plan`, `--repo-root`, `--latest`, `--out-json`, `--out-md`, `--serve`, `--port`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Dotnet-related options require `.NET 8 SDK` and valid solution/project paths (default usually `Game.sln`).
  - Serving parameters are local-only: use on `127.0.0.1`, not in CI.

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
- Declared args: `--repo-root`, `--latest`, `--kind`, `--task-id`, `--run-id`, `--out-json`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.

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
  - Dotnet-related options require `.NET 8 SDK` and valid solution/project paths (default usually `Game.sln`).

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
  - Dotnet-related options require `.NET 8 SDK` and valid solution/project paths (default usually `Game.sln`).

#### `scripts/python/resume_task.py`

- Direct local deps: `scripts/python/inspect_run.py`, `scripts/python/validate_recovery_docs.py`
- Transitive local deps: `scripts/python/inspect_run.py`, `scripts/python/validate_recovery_docs.py`
- Subcommands: None.
- Declared args: `--repo-root`, `--task-id`, `--run-id`, `--latest`, `--out-json`, `--out-md`
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
  - Dotnet-related options require `.NET 8 SDK` and valid solution/project paths (default usually `Game.sln`).

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
  - Dotnet-related options require `.NET 8 SDK` and valid solution/project paths (default usually `Game.sln`).

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

- Direct local deps: `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--task-id`, `--timeout-sec`, `--verify-red`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

#### `scripts/sc/llm_generate_tests_from_acceptance_refs.py`

- Direct local deps: `scripts/sc/_acceptance_testgen_flow.py`, `scripts/sc/_acceptance_testgen_llm.py`, `scripts/sc/_acceptance_testgen_quality.py`, `scripts/sc/_acceptance_testgen_red.py`, `scripts/sc/_acceptance_testgen_refs.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_acceptance_testgen_flow.py`, `scripts/sc/_acceptance_testgen_llm.py`, `scripts/sc/_acceptance_testgen_quality.py`, `scripts/sc/_acceptance_testgen_red.py`, `scripts/sc/_acceptance_testgen_refs.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--task-id`, `--timeout-sec`, `--select-timeout-sec`, `--tdd-stage`, `--verify`, `--godot-bin`, `--include-prd-context`, `--prd-context-path`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

#### `scripts/sc/llm_review.py`

- Direct local deps: `scripts/sc/_llm_review_engine.py`
- Transitive local deps: `scripts/sc/_acceptance_artifacts.py`, `scripts/sc/_delivery_profile.py`, `scripts/sc/_deterministic_review.py`, `scripts/sc/_llm_review_acceptance.py`, `scripts/sc/_llm_review_cli.py`, `scripts/sc/_llm_review_engine.py`, `scripts/sc/_llm_review_exec.py`, `scripts/sc/_llm_review_models.py`, `scripts/sc/_llm_review_prompting.py`, `scripts/sc/_security_profile.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: None.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

#### `scripts/sc/llm_review_needs_fix_fast.py`

- Direct local deps: `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--task-id`, `--security-profile`, `--agents`, `--review-template`, `--base`, `--diff-mode`, `--max-rounds`, `--rerun-failing-only`, `--time-budget-min`, `--llm-timeout-sec`, `--agent-timeout-sec`, `--step-timeout-sec`, `--skip-sc-test`, `--python`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

#### `scripts/sc/run_review_pipeline.py`

- Direct local deps: `scripts/sc/_active_task_sidecar.py`, `scripts/sc/_agent_review_policy.py`, `scripts/sc/_delivery_profile.py`, `scripts/sc/_harness_capabilities.py`, `scripts/sc/_llm_review_tier.py`, `scripts/sc/_marathon_policy.py`, `scripts/sc/_marathon_state.py`, `scripts/sc/_pipeline_approval.py`, `scripts/sc/_pipeline_events.py`, `scripts/sc/_pipeline_helpers.py`, `scripts/sc/_pipeline_plan.py`, `scripts/sc/_pipeline_session.py`, `scripts/sc/_pipeline_support.py`, `scripts/sc/_repair_guidance.py`, `scripts/sc/_summary_schema.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_technical_debt.py`, `scripts/sc/_util.py`, `scripts/sc/agent_to_agent_review.py`
- Transitive local deps: `scripts/sc/_active_task_sidecar.py`, `scripts/sc/_agent_review_contract.py`, `scripts/sc/_agent_review_policy.py`, `scripts/sc/_approval_contract.py`, `scripts/sc/_artifact_schema.py`, `scripts/sc/_artifact_schema_fallback.py`, `scripts/sc/_delivery_profile.py`, `scripts/sc/_harness_capabilities.py`, `scripts/sc/_llm_review_tier.py`, `scripts/sc/_marathon_policy.py`, `scripts/sc/_marathon_state.py`, `scripts/sc/_pipeline_approval.py`, `scripts/sc/_pipeline_events.py`, `scripts/sc/_pipeline_helpers.py`, `scripts/sc/_pipeline_plan.py`, `scripts/sc/_pipeline_session.py`, `scripts/sc/_pipeline_support.py`, `scripts/sc/_repair_approval.py`, `scripts/sc/_repair_guidance.py`, `scripts/sc/_repair_recommendations.py`, `scripts/sc/_sidecar_schema.py`, `scripts/sc/_summary_schema.py`, `scripts/sc/_summary_schema_fallback.py`, `scripts/sc/_summary_schema_local_hard_checks.py`, `scripts/sc/_taskmaster.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_technical_debt.py`, `scripts/sc/_util.py`, `scripts/sc/agent_to_agent_review.py`
- Subcommands: None.
- Declared args: None.
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Model-backed steps require the repo's LLM runtime/CLI; deterministic-only or skip modes can reduce that requirement, but do not assume zero-model execution unless the script explicitly supports it.

#### `scripts/sc/test.py`

- Direct local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_sc_test_refs.py`, `scripts/sc/_sc_test_steps.py`, `scripts/sc/_security_profile.py`, `scripts/sc/_summary_schema.py`, `scripts/sc/_util.py`
- Transitive local deps: `scripts/sc/_delivery_profile.py`, `scripts/sc/_sc_test_refs.py`, `scripts/sc/_sc_test_steps.py`, `scripts/sc/_security_profile.py`, `scripts/sc/_summary_schema.py`, `scripts/sc/_summary_schema_fallback.py`, `scripts/sc/_summary_schema_local_hard_checks.py`, `scripts/sc/_taskmaster_paths.py`, `scripts/sc/_util.py`
- Subcommands: None.
- Declared args: `--type`, `--task-id`, `--solution`, `--configuration`, `--delivery-profile`, `--security-profile`, `--godot-bin`, `--run-id`, `--smoke-scene`, `--timeout-sec`, `--skip-smoke`, `--no-coverage-gate`, `--no-coverage-report`
- Parameter prerequisites:
  - Windows PowerShell + `py -3` from repo root.
  - Engine-side options require a local Godot .NET console binary; without it, Godot/GdUnit/smoke stages will skip or fail depending on the script.
  - Task-scoped parameters require a Taskmaster triplet; template fallback can read `examples/taskmaster/**`, but business repos should use real `.taskmaster/tasks/*.json`.
  - Dotnet-related options require `.NET 8 SDK` and valid solution/project paths (default usually `Game.sln`).

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

