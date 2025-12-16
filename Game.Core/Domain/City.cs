using MoneyValue = Game.Core.Domain.ValueObjects.Money;

namespace Game.Core.Domain;

public sealed record City
{
    public City(string id, string name, string regionId, MoneyValue basePrice, MoneyValue baseToll)
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

        Id = id;
        Name = name;
        RegionId = regionId;
        BasePrice = basePrice;
        BaseToll = baseToll;
    }

    public string Id { get; }

    public string Name { get; }

    public string RegionId { get; }

    public MoneyValue BasePrice { get; }

    public MoneyValue BaseToll { get; }

    public MoneyValue GetPrice(decimal multiplier)
    {
        if (multiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(multiplier), "Multiplier must be non-negative.");

        return MoneyValue.FromDecimal(BasePrice.ToDecimal() * multiplier);
    }

    public MoneyValue GetToll(decimal multiplier)
    {
        if (multiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(multiplier), "Multiplier must be non-negative.");

        return MoneyValue.FromDecimal(BaseToll.ToDecimal() * multiplier);
    }
}
