# RAG Sources And Session SSoT

Use this document when recovering context, selecting authoritative sources, or writing overlays.

## Why This Document Exists

The legacy AGENTS file referenced generated indexes such as `architecture_base.index`, `prd_chunks.index`, `shards/flattened-adr.xml`, and `shards/flattened-prd.xml`.

Those files are not guaranteed to exist in this repository. Do not rebuild ad-hoc replacement indexes when one is missing.

`sanguo` now has a repository Knowledge Control Plane for deterministic source location. It is a derived routing layer, not a source of truth.

## Preferred Sources In This Repository

Repository facts remain owned by their source files. Important authority includes:

- `AGENTS.md`
- `workflow.md`
- `docs/PROJECT_DOCUMENTATION_INDEX.md`
- `docs/architecture/base/00-README.md`
- `docs/architecture/ADR_INDEX_GODOT.md`
- `docs/prd/**/*.md`
- `docs/gdd/**`
- `docs/testing-framework.md`
- `.taskmaster/**` when real task data exists
- `execution-plans/**` and `decision-logs/**` for durable intent/decisions

Generated knowledge files under `knowledge/snapshots`, `knowledge/catalogs`, `knowledge/projections`, and `knowledge/indexes` are derived state only.

## Knowledge Control Plane

Use the Knowledge Control Plane when the question is primarily:

> Which authoritative repository locations should this consumer read?

The Locator is location-only. It returns source paths, anchors/lines, SHA-256 bindings, provenance, and rank evidence. It does not answer repository questions on behalf of the source files.

Read-only inspection:

```powershell
py -3 scripts/python/build_knowledge_catalog.py
```

Normal maintainer publication:

```powershell
py -3 scripts/python/publish_knowledge_catalog.py --publish
py -3 scripts/python/publish_knowledge_catalog.py --check
```

`build_knowledge_catalog.py --write` is a low-level migration/debug primitive only. A canonical Locator does not trust manually written generated layers unless `knowledge/indexes/current.json` binds them to a validated immutable publication generation.

LKG recovery:

```powershell
py -3 scripts/python/publish_knowledge_catalog.py --restore-lkg
```

Locator entrypoint:

```powershell
Get-Content request.json | py -3 scripts/python/knowledge_locator.py
```

Terminal validator:

```powershell
py -3 scripts/python/validate_knowledge_control_plane.py
py -3 scripts/python/validate_knowledge_control_plane.py --require-generated
```

If published knowledge is missing, stale, blocked, has a moved trusted ref, or cannot be hash-verified, fall back to the direct authoritative source files listed in this document. Do not guess from stale generated output.

## Publication Boundary

A valid current publication binds:

- trusted source snapshot;
- catalog;
- consumer projections;
- consumer policies;
- source exclusions;
- the repository-real query suite;
- the passed evaluation report.

A failed candidate publication must not advance `current.json` or `last-known-good.json`.

Ordinary consumers must never publish or rebuild global knowledge as a recovery side effect.

## Consumer Rules

- `repository-session`: may query broad repository authority for recovery and context selection.
- `chapter4`: may query product/design/architecture authority before overlay or contract writes.
- `chapter5`: may query bounded semantic/acceptance authority before stabilization.
- `chapter6`: may query bounded task/implementation authority before RED; a frozen context must not silently widen during RED/GREEN/REFACTOR.
- `review`: may query review-scope authority; `logs/**` remain explicit evidence, not global semantic truth.

Consumer semantic fit is owned by the consumer. A ranked Locator candidate does not by itself satisfy a requirement or context class.

## Legacy To Current Mapping

- Old `architecture_base.index`
  - Current direct-source equivalent: `docs/PROJECT_DOCUMENTATION_INDEX.md` + `docs/architecture/base/00-README.md`
  - Deterministic locator equivalent: repository Knowledge Control Plane when a valid publication is current.
- Old `prd_chunks.index` and `shards/flattened-*.xml`
  - Current direct-source equivalent: `docs/prd/**/*.md` and `docs/gdd/**`
  - Do not rebuild flattened files ad hoc.
- Old `tasks/tasks.json`
  - Current equivalent: `.taskmaster/tasks/*.json` when present.

## Session Start Order

1. Read `AGENTS.md`.
2. Read `docs/agents/00-index.md` and `docs/agents/01-session-recovery.md`.
3. Read this document to choose the right source set.
4. Read `README.md` for project-facing startup context.
5. Use the Knowledge Locator when a bounded authority lookup is useful and a valid publication is current.
6. Re-read returned source files directly and verify/consume their content; do not treat Locator output as the fact itself.
7. Read `docs/architecture/base/00-README.md` and `docs/architecture/ADR_INDEX_GODOT.md` before changing architecture, overlays, or contracts.
8. Read `docs/testing-framework.md` before changing tests or gates.

## File Location Quick Reference

- PRD source material: `docs/prd/**/*.md`
- GDD source material: `docs/gdd/**`
- ADRs: `docs/adr/ADR-*.md`
- ADR index: `docs/architecture/ADR_INDEX_GODOT.md`
- Base chapters: `docs/architecture/base/*.md`
- Overlays: `docs/architecture/overlays/<PRD-ID>/08/`
- Contract SSoT: `Game.Core/Contracts/**`
- Taskmaster triplet: `.taskmaster/tasks/*.json`
- Durable plans/decisions: `execution-plans/**`, `decision-logs/**`
- Logs and evidence: `logs/**`

## Logs And Evidence

`logs/**` are not global repository knowledge authority.

For task recovery, review, or Chapter 6 routing, read the explicit task/run artifacts through the existing recovery commands. Recent evidence may determine what happened, but it must not silently override ADR/PRD/contract/workflow authority.

## Overlay And ADR Discipline

- Any code or test change should cite at least one accepted ADR.
- If a change alters thresholds, contracts, security posture, or release policy, add a new ADR or supersede the old one.
- Concrete feature slices belong only in `docs/architecture/overlays/<PRD-ID>/08/`.
- Base chapter 08 remains a template and must not contain project-specific slices.
- For overlay work, use scoped authority; do not blind-scan the entire `docs/` tree.
- Locator candidates are discovery hints. Re-read the source and preserve its original ownership boundary.

## Typical Workflow

- Parse or refresh task data only after the target project has real Taskmaster inputs.
- Refresh/publish knowledge only through `maintain-knowledge-base` / registered deterministic publication scripts; ordinary consumers do not publish knowledge as a recovery side effect.
- Validate link integrity with `py -3 scripts/python/task_links_validate.py`.
- Validate test, acceptance, and CI behavior through `docs/testing-framework.md` and `scripts/sc/README.md`.
- When knowledge infrastructure is unavailable, use direct authoritative source reading rather than creating an unregistered index.

## Old AGENTS Coverage Map

- `0.1 New Session Quick Reference` -> this document
- `1 Context Discipline (RAG Rules)` -> this document + `docs/agents/10-template-customization.md`
