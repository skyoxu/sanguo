---
name: pr-ci-artifact-repair
description: Analyze a failing PR or GitHub Actions run from downloaded CI artifacts or run ids, classify whether the failure is wrapper noise, shared-state test pollution, or a real product regression, then implement the smallest safe fix, record a decision log, validate recovery docs, commit, and push. Use when the user asks to inspect a failing PR, a GitHub Actions run, CI artifact zip files, or repeated dotnet/selfcheck failures.
---

# PR CI Artifact Repair

Use this skill for `newrouge` when a PR or GitHub Actions run is red and the user wants artifact-based diagnosis plus a direct fix.

This skill is not only for fixing the currently red run. After each repair, you must also run a PR-scoped aggregate regression sweep over the failures already exposed by the same PR, so the next push does not rely on GitHub to reveal the next hidden layer.

## Inputs you should expect

- A GitHub Actions `run id`
- Downloaded artifact zips such as `F:\gitlog\ci-logs*.zip` and `F:\gitlog\selfcheck-logs*.zip`
- A request to inspect repeated CI failures, patch the repo, commit, and push

## Non-negotiable repo rules

- Communicate with the user in Chinese.
- Prefer Windows/PowerShell commands.
- Put evidence under `logs/**` and write the repair note to `decision-logs/YYYY-MM-DD-run-<runid>-failure-analysis.md`.
- Validate with `py -3 scripts/python/validate_recovery_docs.py --dir all` before commit.
- Never revert unrelated user changes in the dirty worktree.
- Commit only the files needed for the CI repair.
- Do not stop after the current run turns green locally; perform a PR-level aggregate check covering the issues already exposed by earlier runs of the same PR.
- For PR-scoped aggregate checks, prefer repo-local evidence under `decision-logs/**` and downloaded artifacts under `logs/ci-artifacts/**`; do not rely on `F:\gitlog` unless the user explicitly asks for those historical zips.

## Workflow

1. Read the latest artifacts first.
   - If the user gives zip files, unpack them under `F:\gitlog\<name>_unpacked`.
   - Read at least:
     - `ci-pipeline-summary.json`
     - `dotnet-test-output.txt`
     - `run-dotnet-console.txt`
     - `selfcheck-summary.json`
   - Confirm whether hard gates or Godot selfcheck are already green.

2. Classify the failure before editing code.
   - `Wrapper false-red / retry policy issue`
     - Signals: zero real failed tests, `Passed! - Failed: 0`, `Test Run Aborted`, `Results File:`, `Attachments:`, host crash after green body.
   - `Shared-state pollution inside tests`
     - Signals: very early fan-out `Could not load file or assembly 'Game.Core'`, unknown test case reporting, one test mutates shared repo files or launches nested build/test flows.
   - `Real functional failure`
     - Signals: stable named red tests with coherent assertions, no suite-wide assembly-load collapse.

3. Prefer the smallest layer for the fix.
   - Wrapper/orchestration layer first if the evidence is infrastructure noise.
   - Test-harness isolation second if one test pollutes shared state.
   - Production code only if the failure is a real behavior regression.

4. Validate the exact hypothesis locally.
   - Use targeted test filters instead of full-suite reruns whenever possible.
   - For wrapper changes, add or update regression tests first when practical.
   - For shared-state races, prove the risky pair or group with filtered `dotnet test`.

5. Run a PR-scoped aggregate regression sweep before commit.
   - Build the failure set from the current PR's already-exposed runs.
   - Use, in order:
     - the current run's artifacts
     - prior `decision-logs/YYYY-MM-DD-run-<runid>-failure-analysis.md` for the same PR
     - downloaded artifacts under `logs/ci-artifacts/run-<runid>/`
   - Convert the exposed failures into a concrete local checklist and run it before commit.
   - The goal is to verify not only the current red run, but also the previously exposed failure classes for the same PR, so GitHub does not "peel the onion" one gate at a time.
   - At minimum, the aggregate checklist must cover:
     - the currently failing gate
     - any earlier hard-gate governance failures exposed by the same PR
     - any earlier CI-pipeline governance failures exposed by the same PR
     - any earlier acceptance/gdunit/runtime failures exposed by the same PR
     - `py -3 scripts/python/validate_recovery_docs.py --dir all`
   - When multiple earlier runs failed for the same root cause family, one representative local verification is enough, but you must say which runs it closes.
   - If the PR has a known sequence of failures, prefer one combined local closure sweep over repeated minimal single-run checks.

