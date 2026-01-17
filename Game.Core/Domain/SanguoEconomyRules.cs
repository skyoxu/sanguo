namespace Game.Core.Domain;

/// <summary>
/// Economy rule limits for the Sanguo T2 gameplay loop.
/// Keeps multiplier bounds configurable per game instance (fixed 0.5-step system).
/// </summary>
public readonly struct SanguoEconomyRules
{
    public const int MinSteps = 1;
    public const int MaxSteps = 6;
    public const int BaseDefaultSteps = 2;
    public const decimal Step = 0.5m;

    public const int DefaultMaxPriceSteps = MaxSteps;
    public const int DefaultMaxTollSteps = MaxSteps;

    public static SanguoEconomyRules Default => new(
        maxPriceSteps: DefaultMaxPriceSteps,
        maxTollSteps: DefaultMaxTollSteps);

    public SanguoEconomyRules(int maxPriceSteps, int maxTollSteps)
    {
        if (maxPriceSteps is < MinSteps or > MaxSteps)
            throw new ArgumentOutOfRangeException(nameof(maxPriceSteps), $"MaxPriceSteps must be between {MinSteps} and {MaxSteps}.");

        if (maxTollSteps is < MinSteps or > MaxSteps)
            throw new ArgumentOutOfRangeException(nameof(maxTollSteps), $"MaxTollSteps must be between {MinSteps} and {MaxSteps}.");

        MaxPriceSteps = maxPriceSteps;
        MaxTollSteps = maxTollSteps;
    }

    public int MaxPriceSteps { get; }

    public int MaxTollSteps { get; }

    public decimal MinMultiplier => MinSteps * Step;

    public decimal MaxPriceMultiplier => MaxPriceSteps * Step;

    public decimal MaxTollMultiplier => MaxTollSteps * Step;

    public static bool IsHalfStepMultiplier(decimal value)
    {
        var doubled = value * 2m;
        return doubled == decimal.Truncate(doubled);
    }

    public bool IsValidPriceMultiplier(decimal value)
        => value >= MinMultiplier && value <= MaxPriceMultiplier && IsHalfStepMultiplier(value);

    public bool IsValidTollMultiplier(decimal value)
        => value >= MinMultiplier && value <= MaxTollMultiplier && IsHalfStepMultiplier(value);
}
