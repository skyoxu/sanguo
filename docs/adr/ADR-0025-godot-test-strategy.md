# ADR-0025: Godot Test Strategy (xUnit + GdUnit4)

- Status: Proposed
- Context: Migration Phase-2; CH06 runtime view and CH07 quality gates; TDD-first architecture
- Decision: Use xUnit for pure C# domain tests (Game.Core) with coverage gates (lines ≥90%, branches ≥85%); use GdUnit4 for scene/node integration tests (headless) with JUnit/XML + JSON outputs; keep contracts engine-agnostic
- Consequences: Domain logic must not depend on Godot types; adapters isolate engine APIs; CI runs unit first, then GdUnit4 smoke/security/perf; logs materialize under logs/ per SSoT
- References: docs/migration/Phase-10-Unit-Tests.md, docs/migration/Phase-11-Scene-Integration-Tests.md, docs/migration/Phase-12-Headless-Smoke-Tests.md

