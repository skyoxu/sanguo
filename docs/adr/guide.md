# ADR Sync Guide (Windows-only)

This guide explains how to keep ADR references in Base docs and PRD chunks consistent with the accepted ADR inventory, and how to triage failures. All commands and scripts are Windows-first and require Node.js. No body content is changed — only front‑matter (FM) ADR lists are updated.

## What This Covers

- Insert ADR-0011 (Windows-only platform & CI) into PRD chunks FM.
- Remove superseded ADR-0009 from PRD chunks FM.
- Verify that Base and PRD FM reference only valid ADRs (Accepted), and no superseded or unknown ones.

## One-shot Sync

- Run: `npm run prd:adr:sync`
  - Steps executed:
    1. `node scripts/adr/apply_adr0011_insertion.mjs`
    2. `node scripts/adr/remove_adr0009.mjs`
    3. `node scripts/adr/scan_adr_refs.mjs` (fails on unknown/superseded refs)

## When To Run

- After adding/updating/removing ADRs under `docs/adr/` (e.g., ADR-0011 accepted, ADR-0009 superseded).
- After adding new PRD chunks under `docs/prd_chunks/`.
- Before release gates and as part of local validation (`npm run guard:base`).

## Logs & Artifacts

- ADR scan reports: `logs/YYYY-MM-DD/adr/`
  - `adr-refs-scan.txt` — human summary (FAIL contexts)
  - `adr-inventory.json` — parsed ADR status (Accepted/Superseded)
  - `base-adr-refs.json` — Base FM references
  - `prd-adr-refs.json` — PRD FM references
- PRD apply actions: `logs/YYYY-MM-DD/prd/`
  - `adr0011-apply-report.json` — which chunks were updated or skipped
  - `remove-adr0009-report.json` — removals performed or skipped
  - Optional preview (dry-run diff): run `node scripts/adr/propose_prd_sync_adr0011.mjs` to generate
    - `adr0011-diff.csv` / `adr0011-diff.json`
    - `adr0011-preview/*.fm.{old,new}`

## Failure Triage (Guard/Scan)

- Symptom: `scan_adr_refs.mjs` exits non‑zero (guard fails)
  - Open `logs/YYYY-MM-DD/adr/adr-refs-scan.txt`
  - Fix the listed files’ FM:
    - Remove superseded ADRs (e.g., ADR-0009)
    - Add missing accepted ADRs where appropriate (e.g., ADR-0011 in platform-related PRD chunks)
  - Re-run: `npm run prd:adr:sync`

## Notes & Conventions

- Scope: Only FM ADR lists are changed; no body or semantics altered.
- Encoding: UTF‑8 (LF). Windows editors are supported; logs use `logs/` dated subfolders.
- ADR-0015 is Proposed. Do not reference it in FM until it becomes Accepted.
- Rollback: Use `git restore` or `git checkout -- <file>` for any affected chunk.

## Related Commands

- `npm run guard:base` — now includes ADR refs scan; fails on superseded/unknown ADR references.
- `npm run docs:index:rebuild` — rebuilds Base index mapping for cross‑checks.

## Prerequisites

- Installed: Node.js (Windows). Python is optional and not required for ADR sync scripts.

## Commit Guidance

- Message example: `docs(prd): sync ADR refs (add ADR-0011, remove ADR-0009)`
- Link ADRs in the commit body where relevant.
