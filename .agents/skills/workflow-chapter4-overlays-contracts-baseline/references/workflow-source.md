# Workflow Source Summary: Chapter 4

Generated from the template repo `workflow.md` by `scripts/python/update_workflow_chapter_skills.py`.

- Canonical English name: Phase 2: Overlays And Contracts Baseline
- Source line span: 207-280
- Heading count: 5
- Command-like line count: 10
- Artifact/reference line count: 0

## Headings

- 4. Phase 2: Overlays And Contracts Baseline
- 4. Phase 2: Overlays And Contracts Baseline
- 4. Phase 2: Overlays And Contracts Baseline
- 4. Phase 2: Overlays And Contracts Baseline
- 4. Phase 2: Overlays And Contracts Baseline

## Command And Artifact Signals

- `py -3 scripts/sc/llm_generate_overlays_batch.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --page-family core --page-mode scaffold --timeout-sec 1200 --dry-run --batch-suffix first`
- `py -3 scripts/sc/llm_generate_overlays_batch.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --page-family core --page-mode scaffold --timeout-sec 1200 --batch-suffix first-core-sim`
- `py -3 scripts/sc/llm_generate_overlays_from_prd.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --page-filter <overlay-file.md> --page-mode scaffold --timeout-sec 1200 --run-suffix f`
- `py -3 scripts/sc/llm_generate_overlays_batch.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --pages _index.md,ACCEPTANCE_CHECKLIST.md,08-rules-freeze-and-assertion-routing.md --page`
- `py -3 scripts/python/sync_task_overlay_refs.py --prd-id <PRD-ID> --write`
- `py -3 scripts/python/validate_overlay_execution.py --prd-id <PRD-ID> --strict-refs`
- `py -3 scripts/python/check_tasks_all_refs.py`
- `py -3 scripts/python/validate_task_master_triplet.py`
- `py -3 scripts/python/validate_contracts.py`
- `py -3 scripts/python/check_domain_contracts.py`
