# sanguo (Godot 4.5.1 + C#)

`sanguo` is a Windows-only single-player game project built with Godot 4.5.1 and C# (.NET 8).

## Project Posture

- Delivery profile: `fast-ship`
- Security profile: `host-safe`
- Primary runtime: Windows desktop only
- Primary PRD-ID: `PRD-NEWROUGE-GAME-0001`

## Quick Links

- Agents index: `docs/agents/00-index.md`
- Session recovery: `docs/agents/01-session-recovery.md`
- Project docs index: `docs/PROJECT_DOCUMENTATION_INDEX.md`
- Project health dashboard: `docs/workflows/project-health-dashboard.md`
- Stable public entrypoints: `docs/workflows/stable-public-entrypoints.md`
- Script entrypoints index: `docs/workflows/script-entrypoints-index.md`
- Prototype lane: `docs/workflows/prototype-lane.md`
- Prototype lane playbook: `docs/workflows/prototype-lane-playbook.md`
- Prototype TDD: `docs/workflows/prototype-tdd.md`

## Quick Start (Windows)

1. Install Godot .NET 4.5.1 and .NET 8 SDK.
2. Set Godot binary path in shell:
   - PowerShell: `$env:GODOT_BIN = "C:\Godot\Godot_v4.5.1-stable_mono_win64.exe"`
3. Restore and build:
   - `dotnet restore Sanguo.sln`
   - `dotnet build Sanguo.sln -c Debug`
4. Optional local hard checks:
   - `py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"`

## Recovery First

When resuming a task after a reset or another session, do not guess from scattered logs first.

1. Read `docs/agents/01-session-recovery.md`
2. Run `py -3 scripts/python/dev_cli.py resume-task --task-id <task-id>`
3. Only if that is still insufficient, run `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id <task-id>`
4. Before paying for another full `6.7` or `6.8`, run `py -3 scripts/python/dev_cli.py chapter6-route --task-id <task-id> --recommendation-only`

Before paying for another full `6.7`, read these signals first:

- `Latest reason`
- `Latest run type`
- `Latest reuse mode`
- `Latest artifact integrity`
- `Chapter6 blocked by`
- `Chapter6 stop-loss note`
- `recommended_action_why`
- `chapter6_route_lane` / `repo_noise_reason` from project-health or active-task when available

Recovery stop-loss rules:

- `run_type = planned-only` or `reason = planned_only_incomplete`: treat the bundle as evidence only; do not reopen `6.7` or `6.8` from it
- `Chapter6 blocked by = artifact_integrity`: fall back to the previous real producer bundle before any rerun choice
- `rerun_guard`: deterministic cost should not be paid again blindly
- `llm_retry_stop_loss`: prefer narrow LLM-only closure, not another full rerun
- `sc_test_retry_stop_loss`: same-run unit retry already proved wasteful; fix unit root cause first
- `waste_signals`: engine-lane cost was already wasted after a known unit/root-cause failure
- `recommended_action = needs-fix-fast`: deterministic evidence is already good enough for targeted closure; do not reopen a full rerun first

## Core Repositories and Files

- Taskmaster triplet:
  - `.taskmaster/tasks/tasks.json`
  - `.taskmaster/tasks/tasks_back.json`
  - `.taskmaster/tasks/tasks_gameplay.json`
- PRD input:
  - `.taskmaster/docs/prd.txt`
  - `docs/prd/**`
- Architecture:
  - `docs/architecture/base/**`
  - `docs/architecture/overlays/PRD-NEWROUGE-GAME-0001/08/**`
- ADR index:
  - `docs/architecture/ADR_INDEX_GODOT.md`

## Commands

- Local hard checks:
  - `py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "<godot-bin>"`
  - `py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"`
- Task recovery (canonical):
  - `py -3 scripts/python/dev_cli.py resume-task --task-id <task-id>`
  - `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id <task-id>`
  - `py -3 scripts/python/dev_cli.py chapter6-route --task-id <task-id> --recommendation-only`
- Gate bundle only:
  - `py -3 scripts/python/run_gate_bundle.py --mode hard --task-files .taskmaster/tasks/tasks_back.json .taskmaster/tasks/tasks_gameplay.json`
- Prototype-lane TDD entry:
  - `py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --stage <red|green|refactor> ...`
- Task review pipeline:
  - `py -3 scripts/sc/run_review_pipeline.py --task-id <task-id> --godot-bin "<godot-bin>"`
  - `py -3 scripts/sc/run_review_pipeline.py --task-id <task-id> --godot-bin "$env:GODOT_BIN"`

## Engineering Rules

- Contracts SSoT: `Game.Core/Contracts/**`
- Contract code stays BCL-only, no `Godot.*` references.
- Domain logic in `Game.Core/**`; engine integration in `Game.Godot/**`.
- Logs and evidence go to `logs/**`.
- Keep docs and tasks aligned through ADR + Base + Overlay + Task refs.

## Chapter 7 UI Wiring Entries

- Chapter 7 UI wiring: [docs/gdd/ui-gdd-flow.md](docs/gdd/ui-gdd-flow.md)
- Chapter 7 profile guide: [docs/workflows/chapter7-profile-guide.md](docs/workflows/chapter7-profile-guide.md)
- Default Chapter 7 profile: [docs/workflows/chapter7-profile.json](docs/workflows/chapter7-profile.json)
