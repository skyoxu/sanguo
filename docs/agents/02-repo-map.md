# Repo Map

## Root
- `AGENTS.md`: short index for agents.
- `README.md`: human-facing project overview.
- `DELIVERY_PROFILE.md`: profile model and switching rules.
- `execution-plans/`: versioned execution checkpoints.
- `decision-logs/`: versioned architecture and workflow decisions.
- `logs/`: runtime and CI evidence, not the durable source of intent.

## Product Code
- `Game.Core/`: pure C# domain, contracts, services, repositories, state.
- `Game.Core.Tests/`: xUnit coverage for core logic.
- `Game.Godot/`: Godot runtime assets, scenes, adapters, autoloads, UI resources.
- `Tests.Godot/`: Godot-side test project and reports.

## Governance And Design
- `docs/adr/`: accepted and historical ADRs.
- `docs/architecture/base/`: arc42 base chapters.
- `docs/architecture/overlays/`: PRD-scoped overlays and feature slices.
- `docs/workflows/`: workflow and gate methodology.
- `docs/agents/`: durable agent recovery and harness docs.

## Automation
- `scripts/sc/`: review pipeline, acceptance, llm review, task analysis.
- `scripts/python/`: validation, gates, sync, reporting, and guardrail scripts.
- `.github/workflows/`: CI entry points.
- `.taskmaster/`: primary Taskmaster triplet and derived planning data for this repository.
- `examples/taskmaster/`: compatibility fallback used by some template-oriented scripts and tests; do not treat it as the repository SSoT.
