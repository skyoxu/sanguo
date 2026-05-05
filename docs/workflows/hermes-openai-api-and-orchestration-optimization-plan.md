# Hermes / OpenAI API / Chapter 5-6 Orchestration Optimization Plan

## Purpose

This document captures the next optimization batch inspired by Hermes Agent design ideas and by the current Chapter 5 / Chapter 6 workflow pain points in this template repository.

The goal is not to copy Hermes Agent as a platform. The goal is to selectively absorb the parts that improve this repository's core use case:
- Windows-only Godot + C# business repos
- arc42-driven AI-led delivery
- local harness first, future cloud control-plane second
- deterministic recovery and stop-loss before more LLM spend

## Current implementation status (2026-04-12)

- Step 1 done: Chapter 6 top-level route contract now hard-blocks `inspect-first`, `record-residual`, `repo-noise-stop`, `fix-deterministic`, `artifact_integrity`, `planned-only`, and `forbidden_commands` before expensive downstream work.
- Step 2 done: plan-time and runtime-time behavior now share one orchestration decision object in `scripts/python/run_single_task_chapter6_lane.py`.
- Step 3 done: no-increment convergence now stops reviewer-only reopen attempts when `run_event_summary` shows multi-turn retries without new reviewer / sidecar / approval movement.
- Step 4 done for the main loop risk: approval contract is enforced by the Chapter 6 orchestrator, `approval_denied` no longer incorrectly blocks same-run resume, and producer-side `explicit_fork` runs no longer generate a fresh pending approval request inside the forked run.
- Step 5 done: regression coverage now includes route hard-stop enforcement, `forbidden_commands`, no-increment convergence, approval pending / denied behavior, explicit-fork approval loop prevention, Chapter 6 marathon regression isolation, and the new Chapter 5 light-lane route-contract cases.
- Step 6 done: `scripts/python/run_single_task_light_lane.py` and `scripts/python/run_single_task_light_lane_batch.py` now emit the Chapter 5 route-contract block in both self-check and real summaries, including `preferred_lane`, `recommended_action`, `recommended_command`, `forbidden_commands`, `latest_reason`, `recommended_action_why`, `blocked_by`, `artifact_integrity`, and `residual_recording`. They now classify timeout backoff, retry-soft-steps-only, inspect-first preflight gaps, extract-only reruns, merge-validation integrity failures, and split-batch stop-loss cases into stable route-contract outputs, while batch recommendations use batch-aware rerun commands instead of implying a blind full rerun.
- Step 7 done: `scripts/sc/_llm_backend.py` now serves as the shared internal provider seam across the high-frequency `scripts/sc` LLM families targeted by this plan. Backend dispatch is no longer hard-coded inside `_llm_review_exec.py`; `llm_review` self-check / dry-run expose backend readiness (`codex-cli|openai-api`); `openai-api` now has a runnable Responses API path for the migrated families; and the higher-level entrypoints `scripts/sc/run_review_pipeline.py` plus `scripts/sc/llm_review_needs_fix_fast.py` both pass through `--llm-backend` without bypassing the normal orchestration layer. The semantics family is fully routed through the seam (`llm_extract_task_obligations.py`, `llm_align_acceptance_semantics.py`, `llm_fill_acceptance_refs.py`, `llm_check_subtasks_coverage.py`, `llm_semantic_gate_all.py`), and Batch 3 test generation is now also covered (`llm_generate_tests_from_acceptance_refs.py`, `llm_generate_red_test.py`). Default behavior still stays on `codex-cli`, while overlay / authoring helpers remain CLI-first by design rather than by migration gap.

## What To Absorb From Hermes Agent

### 1. Stable prompt prefix + context compression

Keep system-level reviewer prompts and task orchestration prompts stable.
Move volatile state into sidecars or file references instead of rebuilding giant prompts every run.

Value for this repo:
- better cache hit probability
- lower token waste in 6.7 / 6.8
- fewer rerun drifts caused by prompt shape changes

Recommended local rule:
- freeze reviewer/system prompt prefix per workflow family
- limit variable prompt content to diff, acceptance excerpts, route facts, and structured sidecar fields
- prefer summary sidecars over re-inlining large raw artifacts into prompts

