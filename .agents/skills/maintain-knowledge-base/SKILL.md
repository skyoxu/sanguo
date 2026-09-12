# Maintain Knowledge Base

Use this skill only to inspect, validate, rebuild, publish, or recover **derived repository knowledge artifacts**.

## Non-negotiable boundaries

- Repository source remains authority.
- Do not edit product/runtime/source documents merely to make the knowledge catalog pass.
- Do not fetch, merge, checkout, reset, or otherwise move repository source authority as an implicit maintenance side effect.
- Default trusted ref is `refs/heads/main`.
- Do not promote dirty worktree content as repository facts.
- Dirty knowledge policy/evaluation/control-plane changes block publication until committed.
- Do not treat `logs/**` as global knowledge truth.
- Do not create ad-hoc replacement indexes when the registered catalog is stale.
- Consumer workflows must not rebuild or publish global knowledge as an implicit recovery side effect.

## Read-only inspection

```powershell
py -3 scripts/python/build_knowledge_catalog.py
```

This reads committed source from the trusted ref and reports source/module counts without writing derived artifacts.

`build_knowledge_catalog.py --write` remains a low-level migration/debug primitive. It does **not** create a valid current publication and must not be used as the normal maintenance publication path.

## Explicit publication

After maintainer review:

```powershell
py -3 scripts/python/publish_knowledge_catalog.py --publish
```

Publication:

1. reads source from the trusted ref;
2. builds snapshot/catalog/projections in memory;
3. runs the repository-real deterministic query suite;
4. writes an immutable generation only after validation passes;
5. atomically updates canonical snapshot/catalog/projections;
6. updates `knowledge/indexes/current.json`;
7. advances `knowledge/indexes/last-known-good.json` only after the validated generation exists.

A failed candidate publication must not advance `current` or LKG.

## Publication check

```powershell
py -3 scripts/python/publish_knowledge_catalog.py --check
```

This verifies:

- current pointer -> generation manifest binding;
- generation artifact hashes;
- canonical snapshot/catalog/projection equality with the generation;
- trusted ref still points at the generation source commit;
- published evaluation status is passed.

## Last Known Good recovery

If canonical generated files are damaged or partially replaced:

```powershell
py -3 scripts/python/publish_knowledge_catalog.py --restore-lkg
```

This restores canonical snapshot/catalog/projections and `current.json` from the immutable LKG generation. It does not move Git source authority. If the trusted ref has since advanced, consumers may still fail freshness and must use direct-source fallback until a new generation is successfully published.

## Locator smoke check

After a valid publication, submit a request bound to the published trusted commit:

```powershell
Get-Content request.json | py -3 scripts/python/knowledge_locator.py
```

The canonical Locator requires a valid `current.json` publication. A stale snapshot, policy mismatch, projection mismatch, missing source, source hash drift, or publication binding failure returns `status=blocked`.

## Consumer rule

Locator candidates are not semantic truth. A trusted consumer must re-read the source, verify the source hash, and record an `accepted` or `rejected` decision using `knowledge-consumption-decision.v1` semantics before claiming a required context class is satisfied.

## Terminal validation

```powershell
py -3 scripts/python/validate_knowledge_control_plane.py
py -3 scripts/python/validate_knowledge_control_plane.py --require-generated
```

The generated-state form requires a valid current publication, current generated layers, and the repository query evaluation.

## Rollback

The migration has no game runtime dependency. If the knowledge system is unavailable, use the repository's existing direct authority routing from `AGENTS.md`, `docs/PROJECT_DOCUMENTATION_INDEX.md`, and `docs/agents/13-rag-sources-and-session-ssot.md`.
