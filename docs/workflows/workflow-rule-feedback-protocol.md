# Workflow Rule Feedback Protocol

Purpose: define how business repositories should feed workflow 5.1 and Chapter 6 execution evidence back into the template repository.

This file is a stable protocol for rule feedback. It does not record one compare range or one project's temporary findings.

## Scope

This protocol covers two workflow families:

- Workflow 5.1 light-lane orchestration
- Chapter 6 task-level recovery, rerun, closure, and residual-routing orchestration

It exists because the template repository does not generate enough real task traffic by itself. Durable routing and stop-loss rules must therefore be learned in business repositories first, then promoted back into the template only when they prove reusable.

## Feedback Sources

Valid feedback sources:

- real `logs/ci/**` outputs from business repositories
- real `summary.json`, `latest.json`, `execution-context.json`, `repair-guide.json`, `agent-review.json`, and `run-events.jsonl`
- repeated failure signatures observed across normal operator usage
- stable workflow regressions caught by repository tests after a rule change

Invalid feedback sources:

- one-off manual guesses
- project-specific local path conventions
- business-only naming, module, or feature assumptions
- conclusions that were not observed in real run artifacts

## Rule Classes

### Class A: Safe To Promote Directly

Promote directly when the rule is protocol-level and repository-agnostic.

Typical examples:

- new sidecar fields that improve recovery observability
- stable stop-loss ordering
- evidence-only handling for `planned-only` or `artifact_integrity`
- route contract fields such as `preferred_lane`, `recommended_action`, `recommended_command`, `forbidden_commands`
- deterministic early guards that fail fast before expensive LLM spend

### Class B: Promote After Cross-Repo Validation

Promote only after the same pattern is confirmed in at least two business repositories.

Typical examples:

- concrete `repo-noise` token expansions
- concrete `P1 floor` category and `owner_step` entries
- failure-family classification tables for extract / align / semantic stages
- retry timeout boosts
- reviewer timeout heuristics
- route thresholds that decide whether `6.8` is worth paying for

### Class C: Do Not Promote

Keep these in the business repository only.

Typical examples:

- business-specific paths, solution names, or project structure
- one-task or one-feature workaround rules
- domain-specific failure signatures
- reviewer defaults tuned for one codebase only
- task semantics that depend on one product's authoring style

## Feedback Targets

### Workflow 5.1

Feedback into the template is appropriate for:

- failure-family and timeout-family classification logic
- summary aggregation fields
- `recommended_next_action` derivation
- retry eligibility and retry scope
- prompt-budget and truncation observability
- deterministic preflight guards

Do not feed back:

- business-specific task ranges
- one repository's preferred batch size
- repository-local timeout values unless they have cross-repo evidence

### Chapter 6

Feedback into the template is appropriate for:

- `repo-noise-stop` classification
- `run-6.7` vs `run-6.8` worth-paying logic
- residual eligibility rules
- `P1 floor` escalation rules
- approval / forbidden-command stop-loss handling
- no-new-evidence stop-loss handling
- timeout and unknown-reviewer observation fields

Do not feed back:

- one repository's custom reviewer bundle
- business-only delivery-profile overrides
- repository-specific task semantics or acceptance authoring habits

## Required Evidence For Promotion

Every proposed template feedback item should include:

1. Rule name
2. Workflow family: `5.1` or `chapter6`
3. Problem statement
4. Artifact evidence
5. Current waste or failure mode
6. Proposed reusable rule
7. Classification:
   - `safe-to-promote`
   - `needs-cross-repo-validation`
   - `business-only`
8. Cross-repo status:
   - `single-repo`
   - `two-repo-confirmed`
   - `three-plus-repo-confirmed`

Minimum artifact evidence should point to at least one of:

- `summary.json`
- `latest.json`
- `execution-context.json`
- `repair-guide.json`
- `agent-review.json`
- `run-events.jsonl`

## Promotion Decision Rules

Promote into the template only when all of the following are true:

1. The rule is not business-specific.
2. The rule reduces cost, false-green risk, or recovery ambiguity.
3. The rule can be expressed as a reusable contract, constant table, classification helper, or workflow note.
4. The rule does not weaken deterministic quality gates.

Require cross-repo validation when any of the following are true:

- the rule changes numeric thresholds
- the rule adds a new failure-family mapping
- the rule changes residual eligibility
- the rule changes retry behavior
- the rule changes timeout handling

Keep the rule local when any of the following are true:

- it depends on one business repository's file layout
- it depends on one product's task taxonomy
- it is a temporary workaround
- it has not yet survived repeated real runs

## Promotion Surface In The Template

When promoting a rule into the template, prefer the smallest stable surface:

1. classification constants or helper modules
2. producer / consumer code paths
3. regression tests
4. workflow documentation

Typical template targets:

- `scripts/python/run_single_task_light_lane.py`
- `scripts/python/chapter6_route.py`
- `scripts/python/run_single_task_chapter6_lane.py`
- `scripts/sc/run_review_pipeline.py`
- `scripts/sc/llm_review_needs_fix_fast.py`
- workflow-facing tests under `scripts/python/tests/**` or `scripts/sc/tests/**`
- `workflow.md`
- `docs/workflows/stable-public-entrypoints.md`
- `docs/workflows/script-entrypoints-index.md`

## Recommended Feedback Loop

1. Observe a repeated real failure or waste pattern in a business repository.
2. Extract the evidence from stable artifacts.
3. Classify the finding as Class A, B, or C.
4. If Class B, wait for cross-repo confirmation before changing template defaults.
5. Promote the rule into the template with tests and doc updates in the same change set.
6. Keep the business repository aligned with the promoted template rule afterward.

## Relationship To Other Docs

- `docs/workflows/template-upgrade-protocol.md`
  - explains how business repositories upgrade from the template
- `docs/workflows/business-repo-upgrade-guide.md`
  - records one compare-range migration surface
- `workflow.md`
  - defines operator behavior for the current repository

This file answers a different question:

- how real business-repository workflow evidence should be converted into reusable template workflow rules

## Suggested Record Template

For one-rule-per-record workflow feedback, use:

- `docs/workflows/templates/workflow-rule-feedback-template.md`

## Recommended Storage Convention

Store git-tracked workflow feedback records under:

- `decision-logs/workflow-rule-feedback/`

Why this location:

- workflow rule feedback is a durable operating decision, not an ephemeral runtime artifact
- it should stay versioned with the repository
- it should be easy to scan during future template backports and upgrade reviews

Recommended filename pattern:

- `YYYY-MM-DD-<repo>-<workflow-family>-<rule-slug>.md`

Examples:

- `2026-04-19-sanguo-chapter6-p1-floor-acceptance-refs.md`
- `2026-04-19-newrouge-5.1-extract-timeout-retry-boost.md`
