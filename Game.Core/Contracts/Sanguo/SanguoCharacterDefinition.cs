namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: SanguoCharacterEconomy
/// Description: Character-scoped economy coefficients (display-only for UI; applied in Core computations only).
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoCharacterEconomy(
    decimal BuyPriceMultiplier,
    decimal TollMultiplier,
    decimal MonthSettlementMultiplier
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
    string Name,
    string Description,
    string PortraitPath,
    SanguoCharacterEconomy Economy
);

