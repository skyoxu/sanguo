# Architecture Guardrails

The repository guardrails are enforced in three layers.

1. ADR layer
- Decisions that change architecture, guardrails, or release policy must be captured in `docs/adr/`.

2. Documentation layer
- arc42 base chapters stay in `docs/architecture/base/`.
- PRD-specific slices stay in `docs/architecture/overlays/`.
- Agent recovery guidance stays in `docs/agents/`.

3. Script layer
- `scripts/python/` and `scripts/sc/` enforce refs, contracts, acceptance, test naming, and review pipeline rules.
