# Startup, Stack, And Template Structure

Use this document when you need the old AGENTS content for startup, template shape, stack decisions, or runtime conventions.

## Template Purpose
- Quick start for a Windows-only Godot + C# game project.
- Preconfigured baseline for architecture, testing, CI, and review tooling.
- AI-friendly structure for task-scoped implementation and verification.
- Reusable template that can be copied into a real project with minimal rewiring.

## Target Use Cases
- Windows desktop games, especially simulation, management, and strategy projects.
- Single-player projects with non-trivial game state.
- Projects that benefit from C# domain logic, deterministic tests, and CI gates.
- Teams using AI-assisted development and review loops.

## Opening The Project
- Open `project.godot` with Godot 4.5.1.
- If you use local portable Godot binaries, the legacy file names were `Godot_v4.5.1-stable_win64.exe` and `Godot_v4.5.1-stable_win64_console.exe`.
- The console variant is the safer choice when you need startup diagnostics or headless troubleshooting.

## Template Structure
- `project.godot`: main Godot project configuration.
- `icon.svg`: replace with the copied project's real icon.
- `.godot/`: generated cache and editor state; do not treat it as durable source.
- `Game.Core/`: pure C# domain logic and contracts.
- `Game.Core.Tests/`: xUnit coverage for core logic.
- `Game.Godot/`: runtime scenes, assets, adapters, and autoloads.
- `Tests.Godot/`: Godot-side tests and reports.
- `docs/architecture/base/`: arc42 base chapters.
- `docs/architecture/overlays/<PRD-ID>/08/`: PRD-scoped feature slices.
- `docs/prd/**/*.md`: PRD source material in the current template layout.

## Technology Stack
- Engine: Godot 4.5.x
- UI: Godot Control + Theme/Skin
- Primary language: C# / .NET 8
- Unit tests: xUnit + FluentAssertions + NSubstitute
- Scene tests: GdUnit4
- Coverage: coverlet
- Local data: godot-sqlite, ConfigFile, Godot Resources
- Communication: Signals + Autoload
- Background work: WorkerThreadPool or Thread when required
- Quality and observability: SonarQube, Sentry, structured logs
- Packaging: Godot export templates for Windows

## Stack Rationale
- Prefer C# for core logic because strong typing improves reviewability, testability, and AI generation quality.
- Prefer xUnit for the red-green-refactor loop because pure C# tests are fast and deterministic.
- Use GdUnit4 only where engine behavior, scenes, or signals matter.
- Keep contracts and domain logic outside Godot-specific APIs.
- Do not add new libraries unless the plan or ADR explicitly requires them.

## Runtime Architecture Conventions
### Scene Organization
- Keep features modular and scene-based.
- Prefer one scene per component or responsibility boundary.
- Design scenes so they map cleanly to task-scoped changes.

### Scripting Conventions
- Use C# for core gameplay logic and maintainable systems.
- Use GDScript only where rapid engine-side iteration is justified.
- Keep node glue thin; push logic into testable code paths.
- Use signals for decoupled event flow.

### State Management
- Use Autoloads for true global state only.
- Prefer signals for publish-subscribe changes.
- Persist lightweight settings in `user://` through ConfigFile.

### Data Persistence
- Use `godot-sqlite` for structured game state when needed.
- Use ConfigFile for preferences and light progress data.
- Use Resources for static asset or tuning data.

### Performance Optimization
- Move heavy simulation or AI work off the main thread when possible.
- Keep runtime-critical loops deterministic and measurable.
- Use scene composition to control memory and lifecycle boundaries.

## AI-Assisted Development Integration
- Modular scenes support task-level delegation.
- Strong typing narrows AI ambiguity.
- Three-layer separation keeps core logic testable without the engine.
- Fast unit tests let you validate generated code quickly.
- Observability and quality gates catch bad changes before release.

## Old AGENTS Coverage Map
- `Template Purpose` -> this document
- `Target Use Cases` -> this document
- `Getting Started / Opening the Project / Template Structure` -> this document
- `Technology Stack / Stack Rationale` -> this document
- `Architecture Guidelines` and runtime conventions -> this document
- `AI-Assisted Development Integration` -> this document
