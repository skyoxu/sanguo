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
/// DTO: SanguoCombatStatsDefinition
/// Description: Additive combat stat payload for v4 runtime combat composition.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-V4/08/08-Contracts-Combat-Baseline.md.
/// </remarks>
public sealed record SanguoCombatStatsDefinition(
    int MaxHP,
    int CurrentHP,
    int Attack,
    decimal CritRate = 0m,
    decimal CritMultiplier = 1.5m,
    decimal LifeStealRate = 0m,
    decimal DodgeRate = 0m,
    decimal AttackSpeed = 2.0m,
    decimal DamageReductionRate = 0m,
    decimal ReflectRate = 0m,
    bool AoEEnabled = false
);

/// <summary>
/// DTO: SanguoSummonStatsDefinition
/// Description: Additive summon defaults for v4 combat without requiring a parallel summon schema.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-V4/08/08-Contracts-Combat-Baseline.md.
/// </remarks>
public sealed record SanguoSummonStatsDefinition(
    decimal InheritRatio = 0.5m,
    decimal DefaultAttackSpeed = 2.0m,
    bool InheritCrit = false,
    bool InheritReflect = false,
    bool InheritAoEEnabled = false
);

/// <summary>
/// DTO: SanguoCharacterCombatProfile
/// Description: Optional combat profile attached to a character definition for v4 additive expansion.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-V4/08/08-Contracts-Combat-Baseline.md.
/// </remarks>
public sealed record SanguoCharacterCombatProfile(
    SanguoCombatStatsDefinition? BaseStats = null,
    SanguoSummonStatsDefinition? SummonDefaults = null,
    IReadOnlyList<string>? PassiveSkillIds = null
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
    SanguoEconomyStepDeltas EconomyStepDeltas,
    SanguoCharacterCombatProfile? CombatProfile = null,
    int Attack = 0,
    int Defense = 0,
    int Health = 0,
    int Morale = 0
);

/// <summary>
/// DTO: CharacterDefinition
/// Description: Compact character combat definition surface for formal combat catalogs.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-V4/08/08-Contracts-Combat-Baseline.md.
/// </remarks>
public sealed class CharacterDefinition
{
    public string Id { get; set; } = string.Empty;

    public string Name { get; set; } = string.Empty;

    public int CombatRating { get; set; }

    public int Attack { get; set; }

    public int Defense { get; set; }

    public int Health { get; set; }

    public int Morale { get; set; }
}
