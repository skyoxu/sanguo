# PR CI Artifact Repair History Patterns

This file captures the repair sequence that stabilized the May 22 PR failure chain.

## Wrapper/orchestration fixes

- `26269469736`
  - Isolated `TestResults/attempt-N`
  - Cleaned stale `bin` and `TestResults` between retry attempts
- `26270996986`
  - Preserved `obj` during retry cleanup to avoid Roslyn `refint` breakage
- `26273323011`
  - Stopped retrying deterministic non-retryable red tests
- `26275559462`
  - Expanded retry detection from coverlet file-lock only to broader all-green post-run aborts
- `26277571264`
  - Increased default retry budget from 1 to 2
- `26279613766`
  - Treated retry-budget-exhausted all-green post-run aborts as success with warning

## Shared-state test isolation fixes

- `26276083401`
  - Serialized `Task0092AcceptanceTests` and `Task2RootBuildGateTests` because both touch `Game.Core.csproj`
- `26281365480`
  - Isolated `Task2RootBuildGateTests` external `dotnet build` outputs via temporary `BaseOutputPath`
- `26283827938`
  - Removed recursive `acceptance_check.py` execution from `Task0046AcceptanceTests`; used deterministic fallback summary instead

## Heuristics

- Early suite-wide `Game.Core` load failures usually mean shared-state pollution, not many simultaneous product regressions.
- `Result reported for unknown test case` is a strong hint that discovery and execution assemblies drifted mid-run.
- If selfcheck is green and only `.NET` is red, prefer wrapper/test-harness triage before touching gameplay code.

## Expected end state for a successful repair

- Artifact-backed root cause is written to a dated decision log
- Local targeted verification proves the hypothesis
- Only the minimal repair files are committed
- Branch is pushed after `validate_recovery_docs.py` passes