6. Write the repair note.
   - Create `decision-logs/YYYY-MM-DD-run-<runid>-failure-analysis.md`.
   - Capture:
     - why now
     - artifact-backed context
     - decision
     - consequences
     - recovery impact
     - validation commands
   - Also record which earlier runs from the same PR were covered by the aggregate regression sweep.

7. Finalize cleanly.
   - Run `py -3 scripts/python/validate_recovery_docs.py --dir all`
   - Run the PR-scoped aggregate checklist and make sure its results are captured in the final validation notes.
   - Review staged diff only for repair files
   - Commit with a run-specific message
   - Push the active branch

## PR-Scoped Aggregate Sweep

Use this section when a PR has already produced multiple red runs, especially when earlier fixes revealed later failures in different gates.

### Purpose

- Prevent GitHub from surfacing one hidden problem per push.
- Convert the PR's run history into a local closure checklist.
- Re-check earlier exposed failure families after the latest fix.

### Required procedure

1. Enumerate the runs for the same PR/branch that already produced failure analysis notes or downloaded artifacts.
2. Group them by failure family, for example:
   - `hard-gate governance`
   - `ci-pipeline governance`
   - `acceptance/gdunit/runtime`
   - `wrapper/retry noise`
3. For each family, define one local verification that proves the family is still closed.
4. Run the smallest checklist that covers all exposed families together.
5. In the final note, explicitly say:
   - which runs were covered
   - which failure families were covered
   - which local commands closed them

### Task 133 / PR #154 known failure families

For PR `#154`, do not stop at the currently red run. After each repair, re-check the already exposed families below as a set:

- `26335879347`: hard-gate governance / overlay task drift
- `26336247211`, `26337110878`: CI-pipeline governance / forbidden manual examples in decision logs
- `26336644402`: Godot runtime integration / reward modifier bridge wiring
- `26337401561`: acceptance/gdunit/runtime / reward modifier lifecycle and reward context semantics
- `26339198233`: hard-gate governance / recovery docs format

Recommended closure mindset for this PR:

- recovery docs validation
- governance gate sanity
- Task 133 targeted gdUnit closure
- any directly affected deterministic build/smoke check for the repaired runtime path

If future runs add new failure families, extend this list instead of replacing it.

### Historical PR supplements: #148 to #153

Use these historical PRs to avoid missing older but recurring failure shapes:

- `#148` (`task/T128`): no failing runs worth adding; no extra family observed.
- `#149` (`task/T129`): `Acceptance check (sc)` failures with hard gates and CI pipeline already green, narrowed to `sc-test -> gdunit-hard`. Treat this as the `acceptance/gdunit-hard scene or UI binding regression` family.
- `#150` (`task/T130`): same outer gate pattern as `#149`, again narrowed to `sc-test -> gdunit-hard`. Treat this as the same `acceptance/gdunit-hard scene or UI binding regression` family, not a separate family.
- `#151` (`newgdd`): `CI pipeline (Python)` failure with hard gates and selfcheck already green, narrowed to `dotnet/tests_failed` and unit-level semantic regressions. Treat this as the `ci-pipeline dotnet/unit semantic regression` family.
- `#152` (`newgdd`): `Hard gates bundle (Python)` failure narrowed to `overlay_task_drift`. This matches the `hard-gate governance / overlay drift` family.
- `#153` (`newgdd`): no failing runs worth adding; no extra family observed.

Historical takeaway:

- not every `CI pipeline (Python)` failure is governance-only; some are real `dotnet/unit semantic` regressions
- not every acceptance failure needs full broad reruns; when hard gates and CI pipeline are green, task-scoped `gdunit-hard` plus related smoke/build checks are often the real closure path

