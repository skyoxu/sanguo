# Prototype TDD

## Purpose

Use this entrypoint when the work is still in `prototype lane`, but you still want a disciplined TDD loop for gameplay, UI, interaction, or local architecture experiments.

It answers whether the idea is worth keeping. It does not replace the formal Chapter 6 delivery path.

## Difference From Formal 6.4 / 6.5 / 6.6

- Prototype TDD can still run `red -> green -> refactor`.
- It does not depend on `.taskmaster/tasks/*.json`.
- It does not depend on acceptance refs, overlay refs, or semantic review.
- It does not publish `run_review_pipeline.py` task recovery sidecars.
- Its outputs are prototype evidence only, not formal delivery evidence.

If the prototype is promoted, rerun the work through the formal path:

```powershell
py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit
py -3 scripts/sc/build.py tdd --task-id <id> --stage green
py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor
```

## Stable Entrypoint

Recommended entrypoint:

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter <Expr>
```

Lower-level script:

```powershell
py -3 scripts/python/run_prototype_tdd.py --slug <slug> --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter <Expr>
```

## Minimal Usage

### 1. Create only the prototype record

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-loop --create-record-only --hypothesis "HUD loop readability is worth keeping"
```

This creates a prototype note under `docs/prototypes/` and exits without running verification.

### 2. Prototype red

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-loop --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter HUDLoop
```

Default behavior:
- `red` defaults to `expect=fail`.
- At least one verification step must fail.
- If all checks pass, the run is marked `unexpected_green`.

### 3. Prototype green

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-loop --stage green --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter HUDLoop
```

Default behavior:
- `green` defaults to `expect=pass`.
- All verification steps must pass.
- Any remaining failure is marked `unexpected_red`.

### 4. Prototype refactor

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-loop --stage refactor --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter HUDLoop
```

Use this to clean up a retained prototype while still keeping it outside the formal task pipeline.

### 5. Godot-side prototype verification

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug ui-flow --stage red --godot-bin "$env:GODOT_BIN" --gdunit-path tests/UI
```

Notes:
- GdUnit runs only when you explicitly pass `--gdunit-path`.
- The run stays scoped to the paths you explicitly select.
- `--gdunit-path` requires `--godot-bin`.

## Common Parameters

- `--slug`
  - Prototype name used in note paths and log paths.
- `--stage red|green|refactor`
  - Prototype TDD stage.
- `--expect auto|fail|pass`
  - Default is `red=fail`, `green/refactor=pass`.
- `--dotnet-target`
  - Repeatable `dotnet test` target.
- `--filter`
  - Dotnet test filter applied to every `--dotnet-target`.
- `--gdunit-path`
  - Repeatable Godot-side verification path.
- `--create-record-only`
  - Create the prototype note without running verification.
- `--skip-record`
  - Run verification only.
- `--related-task-id`
  - Record future formal task ids when they already exist.

## Outputs

- Prototype note: `docs/prototypes/<date>-<slug>.md`
- Summary: `logs/ci/<date>/prototype-tdd-<slug>-<stage>/summary.json`
- Human-readable report: `logs/ci/<date>/prototype-tdd-<slug>-<stage>/report.md`
- Step logs: `logs/ci/<date>/prototype-tdd-<slug>-<stage>/step-*.log`

## Good Fit

Use prototype TDD when you are still proving:
- whether a gameplay loop should stay,
- whether a UI interaction is understandable,
- whether a local architecture option is viable,
- or whether the code path deserves promotion into formal task work.

Do not use it when the work already needs:
- formal Taskmaster tracking,
- acceptance refs / overlay refs / semantic review,
- or formal Chapter 6 evidence for delivery.

## Promotion Rule

When the prototype becomes real work:

1. Create the formal task entry.
2. Add task refs, acceptance refs, and overlay refs.
3. Add execution-plan / decision-log when needed.
4. Return to the formal Chapter 6 flow. Do not treat prototype evidence as done.
