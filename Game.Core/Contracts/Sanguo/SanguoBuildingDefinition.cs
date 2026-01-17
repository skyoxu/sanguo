namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: SanguoBuildingDefinition
/// Description: Building definition contract loaded from Data/buildings.json (stop-loss version).
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoBuildingDefinition(
    string BuildingId,
    string NameKey,
    string DescriptionKey,
    int MaxLevel,
    int BuildCostBase,
    int UpgradeCostBase,
    int SettlementIncomeBase,
    SanguoEconomyStepDeltas EconomyStepDeltas
);
