# Knowledge Context Decision And Freeze Contract

This workflow converts a shadow candidate bundle into a **bounded, explicit, source-verified context revision**.

It is not E2 security isolation. It is a repository workflow contract that prevents silent context expansion after a consumer has chosen its authority set.

## Preconditions

1. Run the normal direct-source workflow preflight first.
2. Produce a `newrouge.knowledge-context-candidates.v1` shadow bundle with `prepare_knowledge_context.py`.
3. Re-read candidate source files directly.
4. Record explicit semantic decisions. Ranking alone never counts as acceptance.

## Decision Set

A decision set uses `newrouge.knowledge-consumption-decision-set.v1` and binds:

- `consumer`
- `request_id`
- `source_bundle_sha256`: canonical SHA-256 of the exact shadow bundle
- one or more `newrouge.knowledge-consumption-decision.v1` records

For every decision:

- `candidate.module_id` and `candidate.path` must identify a candidate in the bound bundle;
- `source_sha256` must equal the candidate source hash;
- `decision` is `accepted` or `rejected`;
- `reason` records bounded semantic-fit reasoning;
- `satisfies` contains only context classes allowed by the consumer policy.

Rejected candidates MUST use an empty `satisfies` list. They cannot satisfy completeness.

## Freeze

Run:

```powershell
py -3 scripts/python/freeze_knowledge_context.py `
  --bundle logs/ci/knowledge-context/chapter6-task-<task-id>.json `
  --decisions logs/ci/knowledge-context/chapter6-task-<task-id>.decisions.json `
  --output logs/ci/knowledge-context/chapter6-task-<task-id>.frozen.json `
  --task-id <task-id>
```

Chapter 4, Chapter 5, and Chapter 6 freezes are task-scoped and require an explicit `--task-id`. Omit `--task-id` when freezing a Review context; the freeze implementation always records `task_id: null` for that consumer. The Review pipeline itself still takes the business task identifier.

The freeze operation fails closed unless all of the following hold:

- the source bundle is `shadow_ready` and still `unfrozen`;
- the decision set is bound to the exact bundle hash;
- the trusted Git ref still resolves to the bundle snapshot commit;
- every decided source can be re-read from the snapshot commit;
- every re-read source SHA-256 matches the decision/candidate binding;
- accepted context classes are policy-allowed;
- every required context class is covered by accepted candidates.

The resulting `newrouge.knowledge-frozen-context.v1` binds the exact accepted sources, source hashes, policy revision, snapshot, freeze point, decision-set hash, and deterministic `context_id`.

## Chapter 6 Rule

A Chapter 6 frozen context is created before RED.

Once a RED/GREEN/REFACTOR sequence starts, do not issue a new semantic Locator query or silently append sources to the frozen context. If task scope changes materially, stop the sequence and create a new explicit candidate/decision/freeze revision.

## Chapter 6 To Review Handoff

When the Chapter 6 orchestrator receives a validated Chapter 6 frozen context, impact report and revision, it stops before launching Review with exit code 1, `status = blocked` and `stop_reason = review_context_required`. This applies to both the normal Review step and the approved fork path. Its `summary.json` retains completed steps and identifies `pending_step` and `next_action`. This is an explicit handoff pause, not a failed Review verdict.

Continue separately:

1. Select the revision to review after coding. Prepare a new `consumer=review` candidate bundle using the applicable current publication, re-read sources, and record explicit Review semantic decisions.
2. Freeze that Review bundle without `--task-id` and generate an Impact Report bound to its exact frozen hash and revision. Rebuild the Impact Index when its revision or identity inputs have changed.
3. Invoke `scripts/sc/run_review_pipeline.py` directly with the business `--task-id`, the Review `--frozen-context`, `--impact-report` and matching `--revision`. Supply `--binding-evidence` when using the corresponding Review sidecar. Existing review prerequisites still apply.

Do not restart the Chapter 6 orchestrator with Review artifacts: its entry validator requires `consumer=chapter6`. Do not edit the consumer field of old artifacts or omit the handoff to bypass the pause. Review resume/fork requires matching Review handoff identity; a changed identity requires a new Review run. An orchestrator fork pause does not authorize reuse of Chapter 6 artifacts in an existing Review run.

## Evidence Boundary

Files under `logs/ci/knowledge-context/**` remain derived evidence. They do not become PRD/GDD/ADR/Overlay/Contract/Taskmaster authority.

The existing review harness sidecar protocol is unchanged during this migration stage. Do not inject frozen-context fields into `summary.json`, `execution-context.json`, or `latest.json` until a later explicit integration requirement updates those contracts and tests.
