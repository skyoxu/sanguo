---
name: workflow-chapter3-task-triplet-baseline
description: Run the fixed Chapter 3 task triplet generation and baseline workflow from workflow.md. Use when a business repo is initialized with authoritative Taskmaster triplet files, when new tasks are added, when requirements must be converted into task candidates, when coverage must be audited before triplet compilation, when tasks.json must be rebuilt from tasks_back.json and tasks_gameplay.json, or when task links, refs, triplet consistency, or semantic review tier baseline must be validated before Chapter 4 overlays.
---

# Workflow Chapter 3 Task Triplet Baseline

## Role

Operate Chapter 3 from `workflow.md` idempotently for a business repository that is a sibling of the template repository.

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

Use this skill to create or refresh the authoritative task triplet baseline from requirement anchors, enriched task candidates, coverage audit, and triplet compilation before overlays, contracts, and Chapter 6 execution depend on it.

## Default Lane

For new project initialization, extract requirement anchors, normalize them into implementation-shaped task intents, generate normalized task candidates, enrich them with repository evidence, audit coverage, compile a patch, then build or confirm all three task files and run the full baseline. For added tasks, run the same chain on changed sources and rerun the baseline before Chapter 4 or Chapter 6 uses the changed task set.

## Primary Command Or Action

`py -3 scripts/python/extract_requirement_anchors.py --mode <init|add> --prd-path <path> --gdd-path <path> --epics-path <path> --stories-path <path> && py -3 scripts/python/normalize_task_intents.py --mode <init|add> && py -3 scripts/python/audit_task_intents_quality.py && py -3 scripts/python/generate_task_candidates_from_sources.py --mode <init|add> && py -3 scripts/python/enrich_task_candidates.py && py -3 scripts/python/audit_task_candidate_coverage.py && py -3 scripts/python/compile_task_triplet.py --mode <init|add>`

## Evidence Rule

Chapter 3 depends on real requirements and triplet files. This template repo may not have business tasks, so use business-repo triplet structure as evidence, pass explicit PRD/GDD/epics/stories paths for each business repo, enrich candidates from repository ADR/overlay/contract-event/test evidence, then audit coverage and validate the target repo directly. Do not treat ADR or overlay files as default requirement sources; include them with --source-glob only when they are intentionally part of planning input.

## Required Reading

1. Read the relevant Chapter 3 section in the template repo `workflow.md`.
2. Optionally read `references/business-repos/<repo>.md` only as empirical validation evidence when the target business repo has a generated reference.
3. If that optional evidence file is missing or stale, run `py -3 scripts/python/update_workflow_chapter_skills.py <repo>` from the template repo.

## Idempotent Procedure

1. Resolve whether the run is new project initialization or added-task refresh.
2. For new project initialization, prepare PRD, GDD, epics, stories, traceability, and rules-supporting docs before building task files.
3. Extract requirement anchors with extract_requirement_anchors.py, passing explicit --prd-path, --gdd-path, --epics-path, and --stories-path values when the business repo layout differs from template defaults. Keep ADR/overlay sources out of default extraction unless explicitly requested.
4. Normalize requirement anchors into implementation-shaped task intents with normalize_task_intents.py; preserve requirement_ids and source_refs.
5. Audit task intent quality with audit_task_intents_quality.py and review duplicate prefixes, generic titles, metadata noise, or oversized intent groups before compiling task views.
6. Generate normalized task candidates with generate_task_candidates_from_sources.py; do not let an LLM write final tasks.json directly.
7. Enrich candidates with enrich_task_candidates.py using ADRs, overlays, contract event constants, tests, existing tasks, owner/layer, acceptance, evidence refs, and duplicate-candidate evidence.
8. Audit coverage with audit_task_candidate_coverage.py and stop when any P0/P1 requirement is missing coverage.
9. Compile a task triplet patch with compile_task_triplet.py; use --write only after reviewing the patch.
10. Build or refresh tasks.json from tasks_back.json and tasks_gameplay.json with build_taskmaster_tasks.py.
11. Run task_links_validate, check_tasks_all_refs, and validate_task_master_triplet as the baseline gate.
12. Backfill semantic review tier conservatively and validate it unless the repo already has a clean conservative baseline.
13. Optionally run run_chapter3_regression_check.py against one or more business repos as read-only regression evidence; do not tune rules to exactly reproduce mature Chapter 4/5/6/7 task history.
14. When new tasks are added after Chapter 3, rerun the baseline gate before Chapter 4 overlay work or Chapter 6 task execution.

## 用户交互文案要求

- Chapter 3 面向用户的说明、分步确认与阻断提示使用中文。
- 任务文件与文档中若写入中文，必须通过 Python 并显式 `encoding=\"utf-8\"` 写入，避免终端编码导致乱码。

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
