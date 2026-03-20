# Overlay Generation SOP

## Purpose

This document defines the standard operating procedure for generating or updating
`docs/architecture/overlays/<PRD-ID>/08/` when a new PRD arrives.

Use these rules unless there is a strong reason to override them:

- Main entry: `py -3 scripts/sc/llm_generate_overlays_batch.py`
- Single-page debug entry: `py -3 scripts/sc/llm_generate_overlays_from_prd.py`
- Default mode: `--page-mode scaffold`
- Default flow: `dry-run -> simulate -> single-page repair -> batch apply`
- Do not start with full `--apply`

## Entry Selection

### Batch Entry

Script:

- `scripts/sc/llm_generate_overlays_batch.py`

Use it when:

- a new PRD is connected for the first time
- you want a page-by-page summary for one PRD wave
- you need isolated output directories per page
- you want one batch summary with similarity ratios

### Single-Page Entry

Script:

- `scripts/sc/llm_generate_overlays_from_prd.py`

Use it when:

- one page from the batch is unstable
- you only want to repair one to three pages
- you need to inspect one page prompt, output, or diff in detail

## Required Inputs

Before running overlay generation, confirm these inputs are ready:

1. Main PRD file exists, for example `prd_v4.md`
2. Companion PRD files exist, for example:
   - `PRD_V4_TRACEABILITY_MATRIX.md`
   - `PRD_V4_RULES_FREEZE.md`
   - `PRD_V4_ACCEPTANCE_ASSERTIONS.md`
3. Task triplet is already aligned with the new PRD:
   - `.taskmaster/tasks/tasks.json`
   - `.taskmaster/tasks/tasks_back.json`
   - `.taskmaster/tasks/tasks_gameplay.json`

If the task triplet is not aligned first, the scripts may still run, but page
routing, task coverage, and overlay intent will drift.

## Recommended Workflow

### Step 1: Core Dry-Run

Start with the `core` family instead of all pages.

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd prd_v4.md --prd-id PRD-SANGUO-V4 --prd-docs PRD_V4_TRACEABILITY_MATRIX.md,PRD_V4_RULES_FREEZE.md,PRD_V4_ACCEPTANCE_ASSERTIONS.md --page-family core --page-mode scaffold --timeout-sec 1200 --dry-run --batch-suffix v4-core-dryrun
```

Goal:

- verify inputs
- verify page selection
- verify batch output directory
- verify prompt artifacts

### Step 2: Core Simulate

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd prd_v4.md --prd-id PRD-SANGUO-V4 --prd-docs PRD_V4_TRACEABILITY_MATRIX.md,PRD_V4_RULES_FREEZE.md,PRD_V4_ACCEPTANCE_ASSERTIONS.md --page-family core --page-mode scaffold --timeout-sec 1200 --batch-suffix v4-core-sim
```

Goal:

- generate candidate pages
- inspect batch summary
- identify low-similarity pages early

### Step 3: Expand by Family

Recommended order:

1. `contracts`
2. `routing`
3. `feature`
4. `governance`

Example:

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd prd_v4.md --prd-id PRD-SANGUO-V4 --prd-docs PRD_V4_TRACEABILITY_MATRIX.md,PRD_V4_RULES_FREEZE.md,PRD_V4_ACCEPTANCE_ASSERTIONS.md --page-family contracts --page-mode scaffold --timeout-sec 1200 --batch-suffix v4-contracts-sim
```

### Step 4: Repair Outlier Pages

If one page is unstable, use the single-page entry.

```powershell
py -3 scripts/sc/llm_generate_overlays_from_prd.py --prd prd_v4.md --prd-id PRD-SANGUO-V4 --prd-docs PRD_V4_TRACEABILITY_MATRIX.md,PRD_V4_RULES_FREEZE.md,PRD_V4_ACCEPTANCE_ASSERTIONS.md --page-filter 08-Contracts-Sanguo-GameLoop-Events.md --page-mode scaffold --timeout-sec 1200 --run-suffix v4-contracts-fix1
```

Use the single-page path when:

- `diff_status=modified` and similarity is too low
- page content drifts into another page's semantics
- one page times out and needs isolated rerun

### Step 5: Apply in Small Batches

Only apply pages after simulate results are reviewed.

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd prd_v4.md --prd-id PRD-SANGUO-V4 --prd-docs PRD_V4_TRACEABILITY_MATRIX.md,PRD_V4_RULES_FREEZE.md,PRD_V4_ACCEPTANCE_ASSERTIONS.md --pages _index.md,ACCEPTANCE_CHECKLIST.md,08-rules-freeze-and-assertion-routing.md --page-mode scaffold --timeout-sec 1200 --apply --batch-suffix v4-apply-core
```

