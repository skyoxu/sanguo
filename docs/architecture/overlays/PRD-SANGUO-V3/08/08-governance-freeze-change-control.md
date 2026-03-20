---
PRD-ID: PRD-SANGUO-V3
Title: V3 Governance - Freeze Change Control
Status: Draft
ADR-Refs:
  - ADR-0005
Arch-Refs:
  - CH07
  - CH10
Test-Refs:
  - scripts/sc/build.py
  - scripts/python/validate_acceptance_refs.py
  - scripts/python/validate_acceptance_anchors.py
---

# V3 Governance - Freeze Change Control

Owner page for `T155`.

## Scope

This page owns the semantic governance of the V3 freeze change-control triplet.
The point is to stop freeze updates from drifting into a docs-only change or a test-only change.

## Explicit Owner Anchor

- `T155`: freeze revision, acceptance assertion update, and executable evidence update must move together.

## Required Triplet

- rules-freeze change in `PRD_V3_RULES_FREEZE.md` or the corresponding overlay owner page
- assertion update in `PRD_V3_ACCEPTANCE_ASSERTIONS.md` and routing overlays
- executable evidence update in tests, gates, or CI summaries

## Routing Boundary

- Semantic owner: this page
- Assertion routing stays in `08-rules-freeze-and-assertion-routing.md`
- Gate execution and schema-valid evidence stay in `08-Contracts-Quality-Metrics.md`

## Stop-the-Line Conditions

- freeze text changes without assertion updates
- assertion changes without executable evidence updates
- task views claim closure while the three legs are not updated in the same change
