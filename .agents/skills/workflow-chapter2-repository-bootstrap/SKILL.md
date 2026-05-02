---
name: workflow-chapter2-repository-bootstrap
description: Run the fixed Chapter 2 repository bootstrap workflow from workflow.md. Use when a new business repo is copied from the template and needs name/path cleanup, entry index rebuild, local hard checks, optional project-health dashboard service, or explicit opt-in OpenAI backend bootstrap.
---

# Workflow Chapter 2 Repository Bootstrap

## Role

Operate Chapter 2 from `workflow.md` idempotently for a business repository that is a sibling of the template repository.

## Operating Contract

- Treat `workflow.md` as the normative workflow source.
- Treat business-repo logs as empirical evidence, not policy overrides.
- Use Python with UTF-8 for documentation reads and writes.
- Keep generated code, scripts, tests, comments, and log messages in English.
- Do not modify the business repo unless the user explicitly asks for that change.
- Do not rerun expensive steps before reading existing recovery artifacts.

## Repository Layout

Template and business repositories are siblings under one parent directory, for example `<parent>/godotgame`, `<parent>/sanguo`, and `<parent>/newrouge`.

## Purpose

Use this skill to bootstrap a copied template repository into a clean business repository before task triplets and overlays are created.

## Default Lane

Clean project identity and indexes first, run repository-level hard checks immediately after that, and start project-health only when an interactive local dashboard is useful.

## Primary Command Or Action

`py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"`

## Evidence Rule

Chapter 2 is an early bootstrap workflow. Prefer direct repository checks and project-health artifacts over historical task logs; OpenAI backend bootstrap is explicit opt-in only.

## Required Reading

1. Read the relevant Chapter 2 section in the template repo `workflow.md`.
2. Inspect the target repository state directly; Chapter 2 does not use historical business-repo evidence.
3. Refresh this skill with `py -3 scripts/python/update_workflow_chapter_skills.py <repo>` when `workflow.md` changes.

## Idempotent Procedure

1. Resolve the target business repo as a sibling of the template repo.
2. Clean copied template names, paths, workflow names, release names, project paths, and PRD ids.
3. Rebuild entry indexes in README.md, AGENTS.md, docs/PROJECT_DOCUMENTATION_INDEX.md, and docs/agents/00-index.md.
4. Run repository-level hard checks immediately after cleanup and index repair.
5. Optionally start the local project-health service when browser-based health inspection is useful; keep it bound to 127.0.0.1.
6. Use OpenAI backend bootstrap only when the repo explicitly opts into openai-api transport, and keep it out of default CI until checklist self-checks are clean.

## Stop-Loss Signals

- Existing `forbidden_commands` blocks the command about to be run.
- `artifact_integrity`, `planned_only_incomplete`, or planned-only run type appears in recovery evidence.
- Route evidence recommends inspect-first, record-residual, fix-deterministic, repo-noise-stop, or pause.
- The same deterministic failure fingerprint appears repeatedly.
- The next action would duplicate work already covered by task, overlay, candidate, or manifest evidence.

## Business Evidence References

Generated evidence lives under `references/business-repos/` and may include:

- `references/business-repos/sanguo.md`
- `references/business-repos/newrouge.md`

## Maintenance

Refresh evidence after new business-repo logs are generated:

```powershell
py -3 scripts/python/update_workflow_chapter_skills.py sanguo
py -3 scripts/python/update_workflow_chapter_skills.py newrouge
```