### 2. Separate memory from workflow skill

This repo already has the right raw pieces:
- `logs/ci/**` sidecars for short-lived run state
- `execution-plans/**` for durable intent
- `decision-logs/**` for durable decisions
- `docs/agents/**` and `workflow.md` for procedural workflow knowledge

Recommended rule:
- sidecars = short-lived operational truth
- execution-plan / decision-log = durable task intent and decision record
- docs = reusable procedural knowledge

Future control-plane rule:
- any browser or cloud control plane should recover from these three layers in this order: sidecars first, execution-plan / decision-log second, docs last
- recovery should never depend primarily on transient chat context when durable sidecars and durable markdown records already exist

### 3. Scripted multi-step tool execution

Hermes Agent's most valuable idea for this repo is not the full platform, but the principle that multi-step tool work should happen inside code, and only the final structured result should go back to the model.

Value for this repo:
- less token spent on intermediate tool chatter
- less context pollution
- easier retry classification
- easier long-run recovery

Recommended rule:
- whenever a workflow needs multiple deterministic inspections before one LLM judgment, run those inspections in Python and send only the compact summary to the model

### 4. Control plane / execution plane split

This repo should continue to evolve toward:
- control plane: browser / API / dashboard / recovery / approval / status
- execution plane: Windows worker running public script entrypoints

This means future web or cloud work should call stable public entrypoints, not reimplement the workflow rules inside the control plane.

## OpenAI API Migration Plan

## Current state

Current LLM entrypoints are primarily implemented through `codex exec` launched from Python subprocesses.
This is convenient for local usage, but it creates four cost and reliability problems:
- process startup overhead per run
- coarse timeout handling (`rc=124`, empty output)
- text-first output parsing instead of first-class structured output
- repeated long prompts with limited retry control

## Scripts with highest recurring token spend

### Highest recurring spend

- `scripts/sc/llm_review.py`
- `scripts/sc/llm_review_needs_fix_fast.py`
- `scripts/sc/run_review_pipeline.py` indirectly, because it repeatedly triggers `llm_review.py`
- `scripts/sc/llm_extract_task_obligations.py`
- `scripts/python/run_single_task_light_lane.py`
- `scripts/python/run_single_task_light_lane_batch.py`

Why these are highest:
- multi-agent or multi-round behavior
- long diff and acceptance context
- frequent reruns during 5.1 / 6.7 / 6.8
- repeated timeout and stop-loss handling
- batch or consensus execution patterns

### Medium recurring spend

- `scripts/sc/llm_generate_tests_from_acceptance_refs.py`
- `scripts/sc/llm_align_acceptance_semantics.py`
- `scripts/sc/llm_fill_acceptance_refs.py`
- `scripts/sc/llm_check_subtasks_coverage.py`
- `scripts/sc/llm_semantic_gate_all.py`

### High single-run spend but lower migration priority

- `scripts/sc/llm_generate_overlays_batch.py`
- `scripts/sc/llm_generate_overlays_from_prd.py`

These can be expensive per invocation, but they are less frequent and more one-off than Chapter 5 / Chapter 6 loops.

## Migrate to OpenAI API first

### Batch 1: immediate ROI

- `scripts/sc/llm_review.py`
- `scripts/sc/llm_review_needs_fix_fast.py`
- shared runtime currently in `scripts/sc/_llm_review_exec.py`

Why first:
- highest recurring spend
- highest timeout pain
- strongest need for structured output and targeted retry
- biggest impact on 6.7 / 6.8 cycle time

Expected gains:
- lower timeout rate through per-agent retry and transport-level timeout separation
- lower token cost through stricter structured output and shorter retry prompts
- better reviewer shrink / rerun-failing-only precision

### Batch 2: semantics stabilization family

- `scripts/sc/llm_extract_task_obligations.py`
- `scripts/sc/llm_align_acceptance_semantics.py`
- `scripts/sc/llm_fill_acceptance_refs.py`
- `scripts/sc/llm_check_subtasks_coverage.py`
- `scripts/sc/llm_semantic_gate_all.py`

Why second:
- these workflows are already highly structured
- they benefit from JSON-first responses
- they are often rerun in batches where transport and retry control matters

### Batch 3: test generation

