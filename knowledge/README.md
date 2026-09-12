# newrouge Repository Knowledge Control Plane

This directory contains **derived repository knowledge infrastructure**. It does not replace repository source authority.

## Authority

Repository facts remain owned by their source files, including `AGENTS.md`, `workflow.md`, Taskmaster, PRD/GDD, ADR/Base/Overlay, `Game.Core/Contracts/**`, workflow documents, execution plans, and decision logs.

The Knowledge Control Plane only answers: **where should a trusted consumer read?**

## Layers

1. `knowledge/snapshots/repository-source-snapshot.v1.json`
   - Trusted-ref source inventory and SHA-256 bindings.
2. `knowledge/catalogs/repository-knowledge-catalog.v1.json`
   - Typed modules, domains, status, visibility, anchors, relations and source hashes.
3. `knowledge/projections/consumer-projections.v1.json`
   - Precomputed eligible module ids per consumer policy.
4. `knowledge/policies/**`
   - Source exclusions and consumer retrieval boundaries.
5. `knowledge/contracts/**`
   - Stable request/result/decision/freeze/publication contracts.
6. `knowledge/evaluation/queries.v1.json`
   - Repository-real deterministic query suite.
7. `knowledge/indexes/generations/<generation-id>/**`
   - Immutable validated publication envelopes.
8. `knowledge/indexes/current.json`
   - Logical current generation pointer.
9. `knowledge/indexes/last-known-good.json`
   - Last validated recoverable generation pointer.

Snapshot, catalog, projection, generation and pointer files are derived artifacts and MUST NOT become a second SSoT.

## Initial domains

- `toolchain`
- `game-design`
- `game-runtime`
- `delivery`

Domain, visibility, lifecycle and enforcement level are independent dimensions.

## Source Coverage

The initial catalog intentionally focuses on authority-bearing knowledge, including:

- `AGENTS.md`, `README.md`, `workflow.md`, `DELIVERY_PROFILE.md`
- `docs/agents/**`
- PRD/GDD/game-design docs
- ADR index, ADRs, Base and Overlay architecture
- `Game.Core/Contracts/**`
- Taskmaster task state
- execution plans and decision logs
- stable workflow/testing documentation

It is not a replacement for code search across `Game.Core/**`, `Game.Godot/**`, `Scenes/**`, or assets.

## Read-only Build Inspection

From a repository with a local `refs/heads/main`:

```powershell
py -3 scripts/python/build_knowledge_catalog.py
```

This computes the expected trusted-ref snapshot/catalog/projections without publishing them.

`build_knowledge_catalog.py --write` exists only as a low-level migration/debug primitive. Canonical consumers do not trust manually written layers unless a valid `current.json` publication binds them.

## Publish

Normal maintenance publication is:

```powershell
py -3 scripts/python/publish_knowledge_catalog.py --publish
```

A publication performs these steps:

1. read source bytes from the trusted Git ref (`refs/heads/main` by default);
2. build snapshot/catalog/projections in memory;
3. run the repository-real deterministic query suite before promotion;
4. create an immutable generation containing snapshot, catalog, projections, policies, exclusions and evaluation report;
5. verify generation artifact hashes;
6. atomically replace canonical snapshot/catalog/projections;
7. update `knowledge/indexes/current.json`;
8. advance `knowledge/indexes/last-known-good.json` only after the validated generation exists.

A failed candidate publication must not advance current or LKG.

Knowledge policy/evaluation/control-plane files must be clean before publication. Unrelated game worktree dirt is not promoted because repository facts are always read from the trusted ref.

## Publication Check and Recovery

Check the current publication:

```powershell
py -3 scripts/python/publish_knowledge_catalog.py --check
```

Restore canonical generated layers from LKG:

```powershell
py -3 scripts/python/publish_knowledge_catalog.py --restore-lkg
```

LKG recovery does not move Git source authority. If `refs/heads/main` advanced after the LKG generation, freshness can still fail and consumers must fall back to direct authoritative source reading until a new publication succeeds.

## Locate

The Locator reads JSON from stdin and emits one JSON result to stdout.

It is location-only: candidates contain source path, anchor/line, SHA-256, provenance and rank evidence. Consumers must re-read the source and own semantic acceptance/rejection.

Example request shape:

```json
{
  "schema_version": "newrouge.knowledge-locator-request.v1",
  "request_id": "example-1",
  "consumer": "chapter6",
  "query": "task contract refs overlay",
  "snapshot": {"ref": "refs/heads/main", "commit": "<40-char-commit>"},
  "policy_revision": "newrouge-knowledge-consumer-policies.v1"
}
```

Run:

```powershell
Get-Content request.json | py -3 scripts/python/knowledge_locator.py
```

For canonical inputs, the Locator requires a valid `current.json` publication and fails closed with `status=blocked` when publication, snapshot, policy, projection, trusted-ref, or source-hash bindings are stale.

## Shadow Consumer Context

Chapter 4/5/6 and review integration is currently observe-only. See:

- `docs/workflows/knowledge-context-shadow.md`
- `docs/workflows/knowledge-context-freeze.md`

Shadow candidate bundles do not satisfy requirements by themselves. A trusted consumer must re-read candidates, verify hashes, record accepted/rejected semantic decisions, and only then may create a bounded frozen context.

Chapter 6 must not silently issue a new semantic query during RED/GREEN/REFACTOR after its context is frozen.

## Evaluation

After a valid publication:

```powershell
py -3 scripts/python/evaluate_knowledge_queries.py
```

The evaluation suite covers repository rules, workflow authority, ADR navigation, contract authority, delivery/task context and review routing while asserting that transient log/migration/backup paths do not satisfy global knowledge queries.

Publication runs the same repository-real suite in memory before promotion, so a failing candidate query suite cannot replace current/LKG.

## Terminal Validation

Kernel/static validation:

```powershell
py -3 scripts/python/validate_knowledge_control_plane.py
```

Full generated-state validation:

```powershell
py -3 scripts/python/validate_knowledge_control_plane.py --require-generated
```

The full form requires:

- a valid current publication;
- generated layers matching current trusted `refs/heads/main`;
- deterministic kernel, freeze and publication unit tests;
- repository-real query evaluation.

## Exclusions

Global semantic knowledge excludes transient or recursively-derived state such as:

- `logs/**`
- `backup/**`
- `docs/migration/**`
- `.godot/**`
- build output
- generated knowledge snapshots/catalogs/projections/indexes

Run/recovery evidence remains available through its existing explicit workflow consumers; it is not promoted to global repository truth.

## Rollout

The migration remains E1 retrieval-scoped. The current implementation order is:

```text
direct-source baseline
  -> deterministic kernel
  -> repository query evaluation
  -> human routing integration
  -> Chapter/review shadow consumers
  -> bounded freeze contract
  -> immutable publication/current/LKG
  -> controlled consumer enforcement only after evidence
```

A frozen task/session context is a workflow freeze contract, not tenant-safe/runtime E2 isolation.

PhaseA/Hosted Context Gate, HMAC manifests, nonce enforcement, account/project isolation and Ji Mu Yun runtime-specific machinery are intentionally out of scope.
