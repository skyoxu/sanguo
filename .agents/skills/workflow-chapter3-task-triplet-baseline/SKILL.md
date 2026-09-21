---
name: workflow-chapter3-task-triplet-baseline
description: Run the fixed Chapter 3 source-ledger, semantic-conservation, task-triplet, and knowledge-refresh workflow from workflow.md. Use when authoritative PRD/GDD inputs must be converted into coarse no-loss tasks without letting one model pass silently drop source semantics.
---

# Workflow Chapter 3 Task Triplet Baseline

## Role

Operate Chapter 3 idempotently for a business repository. Preserve the existing Chapter order and Taskmaster authority while adding deterministic source accounting before task generation.

## Operating Contract

- Treat `workflow.md` as the normative workflow source.
- Treat original PRD/GDD/planning files as semantic authority. Source Block, Semantic Requirement, Capability, topology, and Knowledge are derived projections.
- Use Python with UTF-8 for documentation reads and writes.
- Do not let an LLM write final `.taskmaster/tasks/tasks.json` directly.
- Do not use one prompt/context window as proof that a large GDD was read completely.
- Do not reopen engine, architecture, or technology-stack selection.
- Capability is optional grouping only and has no Taskmaster status.
- Chapter 3 dependencies are provisional skeletons; Chapter 5 must validate or correct them.
- Do not rerun expensive steps before reading existing recovery artifacts.

## Purpose

Produce a coarse but semantically conservative task triplet. The invariant is:

    authoritative sources -> complete Source Block Ledger -> Semantic Projection A -> conservation gate -> optional Capability -> coarse Task skeleton -> closure gate -> Workspace attempt/stable topology

Every source block must be accounted for. Every active delivery Requirement must end at a Task or an explicit governed non-Task sink.

## Required Reading

1. Read the Chapter 3 section in `workflow.md`.
2. Read `docs/planning/semantic-topology/README.md` and ADR-0038.
3. Read `.agents/skills/maintain-knowledge-base/SKILL.md` before any refresh/publication action.
4. Optional business-repo reference files are regression evidence only and never define generation rules.

## Idempotent Procedure

1. Resolve `init` versus `add` and allocate a `trigger_run_id`. Interactive/multi-turn runs must immediately record the run-start attempt with `py -3 scripts/python/dev_cli.py refresh-knowledge --source chapter3 --trigger-run-id <run-id> --begin-run`. Scripted top-level automation must instead wrap its complete child workflow with `py -3 scripts/python/dev_cli.py run-chapter3-guarded --trigger-run-id <run-id> --triplet-status-on-success <passed|blocked|unknown> -- <command...>`; that guard records the start attempt and executes the final refresh even when the child command fails.
2. Build the complete Source Block Ledger with `py -3 scripts/python/build_source_ledger.py --mode <init|add> ...`. This step inventories all supported source blocks before semantic filtering.
3. Build the compatibility anchor index from that ledger with `py -3 scripts/python/extract_requirement_anchors.py --mode <init|add> --ledger-input logs/ci/task-generation/source-blocks.v1.json`. The compatibility index is downstream evidence only.
4. Prepare deterministic semantic batches with `py -3 scripts/python/project_semantics_from_sources.py prepare`. Batches are bounded by both block count and `--max-chars-per-batch`; a single oversized Source Block fails instead of being truncated. The batch index must cover every Source Block exactly once as primary ownership.
   - In `add` mode, a prior candidate may be reused only for ledger `unchanged` blocks whose `content_hash` still matches and whose prior result was fully reviewed. Cross-block atoms are reusable only when every referenced Source Block is unchanged. Changed/added blocks remain `review_required`; removed blocks and stale capabilities are not carried forward.
5. The approved Chapter 3 model/Skill reads **every batch file** and fills `semantic-projection.candidate.json`. The template intentionally starts with blank disposition, `delivery_potential=null`, and `output_accounted_count=0`; these are not defaults the model may leave untouched. For every owned Source Block, explicitly set delivery potential and emit one or more semantic atoms or exactly one explicit disposition, then reconcile the batch output count. Never delete a `block_result` to make a batch pass.
6. Compile Projection A with `py -3 scripts/python/project_semantics_from_sources.py compile`.
7. Run `py -3 scripts/python/validate_semantic_conservation.py --stage projection`. Stop on unaccounted source blocks, source hash drift, invalid semantic refs, or unresolved delivery-potential blocks without an explicit owner decision and rationale.
8. Normalize coarse task intents from validated semantics with `py -3 scripts/python/normalize_task_intents.py --mode <init|add>`, then run `audit_task_intents_quality.py`.
9. Generate and enrich candidates. Enrichment may add implementation-file and overlap/file-churn advisory signals; these signals never mechanically force a merge.
10. Audit semantic sink coverage with `audit_task_candidate_coverage.py`. The old P0/P1 positive-filter view remains only a downstream packaging check bridged by Source Block IDs.
    - Existing task-view entries that already carry `semantic_refs` are part of add-mode reconciliation. A ref to a removed/replaced Requirement blocks closure unless this run updates the same Task ID with valid current refs.
