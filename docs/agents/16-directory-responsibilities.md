# Directory Responsibilities

Use this file when you already know **which directory** you are touching but need the local red lines fast.

## Core Runtime And Domain
- `Game.Core/`
  - Responsibility: pure C# domain rules, state machines, services, DTO mapping, and contract-facing logic.
  - Must hold: zero `Godot.*` dependencies, deterministic behavior, xUnit-friendly design.
  - Stop-loss: if a change needs Godot APIs, move the boundary to `Scripts/Adapters/`.
- `Game.Core/Contracts/`
  - Responsibility: contract SSoT for events, DTOs, and interfaces.
  - Must hold: no implementation details, no Godot dependency, XML comments, overlay backlink discipline.
  - Stop-loss: do not copy contract definitions into docs or runtime code.
- `Game.Core.Tests/`
  - Responsibility: xUnit coverage for domain logic and contract behavior.
  - Must hold: clear test naming, task/test refs alignment, coverage gates for formal work.
  - Stop-loss: do not hide missing domain design behind integration-only tests.

## Godot Runtime Boundary
- `Game.Godot/`
  - Responsibility: shipped Godot runtime project and real game resources.
  - Must hold: real runtime assets, autoload wiring, export-safe paths.
  - Stop-loss: do not let tests depend on a divergent mirror copy.
- `Scripts/Core/`
  - Responsibility: runtime-side core implementation that still stays engine-light.
  - Must hold: business logic that can remain outside direct Godot API access.
  - Stop-loss: if `Godot.*` becomes necessary, isolate it behind adapters.
- `Scripts/Adapters/`
  - Responsibility: Godot API boundary, file/network/runtime adapters, scene glue support.
  - Must hold: explicit boundary to engine APIs and host capabilities.
  - Stop-loss: do not leak adapter assumptions back into `Game.Core/`.
- `Scenes/`, `Assets/`
  - Responsibility: runtime resources, scene composition, visual/audio/config assets.
  - Must hold: stable resource paths referenced by tests and overlays.
  - Stop-loss: when a path changes, fix tests, overlays, and contract references in the same change.
- `Tests.Godot/`
  - Responsibility: GdUnit/headless evidence, smoke, and Godot integration assertions.
  - Must hold: evidence of signal wiring, resource loading, scene/runtime integration.
  - Stop-loss: do not move core business assertions here if xUnit can cover them faster.

## Tasks, Recovery, And Automation
- `.taskmaster/tasks/`
  - Responsibility: task triplet SSoT (`tasks.json`, `tasks_back.json`, `tasks_gameplay.json`).
  - Must hold: task metadata, overlay refs, test refs, semantic review tier, acceptance linkage.
  - Stop-loss: prototype work should not be marked done here before promotion.
- `scripts/sc/`
  - Responsibility: task-scoped orchestration, review pipeline, harness sidecars, TDD helpers, LLM workflows.
  - Must hold: task-aware automation, recovery-aware sidecars, profile-sensitive orchestration.
  - Stop-loss: if a script becomes repo-wide and deterministic, consider moving it to `scripts/python/`.
- `scripts/python/`
  - Responsibility: deterministic validators, gates, migration helpers, reports, recovery utilities.
  - Must hold: reusable, non-chat, repo-facing automation.
  - Stop-loss: do not bury task-scoped orchestration semantics here when they belong to `scripts/sc/`.
- `logs/`
  - Responsibility: runtime evidence, CI outputs, sidecars, review artifacts.
  - Must hold: append-only or regenerable evidence, not hand-edited truth.
  - Stop-loss: consume logs for recovery; do not treat them as long-term design docs.
- `execution-plans/`, `decision-logs/`
  - Responsibility: durable intent and durable decisions.
  - Must hold: git-tracked recovery context across sessions and branches.
  - Stop-loss: do not replace them with chat history summaries.

## Docs And Governance
- `docs/architecture/base/`
  - Responsibility: cross-cutting and runtime SSoT in arc42 order.
  - Must hold: template-clean baseline with no project-specific PRD leakage.
  - Stop-loss: feature slices do not belong here except the 08 template.
- `docs/architecture/overlays/`
  - Responsibility: project or PRD-specific feature slices and acceptance-facing architecture deltas.
  - Must hold: backlinks to base chapters, ADRs, contracts, and tests.
  - Stop-loss: do not duplicate base thresholds or policies.
- `docs/adr/`
  - Responsibility: accepted architecture decisions and their history.
  - Must hold: current decision baseline for code and docs changes.
  - Stop-loss: if a change alters policy, update or supersede the ADR instead of silently drifting.
- `docs/workflows/`
  - Responsibility: operator-facing workflow, migration, protocol, and CI playbooks.
  - Must hold: stable procedures, not transient chat plans.
  - Stop-loss: if guidance is compare-range-specific, keep it in a migration report and extract durable rules separately.
- `.github/workflows/`
  - Responsibility: CI entrypoints and job orchestration.
  - Must hold: minimal reproducible automation that matches local hard gates.
  - Stop-loss: do not hide project-specific path assumptions here without documenting them in the matching workflow doc.
