namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: SanguoBuildingDefinition
/// Description: Building contract (stop-loss version) that only allows multiplier_step_delta effects.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoBuildingDefinition(
    string BuildingId,
    string Name,
    string Description,
    int MultiplierStepDelta
);