11. Run `validate_semantic_conservation.py --stage closure`. Active delivery Requirements without a Task/non-Task sink, invalid Task semantic refs, or Task complexity above 7 block closure.
12. Compile a task-triplet patch. Review before `--write`. Build `tasks.json` from the two reviewable task views and run the existing triplet validators unchanged.
13. Backfill semantic review tier conservatively, then run `py -3 scripts/python/attest_chapter3_triplet_baseline.py`. This reruns the Chapter 3 triplet validators and writes a task-file-hash-bound attestation; a caller-provided `--triplet-status passed` is not sufficient by itself.
14. At the end of **every** Chapter 3 run, call `py -3 scripts/python/dev_cli.py refresh-knowledge --source chapter3 --trigger-run-id <run-id> --refresh-local --triplet-status <passed|blocked|unknown>`. Failed/partial runs update only Last Attempt. A passed run advances Latest Successful only when semantic closure, task coverage, and the bound triplet attestation all verify.
    - A blocked/unknown closure always defers `--publish-if-eligible` with `closure_not_passed`; canonical publication is never attempted before closure PASS.
15. Only after closure PASS may `--write-planning-artifacts` promote the stable topology files under `docs/planning/semantic-topology/`. `--publish-if-eligible` remains trusted-ref/main-only and is normally deferred until the artifacts are committed.

## Semantic Projection A Contract

- Allowed semantic kinds: FR/functional, NFR/non_functional, INV/invariant, FAIL/failure, SCOPE/scope, METRIC/metric, CONSTRAINT/constraint, RISK/risk, CONTEXT/context, RATIONALE/rationale.
- Allowed dispositions: atomized, context, rationale, duplicate, superseded, deferred, out_of_scope, adr_owned, unresolved.
- `unresolved` is visible uncertainty, not permission to drop a block. If the block is delivery-potential, stable closure requires an explicit owner decision, reason, and resolved disposition.
- A Requirement may sink through Capability -> Task, directly to Task, to multiple Tasks, or to a global constraint / quality gate / ADR-owned sink. Do not fabricate Capability nodes.
- Batch counters are deterministic: first/last block id, input block count, input character budget, and accounted output count must reconcile before moving on.
- Batch files carry bounded `context_before` / `context_after` neighbor blocks when budget permits. These are read-only context: primary ownership and output accounting remain only on `block_ids`.
- Projection compile deterministically merges exact normalized duplicate atoms across blocks. Semantically equivalent paraphrases may share one explicit `requirement_id`; the merged Requirement preserves the union of all `source_block_ids` and source edges. It never performs fuzzy similarity guessing.
- `requirement_like_hint` is diagnostic only. It must never pre-classify an untouched block as non-delivery; every block requires explicit model/Skill review.

## Task Generation Rules

- Tasks remain intentionally coarse in Chapter 3. Chapter 5 owns the second semantic stabilization pass.
- Complexity greater than 7/10 must be split into Tasks; if semantic cohesion prevents further Task splitting, use Subtasks under the existing governance.
- The normalizer splits semantic groups before an intent can exceed 7. It must not cap an oversized score to hide the split requirement; semantic refs across the split remain collectively equivalent.
- `depends_on` emitted here is provisional. Same owner/layer or generation adjacency is not semantic proof of dependency.
- Preserve `semantic_refs`, every applicable `capability_refs`, source refs, and complexity metadata into the task views.
- When Capability is absent, group semantic anchors by source heading before source-path fallback. CJK headings/statements may provide the deterministic Task focus/title; do not reintroduce keyword-based semantic filtering.
- Shared multi-Capability signatures emit advisory joint-grouping shadow evidence only. They must not change the default Task partition until separately promoted by policy/regression evidence.
- `implementation_overlap_candidates` and `file_churn_signal` are advisory task-boundary quality evidence only.

## Knowledge / Project Health Closure

- Workspace Last Attempt is refreshed for every registered Chapter 3 run when `--refresh-local` is used.
- Workspace Latest Successful advances only when semantic conservation and the triplet baseline both pass.
- A failed attempt must never overwrite Latest Successful.
- Local topology write failures are an independent `knowledge_refresh_failed` family. `attempt_refresh_failed`, `stable_refresh_failed`, and planning-topology refresh failures are retryable concerns; a stable refresh failure blocks Chapter 3 completion and canonical publication even when semantic/triplet gates already passed.
- Main topology remains committed/trusted-ref state. Workspace topology never advances KCP current/LKG.
- Project Health exposes Workspace `attempt` and `stable` views separately.
- Recovery, Chapter 6, Review, or ordinary consumers must not invoke publication as an implicit repair.

## Stop-Loss Signals

- A declared authoritative source path does not resolve.
- Source ledger block accounting is incomplete.
- A semantic batch is missing a block result or ownership counters do not reconcile.
- Source hash drift appears after projection.
- Delivery-potential unresolved semantics remain without explicit decision/rationale.
- Active delivery Requirement has no explainable sink.
- Task semantic refs point to missing/superseded Requirements.
- Complexity exceeds 7 without split/subtask disposition.
- Triplet baseline validators fail.
- The same deterministic failure fingerprint repeats.

## 用户交互文案要求

- Chapter 3 面向用户的说明、分步确认与阻断提示使用中文。
- 对大 GDD 的模型分析必须按 ledger batch 逐批完成；不得因为单轮上下文结束就把“未读取后续块”当作分析完成。
- 任务文件与文档中若写入中文，必须通过 Python 并显式 UTF-8 写入。

## Regression Evidence

`run_chapter3_regression_check.py` is read-only regression evidence. It reports separate source / semantic / task layers plus the legacy/mature-task shadow comparison. Without a reviewed semantic artifact, the semantic layer must say `not_run`; it must not infer semantics from legacy positive-filter anchors. Use `--semantic-requirements <path>` when reviewed semantics are available. Do not tune production rules to mimic mature Chapter 4/5/6/7 history.

## Maintenance

Refresh optional business evidence with `py -3 scripts/python/update_workflow_chapter_skills.py <repo>` only after production rules above are updated in the template source.
