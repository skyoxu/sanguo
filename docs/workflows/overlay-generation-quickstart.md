# Overlay Generation Quickstart

## Purpose

Use this page when a new PRD wave arrives and you need the shortest safe command
set for generating or repairing `docs/architecture/overlays/<PRD-ID>/08/`.

Rules:

- Main entry: `py -3 scripts/sc/llm_generate_overlays_batch.py`
- Single-page repair: `py -3 scripts/sc/llm_generate_overlays_from_prd.py`
- Default mode: `--page-mode scaffold`
- Default timeout: `--timeout-sec 1200`
- Retry timeout for routing or dense contracts pages: `--timeout-sec 1800`
- Always pass `--batch-suffix` or `--run-suffix`
- Every file listed in `--prd-docs` is treated as required input; a missing file is a hard failure

## 1. Core Dry-Run

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd docs/prd/<prd-main>.md --prd-id PRD-<PRODUCT>-V1 --prd-docs docs/prd/<prd-doc-a>.md,docs/prd/<prd-doc-b>.md,docs/prd/<prd-doc-c>.md --page-family core --page-mode scaffold --timeout-sec 1200 --dry-run --batch-suffix <wave>-core-dryrun
```

Use this first to validate:

- input files
- page selection
- output directory
- prompt artifacts

## 2. Core Simulate

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd docs/prd/<prd-main>.md --prd-id PRD-<PRODUCT>-V1 --prd-docs docs/prd/<prd-doc-a>.md,docs/prd/<prd-doc-b>.md,docs/prd/<prd-doc-c>.md --page-family core --page-mode scaffold --timeout-sec 1200 --batch-suffix <wave>-core-sim
```

Read:

- `logs/ci/<date>/sc-llm-overlay-gen-batch-.../summary.json`
- `logs/ci/<date>/sc-llm-overlay-gen-batch-.../report.md`

## 3. Family Expansion

Example for contracts pages:

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd docs/prd/<prd-main>.md --prd-id PRD-<PRODUCT>-V1 --prd-docs docs/prd/<prd-doc-a>.md,docs/prd/<prd-doc-b>.md,docs/prd/<prd-doc-c>.md --page-family contracts --page-mode scaffold --timeout-sec 1200 --batch-suffix <wave>-contracts-sim
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
py -3 scripts/sc/llm_generate_overlays_from_prd.py --prd docs/prd/<prd-main>.md --prd-id PRD-<PRODUCT>-V1 --prd-docs docs/prd/<prd-doc-a>.md,docs/prd/<prd-doc-b>.md,docs/prd/<prd-doc-c>.md --page-filter 08-Contracts-Domain-Events.md --page-mode scaffold --timeout-sec 1800 --run-suffix <wave>-contracts-fix1
```

## 5. Small-Batch Apply

Only apply reviewed pages:

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd docs/prd/<prd-main>.md --prd-id PRD-<PRODUCT>-V1 --prd-docs docs/prd/<prd-doc-a>.md,docs/prd/<prd-doc-b>.md,docs/prd/<prd-doc-c>.md --pages _index.md,ACCEPTANCE_CHECKLIST.md,08-rules-freeze-and-assertion-routing.md --page-mode scaffold --timeout-sec 1200 --apply --batch-suffix <wave>-apply-core
```

## Stop-Loss Rule

- `similarity_ratio >= 0.95`: usually safe for quick review
- `0.90 <= similarity_ratio < 0.95`: review before apply
- `similarity_ratio < 0.90`: do not apply directly; rerun single-page repair