## Parameter Recommendations

### `--page-mode`

Recommended value:

- `scaffold`

Guidance:

- `scaffold`: default path; preserves current page structure where possible
- `patch`: keep only for debug or compatibility checks
- `replace`: use only when there is no stable overlay structure to reuse or a
  full rewrite is intentional

### `--timeout-sec`

Recommended value:

- `1200`

Reason:

- dense routing and contracts pages can exceed 600 seconds
- too small a timeout creates false failures

### `--batch-suffix` and `--run-suffix`

Always prefer explicit suffixes such as:

- `v4-core-sim`
- `v4-contracts-fix1`
- `v4-routing-apply`

Reason:

- easier artifact lookup under `logs/ci/<date>/`
- easier comparison across runs
- avoids accidental result mixing

### `--pages` vs `--page-family`

Use:

- `--page-family` for first-pass grouped review
- `--pages` for precise repair or apply scope

## Artifact Reading

### Batch Artifacts

Batch output example:

- `logs/ci/<date>/sc-llm-overlay-gen-batch-prd-sanguo-v4--v4-core-sim/`

Important files:

- `summary.json`
- `report.md`

Read `report.md` first. It contains:

- page name
- child status
- diff status
- similarity ratio
- child output directory

### Single-Page Artifacts

Single-page output example:

- `logs/ci/<date>/sc-llm-overlay-gen-prd-sanguo-v4--v4-contracts-fix1/`

Important files:

- `summary.json`
- `diff-summary.json`
- `diff-summary.md`
- `page-prompts/`
- `page-outputs/`

## Practical Review Thresholds

Use these review thresholds as a stop-loss guide:

- `diff_status=unchanged`: normally safe
- `modified` and `similarity_ratio >= 0.95`: usually small change, quick review
- `0.90 <= similarity_ratio < 0.95`: manual review required
- `similarity_ratio < 0.90`: do not apply directly; rerun single-page repair

These are working thresholds, not hard gates.

## Known Limits

### Do Not Start With Nightly

Current recommendation is manual execution, not nightly automation, because:

- LLM output still has mild variance
- runtime cost is high
- overlay generation is event-driven, not a daily baseline task

### Do Not Start With Full Apply

If the first pass applies all pages at once, low-similarity pages will be mixed
into the repo before review. That increases manual repair cost.

### Timeout Is Not the Same as Script Failure

If one page times out:

1. rerun that page alone
2. increase `--timeout-sec`
3. inspect prompt and page complexity only after isolated rerun still fails

## Minimal Best-Practice Sequence

1. update PRD files
2. update the task triplet
3. run batch `core` dry-run
4. run batch `core` simulate
5. expand by family
6. rerun outlier pages with the single-page entry
7. apply only reviewed pages in small batches

## Final Recommendation

For a new PRD wave, use:

- main entry: `scripts/sc/llm_generate_overlays_batch.py`
- repair entry: `scripts/sc/llm_generate_overlays_from_prd.py`
- default mode: `scaffold`
- recommended timeout: `1200`
- recommended suffix strategy: always pass `--batch-suffix` or `--run-suffix`
