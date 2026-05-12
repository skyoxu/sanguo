---
PRD-ID: PRD-SANGUO-V4
Title: Rules Freeze and Assertion Routing
Status: Accepted
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0011
  - ADR-0024
Arch-Refs:
  - CH04
Test-Refs:
  - scripts/python/validate_task_overlays.py
---

# Rules Freeze and Assertion Routing

Route PRD-SANGUO-V4 combat rules freeze, acceptance assertions, and traceability sources into implementation and review without creating parallel combat contracts, schemas, scenes, or event names.

## Inputs

- Primary PRD: `docs/prd/prd_v4.md`.
- Rules freeze source: `docs/prd/PRD_V4_RULES_FREEZE.md`.
- Acceptance assertion source: `docs/prd/PRD_V4_ACCEPTANCE_ASSERTIONS.md`.
- Traceability source: `docs/prd/PRD_V4_TRACEABILITY_MATRIX.md`.

## Routing Rules

- Reuse `SanguoCharacterDefinition` as the character schema extension point and keep `CombatRating` available.
- Reuse `GameStartConfig`, `SanguoCombatStarted`, `SanguoCombatEnded`, `SanguoCombatResolver`, `SanguoBattleView.tscn`, and `SanguoBattleView.cs`; do not create parallel start contracts, combat event names, resolver surfaces, or battle scenes.
- Route v4 combat work through extensions to existing character data, enemy/Boss data, combat contracts, combat resolver behavior, battle view UI, relic effects, and random-event combat triggers.
- Treat conflicts with `docs/prd/PRD_V4_RULES_FREEZE.md` as implementation defects unless superseded by a later freeze revision.
- Use `docs/prd/PRD_V4_ACCEPTANCE_ASSERTIONS.md` assertion IDs as stable references for tasks, tests, CI checks, and review evidence.
- Use `docs/prd/PRD_V4_TRACEABILITY_MATRIX.md` to connect PRD requirements to code evidence, test evidence, and current implementation gaps.