- `scripts/sc/llm_generate_tests_from_acceptance_refs.py`

Why third instead of first:
- valuable, but lower total spend than review + semantics batch pipelines
- test generation still needs careful file-write and verification orchestration regardless of model transport

## Keep CLI first, at least for now

### Better to keep `codex exec` for now

- `scripts/sc/llm_generate_overlays_batch.py`
- `scripts/sc/llm_generate_overlays_from_prd.py`
- one-off prototype authoring helpers
- operator-driven ad-hoc generation flows where human supervision is already strong

Why keep CLI here:
- less frequent
- higher tolerance for manual intervention
- lower ROI from immediate transport migration
- these flows are closer to assisted authoring than to repeatable pipeline gating

## Recommended architecture for migration

Introduce a shared provider abstraction, for example:
- `scripts/sc/_llm_backend.py`
- provider modes: `codex-cli` and `openai-api`

Recommended staged rule:
- default to `codex-cli` first for backward compatibility
- allow `OPENAI_API` mode by env or CLI flag on migrated families
- only flip defaults after schema, retry, and regression coverage are stable

## Token and timeout optimization rules after API migration

- keep stable prompt prefixes per workflow family
- use structured JSON output wherever possible
- send compact route / review / acceptance summaries instead of raw large artifacts
- separate connect timeout, response timeout, and total wall-time budget
- retry only the failing reviewer or failing semantic substep
- preserve fingerprint-based reuse and same-family stop-loss before any model retry

## Chapter 5 should absorb Chapter 6 orchestration ideas

Chapter 5 currently has strong batch and stabilization mechanics, but it should adopt the same top-level orchestration principles already used in Chapter 6.

### What to absorb

- recovery-first entry before paying new LLM cost
- explicit route result before execution
- `preferred_lane` as a contract, not a hint
- `forbidden_commands` as executable stop-loss, not advisory text
- residual recording as a valid terminal lane
- structured route / latest / artifact_integrity checks before any rerun
- route-aware reuse of existing artifacts

### Proposed Chapter 5 top-level orchestration model

For `5.1` and its batch wrappers, add a route layer conceptually equivalent to Chapter 6:
- read latest task or batch summary first
- classify timeout family / repo-noise / deterministic input gap / residual-only case
- decide one lane before execution

Recommended lane examples for Chapter 5:
- `run-5.1`
- `retry-extract-only`
- `retry-soft-steps-only`
- `record-residual`
- `inspect-first`
- `repo-noise-stop`
- `split-batch`
- `timeout-backoff-then-rerun`

### Output alignment target

Chapter 5 summaries should gradually align with Chapter 6 route semantics:
- `recommended_action`
- `recommended_command`
- `forbidden_commands`
- `preferred_lane`
- `blocked_by`
- `artifact_integrity`
- `latest_reason`
- `residual_recording`

Current rollout note:
- `scripts/python/run_single_task_light_lane.py` already emits the core route fields plus `recommended_action_why`.
- `scripts/python/run_single_task_light_lane_batch.py` now emits the same top-level route fields and uses batch-aware rerun commands over failed task ids. Merge-validation failures and rolling stop-loss cutovers now route to `inspect-first` or `split-batch` instead of implying a blind full rerun.

The point is not to make both chapters identical. The point is to make their top-level stop-loss and recovery contracts consistent.

## Chapter 6 top-level orchestration: known issues and fixes

## P0 issues

### 1. Preferred lane is not enforced strongly enough

Problem:
- when route returns `preferred_lane=record-residual` or `preferred_lane=inspect-first`, the top-level orchestrator may still continue into `review-pipeline`
- this means route is treated as a hint, not as an execution contract

Required fix:
- add a single execution gate before every downstream step
- if route lane is not executable for the next step, stop immediately
- `record-residual`, `inspect-first`, `repo-noise-stop`, `fix-deterministic`, and approval-blocked states must be hard stop lanes

### 2. Fork can create approval loop

Problem:
- after fork, a new approval pending may be generated again, creating an approval state-machine loop

Required fix:
- make approval transitions idempotent per recovery intent
- if a matching approval contract is already resolved, reuse it instead of creating a new pending request
- bind approval state to the recovery decision object, not to ad-hoc step sequencing

