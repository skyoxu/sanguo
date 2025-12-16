namespace Game.Core.Domain;

/// <summary>
/// Economy rule limits for the Sanguo T2 gameplay loop.
/// Keeps multiplier bounds configurable per game instance.
/// </summary>
public readonly struct SanguoEconomyRules
{
    public const decimal DefaultMaxPriceMultiplier = 1000m;
    public const decimal DefaultMaxTollMultiplier = 1000m;

    public static SanguoEconomyRules Default => new(
        maxPriceMultiplier: DefaultMaxPriceMultiplier,
        maxTollMultiplier: DefaultMaxTollMultiplier);

    public SanguoEconomyRules(decimal maxPriceMultiplier, decimal maxTollMultiplier)
    {
        if (maxPriceMultiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(maxPriceMultiplier), "MaxPriceMultiplier must be non-negative.");

        if (maxTollMultiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(maxTollMultiplier), "MaxTollMultiplier must be non-negative.");

        MaxPriceMultiplier = maxPriceMultiplier;
        MaxTollMultiplier = maxTollMultiplier;
    }

    public decimal MaxPriceMultiplier { get; }

    public decimal MaxTollMultiplier { get; }
}
