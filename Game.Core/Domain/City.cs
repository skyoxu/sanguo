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

        if (basePrice < MoneyValue.Zero)
            throw new ArgumentOutOfRangeException(nameof(basePrice), "BasePrice must be non-negative.");

        if (baseToll < MoneyValue.Zero)
            throw new ArgumentOutOfRangeException(nameof(baseToll), "BaseToll must be non-negative.");

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
        if (multiplier < 0 || multiplier > rules.MaxPriceMultiplier)
            throw new ArgumentOutOfRangeException(nameof(multiplier), $"Multiplier must be between 0 and {rules.MaxPriceMultiplier}.");

        return MoneyValue.FromDecimal(BasePrice.ToDecimal() * multiplier);
    }

    public MoneyValue GetToll(decimal multiplier, SanguoEconomyRules rules)
    {
        if (multiplier < 0 || multiplier > rules.MaxTollMultiplier)
            throw new ArgumentOutOfRangeException(nameof(multiplier), $"Multiplier must be between 0 and {rules.MaxTollMultiplier}.");

        return MoneyValue.FromDecimal(BaseToll.ToDecimal() * multiplier);
    }
}
