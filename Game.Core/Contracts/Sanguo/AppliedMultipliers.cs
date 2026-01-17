namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Step-delta sources mask describing which breakdown factors are trustworthy.
/// </summary>
[System.Flags]
public enum AppliedMultiplierSources
{
    None = 0,
    Character = 1 << 0,
    Building = 1 << 1,
    Event = 1 << 2,
    ActionCard = 1 << 3,
    Relic = 1 << 4,
    Region = 1 << 5,
}

/// <summary>
/// DTO: AppliedMultipliers
/// Description: Snapshot of the fixed 0.5-step multiplier system used by an economic computation.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// UI must only display this snapshot and MUST NOT compute money on its own.
/// Rules:
/// - base_steps = 2 (=> 1.0x)
/// - effective_steps = clamp(base_steps + sum(step_delta), 1, 6)
/// - effective_multiplier = effective_steps * 0.5
/// </remarks>
public sealed record AppliedMultipliers(
    int BaseSteps,
    int CharacterStepDelta,
    int BuildingStepDelta,
    int EventStepDelta,
    int ActionCardStepDelta,
    int RelicStepDelta,
    int RegionStepDelta,
    int EffectiveSteps,
    AppliedMultiplierSources Sources = AppliedMultiplierSources.None
)
{
    public const decimal Step = 0.5m;
    public const int BaseDefaultSteps = 2;
    public const int MinSteps = 1;
    public const int MaxSteps = 6;

    public decimal EffectiveMultiplier => EffectiveSteps * Step;

    public static int ClampSteps(int value)
    {
        if (value < MinSteps)
        {
            return MinSteps;
        }

        if (value > MaxSteps)
        {
            return MaxSteps;
        }

        return value;
    }

    public static bool IsHalfStepMultiplier(decimal value)
    {
        var doubled = value * 2m;
        return doubled == decimal.Truncate(doubled);
    }
}
