---
name: workflow-chapter6-single-task-daily-loop
description: Run the fixed Chapter 6 single-task daily loop from workflow.md. Use when a business repo needs resume-task, chapter6-route, TDD red/green/refactor, 6.7 review pipeline, 6.8 Needs Fix cleanup, 6.9 repository validation, stop-loss, rerun guard, or idempotent recovery from Chapter 6 logs.
---

# Workflow Chapter 6 Single Task Daily Loop

## Role

Operate Chapter 6 from `workflow.md` idempotently for a business repository that is a sibling of the template repository.

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

Use this skill to drive one task through implementation, review, repair, and repository validation.

## Default Lane

Use the top-level Chapter 6 orchestrator unless active-task or chapter6-route already recommends a narrower recovery command.

## Primary Command Or Action

`py -3 scripts/python/dev_cli.py run-single-task-chapter6 --task-id <id> --godot-bin \"$env:GODOT_BIN\" --delivery-profile <profile>`

## Evidence Rule

Chapter 6 has dense business-repo logs. Always read active-task, latest.json, summary.json, repair-guide, agent-review, and run-events before paying for another 6.7 or 6.8.

## Required Reading

1. Read the relevant Chapter 6 section in the template repo `workflow.md`.
2. Optionally read `references/business-repos/<repo>.md` only as empirical validation evidence when the target business repo has a generated reference.
3. If that optional evidence file is missing or stale, run `py -3 scripts/python/update_workflow_chapter_skills.py <repo>` from the template repo.

## Idempotent Procedure

1. Read active-task first when a task id exists.
2. Run resume-task and chapter6-route recommendation-only before expensive reruns.
3. Use the TDD order 6.3, 6.4, 6.5, 6.6 before 6.7 unless recovery evidence says otherwise.
4. Run 6.7 only when deterministic evidence is stale or required by changed implementation, tests, contracts, scripts, or runtime assets.
5. Run 6.8 only when route evidence says Needs Fix cleanup is the right lane.
6. Run 6.9 repository validation before commit or PR closure.

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
