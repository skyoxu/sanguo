---
PRD-ID: PRD-SANGUO-V3
Title: V3 Governance - Logging Policy and Lint
Status: Draft
ADR-Refs:
  - ADR-0003
  - ADR-0005
Arch-Refs:
  - CH03
  - CH07
  - CH10
Test-Refs:
  - scripts/sc/build.py
  - scripts/python/validate_task_overlays.py
---

# V3 Governance - Logging Policy and Lint

Owner page for `T160`.

## Scope

This page owns the observability-policy side of the V3 logging-guidelines and lint gate.
Privacy suppression policy itself remains on the security overlay.

## Explicit Owner Anchor

- `T160`: structured logging baseline, redaction expectations, traceability fields, and lint enforcement

## Boundary With Other Pages

- privacy and non-crash feedback policy remain owned by `08-Contracts-Security.md`
- gate execution, schema validation, and CI evidence collation remain owned by `08-Contracts-Quality-Metrics.md`

## Policy Expectations

- logging examples and lint rules must agree on required fields
- redaction rules must be machine-checkable rather than narrative only
- traceability identifiers must let CI point to gate, task, and evidence path

## Stop-the-Line Conditions

- logging policy changes without lint-rule updates
- lint rules pass while required structured fields are underspecified
- observability policy duplicates or conflicts with security policy text
