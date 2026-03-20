# Overlay Generation Quickstart

## Purpose

Use this page when a new PRD arrives and you need the shortest safe command set
for overlay generation.

Rules:

- Main entry: `py -3 scripts/sc/llm_generate_overlays_batch.py`
- Single-page repair: `py -3 scripts/sc/llm_generate_overlays_from_prd.py`
- Default mode: `--page-mode scaffold`
- Recommended timeout: `--timeout-sec 1200`
- Always pass `--batch-suffix` or `--run-suffix`

## 1. Core Dry-Run

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd prd_v4.md --prd-id PRD-SANGUO-V4 --prd-docs PRD_V4_TRACEABILITY_MATRIX.md,PRD_V4_RULES_FREEZE.md,PRD_V4_ACCEPTANCE_ASSERTIONS.md --page-family core --page-mode scaffold --timeout-sec 1200 --dry-run --batch-suffix v4-core-dryrun
```

Use this first to validate:

- input files
- page selection
- output directory
- prompt artifacts

## 2. Core Simulate

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd prd_v4.md --prd-id PRD-SANGUO-V4 --prd-docs PRD_V4_TRACEABILITY_MATRIX.md,PRD_V4_RULES_FREEZE.md,PRD_V4_ACCEPTANCE_ASSERTIONS.md --page-family core --page-mode scaffold --timeout-sec 1200 --batch-suffix v4-core-sim
```

Read:

- `logs/ci/<date>/sc-llm-overlay-gen-batch-.../summary.json`
- `logs/ci/<date>/sc-llm-overlay-gen-batch-.../report.md`

## 3. Family Expansion

Example for contracts pages:

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd prd_v4.md --prd-id PRD-SANGUO-V4 --prd-docs PRD_V4_TRACEABILITY_MATRIX.md,PRD_V4_RULES_FREEZE.md,PRD_V4_ACCEPTANCE_ASSERTIONS.md --page-family contracts --page-mode scaffold --timeout-sec 1200 --batch-suffix v4-contracts-sim
```

Recommended order:

1. `core`
2. `contracts`
3. `routing`
4. `feature`
5. `governance`

## 4. Single-Page Repair

Use this when one page is unstable or low-similarity:

```powershell
py -3 scripts/sc/llm_generate_overlays_from_prd.py --prd prd_v4.md --prd-id PRD-SANGUO-V4 --prd-docs PRD_V4_TRACEABILITY_MATRIX.md,PRD_V4_RULES_FREEZE.md,PRD_V4_ACCEPTANCE_ASSERTIONS.md --page-filter 08-Contracts-Sanguo-GameLoop-Events.md --page-mode scaffold --timeout-sec 1200 --run-suffix v4-contracts-fix1
```

## 5. Small-Batch Apply

Only apply reviewed pages:

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd prd_v4.md --prd-id PRD-SANGUO-V4 --prd-docs PRD_V4_TRACEABILITY_MATRIX.md,PRD_V4_RULES_FREEZE.md,PRD_V4_ACCEPTANCE_ASSERTIONS.md --pages _index.md,ACCEPTANCE_CHECKLIST.md,08-rules-freeze-and-assertion-routing.md --page-mode scaffold --timeout-sec 1200 --apply --batch-suffix v4-apply-core
```

## Stop-Loss Rule

- `similarity_ratio >= 0.95`: usually safe for quick review
- `0.90 <= similarity_ratio < 0.95`: review before apply
- `similarity_ratio < 0.90`: do not apply directly; rerun single-page repair
