# RAG Sources And Session SSoT

Use this document when recovering context, selecting authoritative sources, or writing overlays.

## Why This Document Exists
The legacy AGENTS file referenced generated indexes such as `architecture_base.index`, `prd_chunks.index`, `shards/flattened-adr.xml`, and `shards/flattened-prd.xml`.
Those files are not guaranteed to exist in this template repository.
If you blindly follow the old text here, you will route work to missing files and lose time.

## Preferred Sources In This Repository
Use these sources first in the current template state:
- `AGENTS.md`
- `docs/PROJECT_DOCUMENTATION_INDEX.md`
- `docs/architecture/base/00-README.md`
- `docs/architecture/ADR_INDEX_GODOT.md`
- `docs/prd/**/*.md`
- `docs/testing-framework.md`
- `.taskmaster/**` only when the copied project has generated task data

## Legacy To Current Mapping
- Old `architecture_base.index`
  - Current equivalent: `docs/PROJECT_DOCUMENTATION_INDEX.md` + `docs/architecture/base/00-README.md`
- Old `prd_chunks.index` and `shards/flattened-*.xml`
  - Current equivalent: `docs/prd/**/*.md`
  - If a copied project later generates shard or index files, those generated artifacts become the preferred scoped sources.
- Old `tasks/tasks.json`
  - Current equivalent: `.taskmaster/tasks/*.json` when present
  - Bare template repositories may not have any generated task triplet yet.

## Session Start Order
1. Read `AGENTS.md`.
2. Read `docs/agents/00-index.md` and `docs/agents/01-session-recovery.md`.
3. Read this document to choose the right source set.
4. Read `README.md` for project-facing startup and template context.
5. Read `docs/architecture/base/00-README.md` and `docs/architecture/ADR_INDEX_GODOT.md` before changing architecture, overlays, or contracts.
6. Read `docs/testing-framework.md` before changing tests or gates.

## File Location Quick Reference
- PRD source material: `docs/prd/**/*.md`
- ADRs: `docs/adr/ADR-*.md`
- Base chapters: `docs/architecture/base/*.md`
- Overlays: `docs/architecture/overlays/<PRD-ID>/08/`
- Taskmaster triplet after generation: `.taskmaster/tasks/*.json`
- Logs and evidence: `logs/**`

## Overlay And ADR Discipline
- Any code or test change should cite at least one accepted ADR.
- If a change alters thresholds, contracts, security posture, or release policy, add a new ADR or supersede the old one.
- Concrete feature slices belong only in `docs/architecture/overlays/<PRD-ID>/08/`.
- Base chapter 08 remains a template and must not contain project-specific slices.
- For overlay work, start from the scoped sources above; do not blind-scan the entire `docs/` tree.
- If generated shard or index files exist in a copied project, prefer them over rebuilding ad hoc views.

## Typical Workflow
- Parse or refresh task data only after the target project has real Taskmaster inputs.
- Validate link integrity with `py -3 scripts/python/task_links_validate.py`.
- Validate test, acceptance, and CI behavior through `docs/testing-framework.md` and `scripts/sc/README.md`.

## Old AGENTS Coverage Map
- `0.1 New Session Quick Reference` -> this document
- `1 Context Discipline (RAG Rules)` -> this document + `docs/agents/10-template-customization.md`
