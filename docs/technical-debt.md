# Technical Debt Register

This file is updated by scripts/sc/run_review_pipeline.py.

- P0/P1 findings stay in the must-fix path and should not be parked here.
- Only P2/P3/P4 items from sc-llm-review are recorded here, grouped by task.

## Maintenance Rules

- The block between BEGIN/END AUTO:RUN_REVIEW_PIPELINE_TECHNICAL_DEBT is auto-managed. Do not hand-edit task sections there unless you are doing emergency cleanup.
- P0/P1 items are not technical-debt parking items in this workflow. They stay on the must-fix path.
- A task section is cleared by rerunning py -3 scripts/sc/run_review_pipeline.py --task-id <id> after the low-priority review findings are resolved. The next successful sc-llm-review replaces that task section.
- Do not mix transient blockers, environment failures, or approval pauses into this file. This register is only for low-priority review debt that can be scheduled intentionally.

<!-- BEGIN AUTO:RUN_REVIEW_PIPELINE_TECHNICAL_DEBT -->
<!-- END AUTO:RUN_REVIEW_PIPELINE_TECHNICAL_DEBT -->
