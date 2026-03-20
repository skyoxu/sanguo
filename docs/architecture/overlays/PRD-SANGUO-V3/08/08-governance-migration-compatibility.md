---
PRD-ID: PRD-SANGUO-V3
Title: V3 Governance - Migration Compatibility
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH05
  - CH07
  - CH10
Test-Refs:
  - scripts/sc/build.py
  - scripts/python/validate_task_overlays.py
---

# V3 Governance - Migration Compatibility

Owner page for `T161`, `T166`, `T167`, and `T168`.

## Scope

This page owns the migration-compatibility reporting lane for V3 runtime and task evolution.
It is about report generation and CI enforcement, not about additive-only contract semantics themselves.

## Explicit Owner Anchors

- `T161`: migration compatibility automation gate integration
- `T166`: compatibility report generation
- `T167`: compatibility completeness validation
- `T168`: CI hard-gate integration for the migration report

## Boundary With Other Pages

- additive-only contract evolution remains owned by `08-contracts-taskmap-t50-t65.md`
- gate execution, summary schema, and evidence routing remain owned by `08-Contracts-Quality-Metrics.md`

## Report Expectations

- generated reports identify the exact compatibility surface under review
- completeness validation proves no required migration fields are omitted
- CI hard gate consumes the report rather than relying on narrative checklists

## Stop-the-Line Conditions

- compatibility report exists but omits required surfaces or versions
- completeness validation runs against a different report shape than CI consumes
- migration hard gate reports pass without an attached report artifact
