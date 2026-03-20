---
PRD-ID: PRD-SANGUO-V3
Title: V3 Contract and Content Task Mapping (Compatibility Filename)
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0010
Arch-Refs:
  - CH03
  - CH05
  - CH07
  - CH10
---

# V3 Contract and Content Task Mapping

Compatibility note: this file keeps the old filename to reduce migration churn in `tasks.json`, `tasks_back.json`, and `tasks_gameplay.json`, but the content is V3 campaign-specific.

This page owns V3 tasks that directly govern contracts and content schema so the repository does not drift into "tasks are growing while contract/schema docs still live in T2".

## Task Groups

### Contract evolution and compatibility

- T73: additive-only compatibility gate
- T109: campaign contracts and DTO mapper completion integration pack
- T145/T146: contract-set completion and HUD DTO mapper closure
- T169/T170: additive set, versioning, and runtime-field harmonization

### Content schema and catalog

- T110: campaign content-pack schema and gate extension integration pack
- T147/T148: schema extension and quality-gate closure
- T171: commander / strategem / building / Boss / objective schema catalog extension
- T172: commander / strategem / building / Boss / objective cross-table constraints and version bump rules

## A-020 Hard Rule

- Contract evolution is additive-only by default.
- remove/rename is invalid unless a deprecation window and migration plan are documented together.
- task views may reference a small sentinel set of extant events only when the gate truly consumes landed runtime contracts; contract, schema, and DTO governance splits should keep empty `contractRefs` rather than borrowing sentinels.

## Sentinel Compatibility Set

The following extant events are the minimum sentinel set currently used by T73 additive-only compatibility checks:

- `core.sanguo.game.started`
- `core.sanguo.boss.challenge.prompted`
- `core.sanguo.random_event.applied`
- `core.sanguo.loot.granted`
- `core.sanguo.game.ended`

The set is intentionally small. It is not full coverage; it is the stop-line set for the highest-value contract families first.

- T109, T145, T146, T147, T148, T151, T169, T170, T171, T172, and T175 currently keep empty `contractRefs`; they are contract, schema, DTO, or assertion-governance tasks first and should not borrow the sentinel set just to look linked.

## Task Ownership Detail

| Task | Concern | Current extant EventType set |
|---|---|---|
| T147 | campaign content schema extension integration pack | none yet; schema-extension governance task with empty `contractRefs` |
| T148 | campaign content quality gates closure | none yet; content-gate governance task with empty `contractRefs` |
| T171 | campaign content schema catalog extension | none yet; schema/catalog task with empty `contractRefs` |
| T172 | campaign content cross-table constraints and bump rules | none yet; cross-table schema gate with empty `contractRefs` |
| T175 | additive-only compatibility closure | none yet; compatibility hard-gate task with empty `contractRefs`; sentinel set stays documented here rather than copied into task views |
## V3 Convergence Goal

- event contracts and content schema are governed separately, but task views backlink both
- pack version, content fingerprint, and schema version enter replay and save-trust inputs
- commander, strategem, building, Boss, and objective data all require machine-checkable schema
- compatibility gates fail on drift between overlay expectation, task-view `contractRefs`, and landed C# contract surface

## Why T110 May Keep Empty `contractRefs`

T110 is primarily a schema and gate task. If it does not publish or consume runtime domain events directly, empty `contractRefs` is correct. The overlay must still define the sentinel contract families that the schema gate protects indirectly.

## Documentation Split

- contract semantics: `08-Contracts-Sanguo-GameLoop-Events.md`
- content data and ranges: `08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md`
- quality gates: `08-Contracts-Quality-Metrics.md`
- freeze ownership: `08-rules-freeze-and-assertion-routing.md`
