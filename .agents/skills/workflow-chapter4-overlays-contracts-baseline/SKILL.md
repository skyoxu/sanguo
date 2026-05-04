---
name: workflow-chapter4-overlays-contracts-baseline
description: Run the fixed Chapter 4 overlays and contracts baseline workflow from workflow.md. Use when a business repo needs overlay skeleton generation after a valid triplet baseline, overlay refs freezing, contract skeleton creation or adjustment, contract baseline validation, or idempotent overlay/contract recovery before Chapter 5 and Chapter 6.
---

# Workflow Chapter 4 Overlays And Contracts Baseline

## Role

Operate Chapter 4 from `workflow.md` idempotently for a business repository that is a sibling of the template repository.

## Operating Contract

- Treat `workflow.md` as the normative workflow source.
- Treat business-repo logs as empirical evidence, not policy overrides.
- Use Python with UTF-8 for documentation reads and writes.
- Keep generated code, scripts, tests, comments, and log messages in English.
- Do not modify the business repo unless the user explicitly asks for that change.
- Do not rerun expensive steps before reading existing recovery artifacts.

## Repository Layout

Template and business repositories are siblings under one parent directory, for example `<parent>/godotgame`, `<parent>/<business-repo-a>`, and `<parent>/<business-repo-b>`.

## Purpose

Use this skill to establish overlay skeletons, freeze task overlay refs, and validate Game.Core contract baselines after the task triplet is valid.

## Default Lane

Enter Chapter 4 only after the Chapter 3 triplet baseline is clean. Use batch dry-run, batch simulate, outlier single-page repair, then limited apply; never start with full apply.

## Primary Command Or Action

`py -3 scripts/python/sync_task_overlay_refs.py --prd-id <PRD-ID> --write && py -3 scripts/python/validate_overlay_execution.py --prd-id <PRD-ID> --strict-refs`

## Evidence Rule

Chapter 4 depends on real overlay and contract files. Use business-repo overlays and Game.Core/Contracts as structural evidence, but keep workflow.md as the execution policy source.

## Required Reading

1. Read the relevant Chapter 4 section in the template repo `workflow.md`.
2. Optionally read `references/business-repos/<repo>.md` only as empirical validation evidence when the target business repo has a generated reference.
3. If that optional evidence file is missing or stale, run `py -3 scripts/python/update_workflow_chapter_skills.py <repo>` from the template repo.

## Idempotent Procedure

1. Confirm the Chapter 3.9 triplet baseline is clean before generating overlays.
2. Generate overlay skeletons through batch dry-run, batch simulate, single-page repair for outliers, and limited apply.
3. Do not perform full apply in the first overlay pass, and do not mix acceptance rewrites into overlay generation.
4. Freeze overlay refs with sync_task_overlay_refs and validate_overlay_execution, then rerun task refs and triplet validators.
5. Create or adjust contract skeletons under Game.Core/Contracts only, using the workflow contract templates.
6. Validate contract baseline with validate_contracts, check_domain_contracts, and Game.Core.Tests before leaving Chapter 4.

## Stop-Loss Signals

- Existing `forbidden_commands` blocks the command about to be run.
- `artifact_integrity`, `planned_only_incomplete`, or planned-only run type appears in recovery evidence.
- Route evidence recommends inspect-first, record-residual, fix-deterministic, repo-noise-stop, or pause.
- The same deterministic failure fingerprint appears repeatedly.
- The next action would duplicate work already covered by task, overlay, candidate, or manifest evidence.

## Business Evidence References

Generated evidence may live under `references/business-repos/<repo>.md`. These files are optional regression evidence from known business repositories; they must not define production generation rules.

## Maintenance

Refresh optional evidence after new business-repo logs are generated:

```powershell
py -3 scripts/python/update_workflow_chapter_skills.py <business-repo>
py -3 scripts/python/update_workflow_chapter_skills.py <business-repo-a>,<business-repo-b>
```
