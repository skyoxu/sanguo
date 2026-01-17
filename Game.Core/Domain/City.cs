using MoneyValue = Game.Core.Domain.ValueObjects.Money;
namespace Game.Core.Domain;

public sealed record City
{
    public City(string id, string name, string regionId, MoneyValue basePrice, MoneyValue baseToll, int positionIndex = 0)
    {
        if (string.IsNullOrWhiteSpace(id))
            throw new ArgumentException("Id must be non-empty.", nameof(id));

        if (string.IsNullOrWhiteSpace(name))
            throw new ArgumentException("Name must be non-empty.", nameof(name));

        if (string.IsNullOrWhiteSpace(regionId))
            throw new ArgumentException("RegionId must be non-empty.", nameof(regionId));

        if (positionIndex < 0)
            throw new ArgumentOutOfRangeException(nameof(positionIndex), "PositionIndex must be non-negative.");

        Id = id;
        Name = name;
        RegionId = regionId;
        BasePrice = basePrice;
        BaseToll = baseToll;
        PositionIndex = positionIndex;
    }

    public string Id { get; }

    public string Name { get; }

    public string RegionId { get; }

    public MoneyValue BasePrice { get; }

    public MoneyValue BaseToll { get; }

    public int PositionIndex { get; }

    public MoneyValue GetPrice(decimal multiplier, SanguoEconomyRules rules)
    {
        if (!rules.IsValidPriceMultiplier(multiplier))
            throw new ArgumentOutOfRangeException(nameof(multiplier), $"Multiplier must be between {rules.MinMultiplier} and {rules.MaxPriceMultiplier} in 0.5 steps.");

        return MoneyValue.FromDecimal(BasePrice.ToDecimal() * multiplier);
    }

    public MoneyValue GetToll(decimal multiplier, SanguoEconomyRules rules)
    {
        if (!rules.IsValidTollMultiplier(multiplier))
            throw new ArgumentOutOfRangeException(nameof(multiplier), $"Multiplier must be between {rules.MinMultiplier} and {rules.MaxTollMultiplier} in 0.5 steps.");

        return MoneyValue.FromDecimal(BaseToll.ToDecimal() * multiplier);
    }
}
