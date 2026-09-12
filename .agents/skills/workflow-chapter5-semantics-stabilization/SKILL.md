---
name: workflow-chapter5-semantics-stabilization
description: Run the fixed Chapter 5 conditional semantics stabilization workflow from workflow.md. Use when a business repo needs task triplet semantics stabilization, lightweight semantic lanes, batch instability handling, acceptance extraction guardrails, or idempotent Chapter 5 recovery before Chapter 6.
---

# Workflow Chapter 5 Semantics Stabilization

## Role

Operate Chapter 5 from `workflow.md` idempotently for a business repository that is a sibling of the template repository.

## Operating Contract

- Treat `workflow.md` as the normative workflow source.
- Treat business-repo logs as empirical evidence, not policy overrides.
- Use Python with UTF-8 for documentation reads and writes.
- Keep generated code, scripts, tests, comments, and log messages in English.
- Do not modify the business repo unless the user explicitly asks for that change.
- Do not rerun expensive steps before reading existing recovery artifacts.
- During Knowledge Control Plane migration, Locator candidates are shadow-only and cannot satisfy acceptance/semantic obligations without direct-source reread and consumer judgment.

## Repository Layout

Template and business repositories are siblings under one parent directory, for example `<parent>/godotgame`, `<parent>/<business-repo-a>`, and `<parent>/<business-repo-b>`.

## Purpose

Use this skill to stabilize task semantics before daily task execution enters the Chapter 6 loop.

## Default Lane

Start with the lightweight single-task lane. Escalate to batch instability only when repeated semantic drift or extraction failure is proven by logs.

## Primary Command Or Action

`Inspect task triplets, overlays, acceptance refs, and semantic review tier before paying for any batch lane.`

## Evidence Rule

Chapter 5 evidence is usually sparse, so workflow.md remains the governing source and logs only tune failure-family recognition.

A `logs/ci/knowledge-context/**` bundle is optional shadow routing evidence only. It cannot replace acceptance refs, task triplets, overlays, or direct source authority.

## Required Reading

1. Read the relevant Chapter 5 section in the template repo `workflow.md`.
2. Read `docs/workflows/knowledge-context-shadow.md` before using the optional Chapter 5 knowledge preflight.
3. Optionally read `references/business-repos/<repo>.md` only as empirical validation evidence when the target business repo has a generated reference.
4. If that optional evidence file is missing or stale, run `py -3 scripts/python/update_workflow_chapter_skills.py <repo>` from the template repo.

## Idempotent Procedure

1. Resolve the target business repo as a sibling of the template repo.
2. Check task triplet validity before semantic stabilization work.
3. Optionally run the Chapter 5 shadow knowledge preflight from `docs/workflows/knowledge-context-shadow.md`. If it returns `fallback_required`, continue from direct authoritative sources.
4. Run lightweight semantic checks before any batch lane.
5. Treat acceptance extraction failure as a stop-and-fix signal, not a reason to add more downstream review.
6. Escalate to batch instability only when the same failure family repeats across tasks.
7. Record durable rule feedback only when a repeated workflow rule gap is proven.

## Stop-Loss Signals

- Existing `forbidden_commands` blocks the command about to be run.
- `artifact_integrity`, `planned_only_incomplete`, or planned-only run type appears in recovery evidence.
- Route evidence recommends inspect-first, record-residual, fix-deterministic, repo-noise-stop, or pause.
- The same deterministic failure fingerprint appears repeatedly.
- The next action would duplicate work already covered by task, overlay, candidate, or manifest evidence.
- A Locator candidate cannot be re-read/hash-verified from repository authority; reject it and use the direct-source path.

## Business Evidence References

Generated evidence may live under `references/business-repos/<repo>.md`. These files are optional regression evidence from known business repositories; they must not define production generation rules.

## Maintenance

Refresh optional evidence after new business-repo logs are generated:

```powershell
py -3 scripts/python/update_workflow_chapter_skills.py <business-repo>
py -3 scripts/python/update_workflow_chapter_skills.py <business-repo-a>,<business-repo-b>
```