## Stable patterns from this PR history

### 1. `run_dotnet.py` retry and artifact isolation

Check `scripts/python/run_dotnet.py` and `scripts/sc/tests/test_run_dotnet_solution_resolution.py` first when CI shows post-run abort noise.

Known good rules:

- Isolate each `dotnet test` attempt into `Game.Core.Tests/TestResults/attempt-N`
- On retry, clean:
  - `Game.Core.Tests/TestResults`
  - `Game.Core.Tests/bin/<Configuration>`
  - `Game.Core/bin/<Configuration>`
- Do not delete `obj` during retry cleanup
- Retry only retryable post-run aborts
- Do not retry deterministic red tests
- Treat exhausted all-green retryable aborts as success with warning

### 2. Shared mutable file or output races inside tests

Look for tests that:

- rewrite `Game.Core/Game.Core.csproj`
- run `dotnet build` or `dotnet restore`
- spawn `acceptance_check.py`, `quality_gates.py`, or other scripts that can trigger nested dotnet work
- read/write repo-root artifacts used by other tests

Known good repairs:

- Serialize shared mutators with an xUnit collection
- Isolate external build outputs with temporary `BaseOutputPath`
- Keep `obj` when `--no-restore` relies on existing assets
- Remove nested acceptance/build/test execution from unit tests; use deterministic fixtures or prebuilt summaries instead

### 3. Decision boundary for `real bug` vs `CI noise`

Treat it as CI noise if:

- build succeeds
- many unrelated tests fail almost immediately
- stack traces collapse into the same missing assembly or unknown test case pattern

Treat it as a real bug if:

- failures stay localized
- assertion messages are coherent
- the same test remains red in filtered local runs without suite interference

### 4. Multi-run PR onion pattern

If the same PR has already failed in multiple different gates across multiple runs, assume hidden sibling failures may still exist.

Required response:

- do not validate only the current gate in isolation
- derive a PR-scoped aggregate checklist from earlier run notes
- re-run the checks for the already exposed families before push
- document which earlier runs are considered closed by the current sweep

### 5. Family-to-check mapping

When building the PR-scoped aggregate checklist, map exposed run families to local verification lanes like this:

- `hard-gate governance / overlay drift`
  - run the smallest relevant hard-gate/governance check
  - include any write-back sync step if the failure family requires updating tracked baselines
- `hard-gate governance / recovery docs`
  - run `py -3 scripts/python/validate_recovery_docs.py --dir all`
- `ci-pipeline governance`
  - run the narrow governance script that failed, not a blind full rerun
- `ci-pipeline dotnet/unit semantic regression`
  - run the narrow `dotnet` or `run_dotnet.py` filter that proves the failing semantic/unit family is closed
- `acceptance/gdunit-hard scene or UI binding regression`
  - run task-scoped `gdunit-hard` targets plus the smallest adjacent smoke/build check needed for confidence
- `acceptance/gdunit/runtime reward or route lifecycle regression`
  - run the exact task-scoped gdUnit set that previously exposed the failure, plus the directly affected deterministic build/smoke checks

## Files to inspect first

- `scripts/python/run_dotnet.py`
- `scripts/sc/tests/test_run_dotnet_solution_resolution.py`
- `Game.Core.Tests/Tasks/Task0092AcceptanceTests.cs`
- `Game.Core.Tests/Tasks/Task2RootBuildGateTests.cs`
- `Game.Core.Tests/Tasks/Task0046AcceptanceTests.cs`
- latest `decision-logs/2026-05-22-run-*-failure-analysis.md`

## Output contract

When you use this skill, do all of the following unless blocked:

- state the classified failure type
- cite the artifact files that proved it
- apply the smallest fix
- run targeted validation
- run a PR-scoped aggregate regression sweep over the already exposed runs for the same PR
- write the decision log
- validate recovery docs
- commit and push

If you cannot complete one of these steps, say exactly what blocked it.
