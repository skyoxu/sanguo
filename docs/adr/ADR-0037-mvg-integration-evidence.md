# ADR-0037: Bounded MVG Integration Evidence

- Status: Proposed
- Date: 2026-09-18
- Context: Per-task commits and gates do not alone prove that Sanguo's integrated MVG behaves correctly across task boundaries.
- Decision:
  - Add an opt-in manifest connecting existing Taskmaster IDs, handoff ownership, contract references and integration tests. Taskmaster remains the only task-state authority; MVG evidence never writes task status.
  - Execute all declared tests against an isolated, identified commit or workspace snapshot. Runtime verification requires non-empty positive reports, exact class/suite identity, consistent counts, process success and zero skipped tests.
  - Distinguish domain-integration, scene-method and engine-input evidence. The first Sanguo pilot covers MainMenu/new-game/bootstrap only; it does not establish whole-MVG or human gameplay acceptance.
  - Add a conservative MVG regression recommendation layer over explicit source/contract/test mappings. Unknown or unmapped changes fall back to full-MVG, and recommendations never authorize excluding required tests. Formal Impact Index and Knowledge Control Plane remain authoritative for their existing scopes.
  - Keep seeded mutation and hole/refill experiments optional. Keep existing delivery-profile gates, Chapter 6 review and knowledge publication cadence.
- Consequences: Cross-task integration gaps gain explicit owners and executable evidence with bounded runtime cost. Manifest scope and behavioral assertions still require review. No branch-protection or release-policy change is introduced.
- Supersedes: None
- References: `docs/adr/ADR-0025-godot-test-strategy.md`, `docs/adr/ADR-0035-repository-knowledge-control-plane.md`, `docs/workflows/mvg-integration-acceptance.md`.

Implementation refinement: recommendations bind to the selected input revision. Godot prewarm is reused only after a passing suite in the same snapshot. Engine-input challenges count as defect detection only when the expected test assertion fails; runtime absence, compilation errors and timeouts are not accepted as evidence.
