# Workflow Source Summary: Chapter 7

Generated from the template repo `workflow.md` by `scripts/python/update_workflow_chapter_skills.py`.

- Canonical English name: Phase 5: Chapter 7 UI Wiring Closure
- Source line span: 1136-1325
- Heading count: 8
- Command-like line count: 8
- Artifact/reference line count: 30

## Headings

- 7. Phase 5: Chapter 7 UI Wiring Closure
- 7.1 Entry conditions
- 7.2 Top-level orchestrator
- 7.3 Input collection rules
- 7.4 UI/GDD flow design rules
- 7.5 Hard gate
- 7.6 Task generation rules
- 7.7 Stop and inspect

## Command And Artifact Signals

- `py -3 scripts/python/dev_cli.py run-chapter7-ui-wiring --delivery-profile fast-ship --self-check`
- `py -3 scripts/python/dev_cli.py run-chapter7-ui-wiring --delivery-profile fast-ship --write-doc`
- `py -3 scripts/python/dev_cli.py run-chapter7-ui-wiring --delivery-profile fast-ship --write-doc --create-tasks`
- `py -3 scripts/python/collect_ui_wiring_inputs.py`
- `py -3 scripts/python/validate_chapter7_ui_wiring.py`
- `py -3 scripts/python/validate_chapter7_artifact_manifest.py --manifest logs/ci/<date>/chapter7-ui-wiring/artifact-manifest.json`
- `py -3 scripts/python/dev_cli.py run-chapter7-backlog-gap --design-doc-path <doc> --epics-doc-path <doc> --duplicate-audit-path <doc>`
- `py -3 scripts/python/dev_cli.py apply-chapter7-status-patch --patch logs/ci/<date>/chapter7-ui-wiring/task-status-patch.json --dry-run`
- `Chapter 7 runs after the formal task backlog has been completed through Chapter 6. Its purpose is to convert completed domain and gameplay capabilities into player-facing UI wiring based on `docs/gdd/ui-gdd-flow.md`.`
- `3. `docs/gdd/ui-gdd-flow.md` exists or is about to be created as the governed Chapter 7 artifact.`
- `1. The default template profile now lives at `docs/workflows/chapter7-profile.json`.`
- `2. Pass `--chapter7-profile-path <path>` when a business repo needs to override bucket mapping, closure task ids, task identity templates, labels, refs, screen headings, or surface defaults without forking the Chapter 7 `
- `3. Use `docs/workflows/templates/chapter7-profile.template.json` as the full seed when you need a complete override file.`
- `4. Use `docs/workflows/templates/chapter7-profile.minimal.example.json` when you only need the most common business-repo overrides.`
- `5. See `docs/workflows/chapter7-profile-guide.md` for the field map, minimal override patterns, and field-to-example diff.`
- `2. `chapter7_ui_gdd_writer.py` rewrites `docs/gdd/ui-gdd-flow.md` and `docs/gdd/ui-gdd-flow.candidates.json` when `--write-doc` is enabled.`
- `6. `run_chapter7_ui_wiring.py` writes `logs/ci/<date>/chapter7-ui-wiring/summary.json` as the canonical Chapter 7 run summary.`
- `1. `logs/ci/<date>/chapter7-ui-wiring-inputs/summary.json``
- `3. `docs/gdd/ui-gdd-flow.md``
- `4. `docs/gdd/ui-gdd-flow.candidates.json``
- `5. `logs/ci/<date>/chapter7-ui-wiring/closure-summary.json``
- `9. `logs/ci/<date>/chapter7-ui-wiring/artifact-manifest.json``
- `10. `logs/ci/<date>/chapter7-ui-wiring/artifact-manifest-validation.json``
- `11. `logs/ci/<date>/chapter7-ui-wiring/summary.json``
- `5. Write the default summary to `logs/ci/<date>/chapter7-ui-wiring-inputs/summary.json`.`
- ``docs/gdd/ui-gdd-flow.md` must reorganize capabilities by player experience rather than by technical module. It must cover at least:`
- `8. Candidate follow-up UI tasks in `docs/gdd/ui-gdd-flow.candidates.json`, grouped by screen or surface rather than by raw task order.`
- `1. `docs/gdd/ui-gdd-flow.md` exists.`
- `3. Every `status = done` task in `.taskmaster/tasks/tasks.json` is referenced in `ui-gdd-flow.md` as `T<id>`.`
- `1. Each task must link back to a concrete flow or matrix row in `ui-gdd-flow.md`.`
- `6. Use `ui-gdd-flow.candidates.json` as the machine-readable backlog source when deriving the next Chapter 7 task slice.`
- `3. `ui-gdd-flow.md` lacks required hard-gate sections.`
- `3. `logs/ci/<date>/chapter7-ui-wiring/closure-summary.json``
- `7. `logs/ci/<date>/chapter7-ui-wiring/artifact-manifest.json``
- `8. `logs/ci/<date>/chapter7-ui-wiring/artifact-manifest-validation.json``
- `9. `logs/ci/<date>/chapter7-ui-wiring/summary.json``
