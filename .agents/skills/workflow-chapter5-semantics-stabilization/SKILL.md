---
name: workflow-chapter5-semantics-stabilization
description: Run the fixed Chapter 5 semantic reconciliation workflow from workflow.md. Use when a business repo needs Independent Extraction B, global orphan/omission audit, bidirectional Requirement/Acceptance validation, dependency/overlap stabilization, readiness gating, Knowledge refresh, or the legacy lightweight acceptance lane before Chapter 6.
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
- During Knowledge Control Plane migration, Locator candidates are shadow-only. Complete source scope comes from the authoritative manifest/Ledger A, never task refs.
- Chapter 5 is a registered closure producer: every run may update Last Attempt, but only READY or policy-allowed CONCERNS may advance Latest Stabilized.

## Repository Layout

Template and business repositories are siblings under one parent directory, for example `<parent>/godotgame`, `<parent>/<business-repo-a>`, and `<parent>/<business-repo-b>`.

## Purpose

Use this skill to stabilize task semantics before daily task execution enters the Chapter 6 loop.

## Default Lane

Build or reuse one revision-bound Independent Extraction B snapshot from the complete authoritative source scope, then reconcile only the target Task against that global inventory. Keep the existing lightweight lane for acceptance authoring; batch escalation remains conditional.

## Primary Command Or Action

`py -3 scripts/python/chapter5_semantic_reconciliation.py prepare && <independent review of every block> && py -3 scripts/python/chapter5_semantic_reconciliation.py compile && py -3 scripts/python/chapter5_semantic_reconciliation.py reconcile --task-id <id> --decisions <decisions.json>`

The audit scope comes from the Chapter 3 source manifest and Source Block Ledger, never from `task.semantic_refs` or `capability_refs`.

## Evidence Rule

Chapter 5 evidence is usually sparse, so workflow.md remains the governing source and logs only tune failure-family recognition.

A `logs/ci/knowledge-context/**` bundle is optional shadow routing evidence only. It cannot replace acceptance refs, task triplets, overlays, or direct source authority.

## Required Reading

1. Read the relevant Chapter 5 section in the template repo `workflow.md`.
2. Read `docs/workflows/knowledge-context-shadow.md` before using the optional Chapter 5 knowledge preflight.
3. Optionally read `references/business-repos/<repo>.md` only as empirical validation evidence when the target business repo has a generated reference.
4. If that optional evidence file is missing or stale, run `py -3 scripts/python/update_workflow_chapter_skills.py <repo>` from the template repo.

## Idempotent Procedure

1. Resolve the target business repo, allocate a `trigger_run_id`, and immediately record `py -3 scripts/python/dev_cli.py refresh-knowledge --source chapter5 --trigger-run-id <run-id> --begin-run`. Scripted automation must wrap its child workflow with `py -3 scripts/python/dev_cli.py run-chapter5-guarded --trigger-run-id <run-id> -- <command...>` so both start and final Attempt refresh are guaranteed. Then verify Chapter 3 source manifest/Ledger A plus Chapter 4 overlay/contract backlinks.
2. Run `chapter5_semantic_reconciliation.py prepare`. A cache hit is reusable only when `source_manifest_sha`, `source_block_ledger_sha`, `parser_revision`, and `extractor_revision` match exactly.
3. Independently review every candidate `raw_source`; fill `delivery_potential`, obligations, or a valid disposition. Do not consult Task mappings to decide which blocks to omit.
4. Run `chapter5_semantic_reconciliation.py compile`; an incomplete source scope or unreviewed block is blocking.
5. Before task-local acceptance work, run `reconcile --task-id <id>` so global `missing_in_ch3` / `orphan_delivery_semantic` findings are visible even when no Task references the source semantic. Lexical similarity is diagnostic only: every semantic match verdict must be explicit and include rationale; otherwise readiness is BLOCKED.
6. Use the existing lightweight lane to stabilize acceptance. Then provide `acceptance_links` that bind each Acceptance to Requirement/ADR/Contract authority and test refs, plus explicit `authority_decisions` for every relevant ADR/Contract (`compatible | conflict | out_of_scope` with rationale), and rerun reconciliation.
7. Resolve provisional dependencies with explicit relation/reason/evidence and record each overlap candidate as `keep_separate`, `merge_recommended`, or `overlap_justified` with rationale.
8. Apply task corrections only when readiness is closable. `BLOCKED` must not enter Chapter 6; `CONCERNS` needs explicit policy allowance.
9. End every interactive Chapter 5 run with `py -3 scripts/python/dev_cli.py refresh-knowledge --source chapter5 --trigger-run-id <run-id> --refresh-local --reconciliation <path> --readiness <path>`. Guarded scripted runs do this automatically. The refresh revalidates the same full input fingerprint (source, semantic requirements, Task/Acceptance/dependency surface, Overlay/Contract/ADR bytes and authority review) before stable promotion.
10. Treat acceptance extraction failure as a stop-and-fix signal and escalate batch instability only when the same failure family repeats.

## Stop-Loss Signals

- Existing `forbidden_commands` blocks the command about to be run.
- `artifact_integrity`, `planned_only_incomplete`, or planned-only run type appears in recovery evidence.
- Route evidence recommends inspect-first, record-residual, fix-deterministic, repo-noise-stop, or pause.
- The same deterministic failure fingerprint appears repeatedly.
- The next action would duplicate work already covered by task, overlay, candidate, or manifest evidence.
- A Locator candidate cannot be re-read/hash-verified from repository authority; reject it and use the direct-source path.
- Extraction B source scope is incomplete, stale, or task-selected; stop before task-local reconciliation.

## Business Evidence References

Generated evidence may live under `references/business-repos/<repo>.md`. These files are optional regression evidence from known business repositories; they must not define production generation rules.

## Maintenance

Refresh optional evidence after new business-repo logs are generated:

```powershell
py -3 scripts/python/update_workflow_chapter_skills.py <business-repo>
py -3 scripts/python/update_workflow_chapter_skills.py <business-repo-a>,<business-repo-b>
```
