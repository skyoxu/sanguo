# Knowledge Context Shadow Preflight

This workflow is **observe-only**. It does not replace direct repository authority, does not mutate business source, and does not change Chapter 4/5/6/review execution order.

## Purpose

Use `prepare_knowledge_context.py` before a workflow writes or executes expensive work to see which authoritative repository locations the current consumer would receive from the deterministic Knowledge Locator.

The output is a candidate bundle only:

- `mode = shadow`
- `semantic_decision_required = true`
- `freeze_state = unfrozen`

A candidate does not satisfy a requirement, acceptance item, architecture obligation, or task context until a trusted consumer re-reads the source and makes an explicit semantic decision.

`status = shadow_ready` means retrieval completed without a publication/freshness block. It does **not** mean that the bundle is semantically complete enough to freeze. Required context classes are satisfied only by later explicit `accepted` decisions.

## Required-Context Retrieval

A broad workflow query can over-rank one source family. For example, a Chapter 4 query containing `overlay contracts ADR architecture` may rank many runtime/overlay sources while crowding out the PRD that is still required for `product-intent`.

The consumer adapter may therefore use bounded, deterministic class-specific query hints from its consumer policy to supplement the base Locator result. These hints:

- apply only to declared `required_context_classes`;
- preserve explicit scope identifiers such as a PRD id or `task <id>` when present;
- do not lower the global Locator threshold;
- do not auto-accept a candidate;
- attach `retrieval_context_classes` only as retrieval evidence for the later semantic reviewer.

Chapter 4 currently uses this mechanism for `product-intent` and `architecture-authority`. Other consumers stay on their current base-query behavior until their own real pilot proves a class-specific retrieval need.

## Commands

Chapter 4, before overlay/contract writes:

```powershell
py -3 scripts/python/prepare_knowledge_context.py --consumer chapter4 --query "<PRD-ID> overlay contracts ADR architecture" --output logs/ci/knowledge-context/chapter4-<PRD-ID>.json
```

Chapter 5, before semantic stabilization:

```powershell
py -3 scripts/python/prepare_knowledge_context.py --consumer chapter5 --query "task <task-id> acceptance semantic authority overlay refs" --output logs/ci/knowledge-context/chapter5-task-<task-id>.json
```

Chapter 6, after `resume-task` / `chapter6-route` and before RED:

```powershell
py -3 scripts/python/prepare_knowledge_context.py --consumer chapter6 --query "task <task-id> implementation authority contract refs tests overlay decisions" --output logs/ci/knowledge-context/chapter6-task-<task-id>.json
```

Review, before `run_review_pipeline.py`:

```powershell
py -3 scripts/python/prepare_knowledge_context.py --consumer review --query "task <task-id> review scope architecture delivery acceptance" --output logs/ci/knowledge-context/review-task-<task-id>.json
```

## Fallback

Default shadow mode is non-blocking.

When generated knowledge is missing, stale, or blocked, the command returns:

- `status = fallback_required`
- `fallback.required = true`

The workflow then continues using the direct authoritative source routing in `docs/agents/13-rag-sources-and-session-ssot.md`.

`--enforce` exists only for later controlled rollout and validation. Do not add it to Chapter 4/5/6/review defaults during the shadow phase.

## Evidence Boundary

`logs/ci/knowledge-context/**` is optional derived evidence.

It is not global knowledge authority, is not part of the existing review harness sidecar schema, and must not be consumed as a substitute for PRD/GDD/ADR/Overlay/Contracts/Taskmaster source files.

## Chapter 6 Stop Rule

Only prepare/query the Chapter 6 knowledge context before RED.

RED/GREEN/REFACTOR must not silently issue a new semantic Locator query. If the task scope genuinely changes, stop and create a new explicit preflight/context revision rather than widening context invisibly.
