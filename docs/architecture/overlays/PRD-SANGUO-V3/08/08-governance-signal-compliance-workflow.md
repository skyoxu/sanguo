---
PRD-ID: PRD-SANGUO-V3
Title: V3 Governance - Signal Compliance Workflow
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH03
  - CH07
Test-Refs:
  - scripts/sc/build.py
  - scripts/python/validate_contracts.py
  - scripts/python/validate_task_overlays.py
---

# V3 Governance - Signal Compliance Workflow

Owner page for `T157`, `T162`, and `T163`.

## Scope

This page owns the workflow-level governance for signal compliance aggregation and hard-gate wiring.
It does not own the signal contract semantics themselves; those stay in the contract overlays.

## Explicit Owner Anchors

- `T157`: integration closure for the signal compliance workflow lane
- `T162`: deterministic signal compliance aggregation
- `T163`: CI hard-gate wiring and artifact publication

## Boundary With Other Pages

- `T156` signal XML completeness remains owned by `08-Contracts-Sanguo-GameLoop-Events.md`
- runtime leak guard `T158`, `T164`, and `T165` remains owned by `08-feature-slice-t2-monopoly-loop.md`
- gate execution schema and evidence layout remain owned by `08-Contracts-Quality-Metrics.md`

## Workflow Expectations

- aggregate signal-compliance findings deterministically
- publish CI-readable summaries with exact task, gate, and evidence path
- fail hard when workflow wiring claims compliance without the aggregated evidence file

## Stop-the-Line Conditions

- workflow passes without consuming the aggregator output
- aggregator output exists but lacks task or evidence-path identity
- signal-compliance gate is wired only in docs and not in CI execution
