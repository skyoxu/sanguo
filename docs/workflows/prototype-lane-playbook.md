# Prototype Lane Playbook

## 1. Decide Whether Prototype Lane Is The Right Path

Use prototype lane when:

- you are still proving whether a mechanic is worth building,
- you are still testing whether a UI or interaction is understandable,
- you are still evaluating a local architecture option,
- you want the smallest possible code and test loop first,
- and you are not ready to move the work into formal `.taskmaster/tasks/*.json` tracking.

Do not use prototype lane when:

- the work is already a formal delivery task,
- the work already needs acceptance refs, overlay refs, or semantic review,
- the work must serve as Chapter 6 delivery evidence,
- or the work is clearly ready for `run_review_pipeline.py`.

Short rule:

- prototype lane answers "should this become real work?"
- formal Chapter 6 answers "how do we deliver this real work safely?"

## 2. Recommended End-to-End Flow

Use this order:

1. Write the hypothesis.
2. Create the prototype record.
3. Run prototype red.
4. Implement the smallest code change.
5. Run prototype green.
6. Run prototype refactor only when needed.
7. Decide `discard | archive | promote`.
8. If the answer is `promote`, move back to the formal Chapter 6 flow.

## 3. Step 1: Create The Prototype Record

Recommended command:

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --create-record-only --hypothesis "<what are you proving>"
```

Recommended fields to fill early:

- `--hypothesis`
- `--scope-in`
- `--scope-out`
- `--success-criteria`
- `--next-step`

Example:

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-loop --create-record-only --hypothesis "HUD loop readability is worth keeping" --scope-in "HUD tick loop" --scope-out "formal task refs" --success-criteria "A red test proves the loop is not implemented yet" --success-criteria "A green test proves the loop is understandable enough to keep"
```

Artifact:

- `docs/prototypes/<date>-<slug>.md`

## 4. Step 2: Run Prototype Red

### 4.1 Pure C# prototype

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter <Expr>
```

Use this when you want to prove that the behavior is still missing.

Default semantics:

- `red` defaults to `--expect fail`
- at least one verification step must fail
- if every check passes, the run becomes `unexpected_green`

### 4.2 Godot / GdUnit prototype

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --stage red --godot-bin "$env:GODOT_BIN" --gdunit-path tests/UI
```

Notes:

- GdUnit runs only when you explicitly pass `--gdunit-path`
- `--gdunit-path` requires `--godot-bin`
- the run stays scoped to the exact Godot test paths you choose

## 5. Step 3: Implement The Smallest Change, Then Run Prototype Green

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --stage green --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter <Expr>
```

Default semantics:

- `green` defaults to `--expect pass`
- every verification step must pass
- any remaining failure becomes `unexpected_red`

Mental model:

- prototype red proves the idea is not implemented yet
- prototype green proves the idea is viable in the current small scope

## 6. Step 4: Run Prototype Refactor Only When Needed

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --stage refactor --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter <Expr>
```

Good fit:

- you want to keep the prototype around for a while,
- you want to clean temporary code,
- and you still want prototype-level verification afterward.

Not the goal:

- this is not formal delivery completion,
- and it does not replace Chapter 6.

## 7. Step 5: Read The Outputs And Decide

Each prototype TDD run writes:

- prototype note:
  - `docs/prototypes/<date>-<slug>.md`
- summary:
  - `logs/ci/<date>/prototype-tdd-<slug>-<stage>/summary.json`
- report:
  - `logs/ci/<date>/prototype-tdd-<slug>-<stage>/report.md`
- raw step logs:
  - `logs/ci/<date>/prototype-tdd-<slug>-<stage>/step-*.log`

Decision meanings:

- `discard`
  - the idea failed; stop here
- `archive`
  - keep the evidence, but do not move into formal delivery yet
- `promote`
  - the idea is now ready to become real task work

## 8. If The Answer Is Promote, What Happens Next

Do not keep treating prototype artifacts as formal delivery results.

Switch back to the formal path:

1. Create the formal task entry.
2. Add task refs, acceptance refs, and overlay refs.
3. Add execution-plan / decision-log when needed.
4. Return to formal Chapter 6.

Recommended formal commands:

```powershell
py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit
py -3 scripts/sc/build.py tdd --task-id <id> --stage green
py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship
```

## 9. Practical Command Templates

### Template A: small pure C# mechanic

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combo-rule --create-record-only --hypothesis "Combo rule is worth keeping"
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combo-rule --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter ComboRule
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combo-rule --stage green --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter ComboRule
```

### Template B: UI / Godot interaction

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-flow --create-record-only --hypothesis "HUD flow is understandable enough to keep"
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-flow --stage red --godot-bin "$env:GODOT_BIN" --gdunit-path tests/UI
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-flow --stage green --godot-bin "$env:GODOT_BIN" --gdunit-path tests/UI
```

### Template C: first C#, then Godot verification

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug target-selection --create-record-only --hypothesis "Target selection flow is worth promoting"
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug target-selection --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter TargetSelection
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug target-selection --stage green --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter TargetSelection
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug target-selection --stage green --godot-bin "$env:GODOT_BIN" --gdunit-path tests/UI
```

## 10. Common Mistakes

Do not:

- use prototype lane as a replacement for the formal delivery flow,
- treat prototype red/green as Chapter 6 delivery evidence,
- change long-lived contracts during prototype work without creating formal follow-up work,
- or stay in prototype lane after the work is clearly real product work.

## 11. Fast Decision Tree

- Is the question still "is this worth doing"?
  - yes: start with prototype lane
  - no: go directly to formal Chapter 6
- Do you still want TDD while exploring?
  - yes: use `run-prototype-tdd`
- Did the result clearly prove the idea should stay?
  - yes: choose `promote` and move back to the formal task flow
- Is the result only partially useful, but not ready for delivery?
  - choose `archive`
- Did the result prove the direction is wrong?
  - choose `discard`
