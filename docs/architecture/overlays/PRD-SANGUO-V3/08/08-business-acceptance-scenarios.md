---
PRD-ID: PRD-SANGUO-V3
Title: V3 Business Acceptance Scenarios - T111/T149/T150
Status: Accepted
ADR-Refs:
  - ADR-0005
  - ADR-0020
Arch-Refs:
  - CH05
  - CH06
  - CH07
Test-Refs:
  - scripts/sc/acceptance_check.py
  - scripts/python/validate_acceptance_refs.py
  - scripts/python/validate_acceptance_anchors.py
---

# V3 Business Acceptance Scenarios - T111/T149/T150

## Scope

This page owns the semantic acceptance scenarios for the V3 campaign full-loop evidence tasks.
It exists to prevent `08-rules-freeze-and-assertion-routing.md` from becoming the only apparent owner page for business acceptance work.
Routing remains in the routing page; scenario intent, boundaries, and evidence ownership live here.

## Explicit Owner Anchors

- `T111`: business acceptance integration suite aggregator for the split scenarios below.
- `T149`: deterministic full-loop scenario from campaign start to final Boss victory.
- `T150`: deterministic full-loop scenario from campaign start to camp durability defeat.

## Scenario Boundaries

### `T149` Boss-Win Scenario

- Covers campaign start, camp phase progression, board progression, Boss reveal, Boss challenge, and final victory adjudication.
- Must prove milestone ordering remains deterministic and machine-checkable.
- Must include release-closure evidence for explainability cleanliness and replay stability where the scenario touches those systems.

### `T150` Camp-Fail Scenario

- Covers campaign start, camp durability reduction, fatal preemption, defeat routing, and post-failure evidence closure.
- Must prove camp-failure defeat remains terminal and is not silently converted into a normal settlement branch.
- Must remain deterministic enough to serve as CI evidence rather than manual exploratory verification.

## Aggregator Role

- `T111` is not an extra runtime feature task.
- `T111` closes the acceptance bundle by consuming evidence from `T149` and `T150` and by making the suite machine-routable for CI and release checks.
- `T111`, `T149`, and `T150` intentionally keep empty `contractRefs`; if future scenario harnesses consume dedicated evidence events, update this page and both exported task views together.

## Evidence Expectations

- Acceptance evidence must be emitted in a form that `acceptance_check.py` and related validators can consume.
- Failure should identify whether the regression is in scenario setup, milestone ordering, victory/defeat adjudication, replay integrity, or explainability cleanliness.
- This page owns the business-acceptance scenario semantics; `08-rules-freeze-and-assertion-routing.md` only owns routing and assertion-to-gate wiring.
