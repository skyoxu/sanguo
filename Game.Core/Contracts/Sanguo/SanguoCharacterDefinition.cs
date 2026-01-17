namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: SanguoEconomyStepDeltas
/// Description: Economy step-deltas for the fixed 0.5-step multiplier system.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoEconomyStepDeltas(
    int BuyPrice,
    int Toll,
    int IncomeSettlement,
    int BuildCost,
    int UpgradeCost
);

/// <summary>
/// DTO: SanguoCharacterDefinition
/// Description: Read-only character definition loaded from res:// (no user:// template sources).
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0019 (security baseline), ADR-0004 (event bus and contracts).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoCharacterDefinition(
    string CharacterId,
    string NameKey,
    string DescriptionKey,
    int CombatRating,
    string PortraitPath,
    int StartingMoneyStepDelta,
    SanguoEconomyStepDeltas EconomyStepDeltas
);
