namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Multiplier sources mask describing which breakdown factors are trustworthy.
/// </summary>
[System.Flags]
public enum AppliedMultiplierSources
{
    None = 0,
    Character = 1 << 0,
    Building = 1 << 1,
    Event = 1 << 2,
    ActionCard = 1 << 3,
}

/// <summary>
/// DTO: AppliedMultipliers
/// Description: Snapshot of all multiplier factors used by an economic computation.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// UI must only display this snapshot and MUST NOT compute money on its own.
/// Multiplier rules (current): values use 0.5 step, clamp the final effective multiplier to [0.5, 3.0].
/// </remarks>
public sealed record AppliedMultipliers(
    decimal Character,
    decimal Building,
    decimal Event,
    decimal ActionCard,
    decimal Effective,
    AppliedMultiplierSources Sources = AppliedMultiplierSources.None
)
{
    public const decimal MinMultiplier = 0.5m;
    public const decimal MaxMultiplier = 3.0m;
    public const decimal Step = 0.5m;

    public static decimal ClampToRange(decimal value)
    {
        if (value < MinMultiplier)
        {
            return MinMultiplier;
        }

        if (value > MaxMultiplier)
        {
            return MaxMultiplier;
        }

        return value;
    }

    public static bool IsHalfStep(decimal value)
    {
        var doubled = value * 2m;
        return doubled == decimal.Truncate(doubled);
    }
}
