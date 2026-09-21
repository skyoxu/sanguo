# Semantic Delivery Topology

This directory is the governed structural home for the design-to-delivery topology.

Repository authority remains in the original GDD/PRD, ADR/architecture, Taskmaster and acceptance sources. Files in this directory are derived planning projections and MUST NOT become a second source of truth.

## Registered artifacts

Chapter 3 will eventually produce these files:

- `topology-manifest.v1.json`
- `source-blocks.v1.json`
- `semantic-requirements.v1.json`
- `capabilities.v1.json`
- `topology-edges.v1.json`
- optional `topology-overrides.v1.json`

Until the producer exists, the absence of these artifacts is valid migration state. Consumers must report `legacy_unmapped` / `topology unavailable`; they must not fabricate nodes.

Machine-readable minimum contracts live under `docs/planning/semantic-topology/schemas/**`. The runtime validator intentionally uses the same required fields without introducing a new JSON Schema package dependency. Once topology artifacts exist, missing artifact hashes, source-file hash drift, invalid ids/refs or schema-version drift are blocking structural failures.


## Authority and identity

- Source blocks are stable locators into original authority; copied preview text is never authority. JSON blocks preserve their logical `json_pointer` plus exact `source_char_start` / `source_char_end_exclusive` offsets, and `raw_text` is the corresponding original source slice rather than a JSON re-serialization.
- Semantic Requirements are normalized projections bound to one or more source blocks.
- Capability is optional grouping only. It has no sprint, status or completion lifecycle.
- Taskmaster remains the only task-state authority.
- Acceptance remains governed by the Chapter 5/task acceptance system.
- Project Health may project current task-view `acceptance[]` entries as read-only Acceptance nodes using stable `task_id + statement hash` ids. These nodes remain task-view authority; only explicit topology edges may mark semantic origin as mapped.
- Scene/script/resource/test links are evidence and navigation, not proof that a semantic requirement is accepted.
- Main topology is bound to `refs/heads/main` and canonical KCP publication identity.
- Workspace/Chapter-run topology is preview-only and must use an explicit `workspace:<digest>` or run identity. It never updates KCP `current` / `last-known-good`.

## Typed edge minimum

Edges use explicit endpoint types and ids:

```json
{
  "source_type": "requirement",
  "source_id": "FR-UPGRADE-001",
  "target_type": "task",
  "target_id": "42",
  "relation": "implemented_by"
}
```

Valid routes include Requirement → Capability → Task, Requirement → Task, Requirement → global constraint / quality gate / ADR-owned sink, and Requirement → multiple Tasks. Do not create a Capability merely to make a graph look complete.
