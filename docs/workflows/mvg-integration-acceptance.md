# MVG Integration Acceptance

This repository carries the bounded MVG integration runner evolved in `skyoxu/newrouge`, adapted to Sanguo's own gameplay contracts.

## Purpose

MVG evidence answers a narrow question: do selected cross-task handoffs still work together on an isolated repository snapshot?

It does **not** authorize Taskmaster status changes, replace Chapter 6 review, or claim full gameplay coverage.

## Commands

Plan and validate the manifest without runtime claims:

```powershell
py -3 scripts/python/run_mvg_acceptance.py --mode plan
```

Recommend related flows for a change range. The recommendation never excludes required tests:

```powershell
py -3 scripts/python/run_mvg_acceptance.py --mode recommend --base <base-sha>
```

Run the complete pilot against the committed revision:

```powershell
py -3 scripts/python/run_mvg_acceptance.py --mode run --snapshot commit --revision HEAD --godot-bin "$env:GODOT_BIN" --challenge-input
```

Optional seeded mutation probe:

```powershell
py -3 scripts/python/run_mvg_mutation_probe.py --snapshot commit --revision HEAD
```

## Sanguo pilot scope

The committed manifest is `docs/testing/mvg/sanguo-pilot.json`.

It combines:

- .NET boundary evidence for `SanguoEconomyRules`.
- GdUnit engine-action input against the real `GameOverFailMenu` -> main-menu route.
- A negative input challenge that temporarily disconnects the real button signal and requires the test to detect the defect.
- Isolated Git snapshot execution through the project-health snapshot implementation already used by repository health checks.

Runtime summaries are written under `logs/ci/mvg-acceptance/**`; mutation evidence goes to `logs/ci/mvg-mutation/**`.

## Impact-analysis alignment

The upstream concurrent Impact failure handling is already present in Sanguo: a losing writer emits failure evidence to an isolated run directory instead of racing the winner's requested output path. Existing `scripts/python/tests/test_analyze_impact_cli.py` concurrency coverage remains the regression authority for that behavior.