### 3. No-increment reruns do not stop early enough

Problem:
- after multiple resumes with no new reviewer evidence, the orchestrator does not automatically converge to residual recording or inspect-first

Required fix:
- detect no-increment convergence using `run-events.jsonl`, `agent-review.json`, and reviewer deltas
- if no new reviewer or sidecar movement is observed across configured turns, stop and downgrade to `record-residual` or `inspect-first`

## P1 issues

### 4. `artifact_integrity` and `planned-only` can still be mis-released

Problem:
- `blocked_by=artifact_integrity`
- `latest_reason=planned_only_incomplete`
- `run_type=planned-only`

These states are protocol-level stop-loss conditions and must never fall back into the full path.

Required fix:
- promote these checks into the top-level execution gate
- treat them the same way as route-level hard stops
- if present, allow only inspection or recovery from an earlier real producer bundle

### 5. `forbidden_commands` is not enforced generically before execution

Problem:
- execution still depends mostly on inferred route logic instead of a direct command-vs-protocol check
- future protocol evolution could bypass stop-loss boundaries again

Required fix:
- before running any planned command, compare it against `forbidden_commands`
- if blocked, stop and emit a route-contract violation result
- keep this check generic, not tied only to current lane names

## P2 issues

### 6. `build_execution_plan()` and `main()` duplicate state-machine logic

Problem:
- planning and runtime execution each maintain their own state transitions
- this is drift-prone and hard to evolve safely

Required fix:
- extract one shared orchestration decision layer
- planning should render from the decision object
- runtime should execute from the same decision object

### 7. Decision model is fragmented

Problem:
- approval helpers, route helpers, resume helpers, and ad-hoc step logic are still combined procedurally

Required fix:
- introduce one unified decision object, for example in a dedicated module such as `scripts/python/_chapter6_decision.py`
- recommended fields:
  - `preferred_lane`
  - `blocked_by`
  - `allowed_actions`
  - `forbidden_commands`
  - `approval_state`
  - `artifact_integrity_state`
  - `residual_policy`
  - `next_step`
  - `stop_reason`

### 8. Self-check coverage is still too weak

Problem:
- current self-check validates plan shape, but not enough realistic recovery combinations

Required fix:
- add realistic self-check and regression cases for:
  - `artifact_integrity`
  - `planned_only_incomplete`
  - `forbidden_commands`
  - approval pending / approved / denied / invalid transitions
  - no-increment rerun convergence
  - route hard-stop enforcement before `review-pipeline`

## Recommended implementation order

### Step 1

Introduce a single `enforce_route_contract()` gate in the top-level Chapter 6 orchestrator.
This gate should run before any expensive downstream step.

It should stop on:
- `preferred_lane=record-residual`
- `preferred_lane=inspect-first`
- `preferred_lane=repo-noise-stop`
- `preferred_lane=fix-deterministic`
- `blocked_by=artifact_integrity`
- `latest_reason=planned_only_incomplete`
- `run_type=planned-only`
- any command explicitly present in `forbidden_commands`
- approval states that do not allow the requested action

### Step 2

Unify plan-time and runtime-time decision logic around one shared decision object.

### Step 3

Add no-increment convergence protection.
Use reviewer delta and sidecar delta, not just generic rerun counts.

### Step 4

Make fork approval transitions idempotent and contract-based.

### Step 5

Expand self-check and regression coverage using realistic recovery fixtures.

## Practical expected result

If this plan is implemented well, this repository should gain:
- lower LLM token waste
- fewer timeout-driven reruns
- stronger route stop-loss correctness
- no approval loop in Chapter 6 orchestration
- more consistent route semantics between Chapter 5 and Chapter 6
- a cleaner future path from local harness to cloud control-plane + Windows worker execution

## Non-goals

These are explicitly not the next-step goal:
- turning this repo into a full Hermes-style multi-channel platform
- adding messaging gateway complexity
- adding remote daemon or JSON-RPC before the execution contracts are stable
- replacing all `codex exec` usage at once

## Short conclusion

The next high-value direction is:
1. stabilize route and stop-loss execution first
2. migrate the highest recurring LLM-cost families to OpenAI API second
3. then make Chapter 5 and Chapter 6 share one top-level orchestration philosophy
