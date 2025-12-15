namespace Game.Core.Domain;

public sealed record City
{
    public City(string id, string name, string regionId, decimal basePrice, decimal baseToll)
    {
        if (string.IsNullOrWhiteSpace(id))
            throw new ArgumentException("Id must be non-empty.", nameof(id));

        if (string.IsNullOrWhiteSpace(name))
            throw new ArgumentException("Name must be non-empty.", nameof(name));

        if (string.IsNullOrWhiteSpace(regionId))
            throw new ArgumentException("RegionId must be non-empty.", nameof(regionId));

        if (basePrice < 0)
            throw new ArgumentOutOfRangeException(nameof(basePrice), "BasePrice must be non-negative.");

        if (baseToll < 0)
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

    public decimal BasePrice { get; }

    public decimal BaseToll { get; }

    public decimal GetPrice(decimal multiplier)
    {
        if (multiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(multiplier), "Multiplier must be non-negative.");

        return BasePrice * multiplier;
    }

    public decimal GetToll(decimal multiplier)
    {
        if (multiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(multiplier), "Multiplier must be non-negative.");

        return BaseToll * multiplier;
    }
}
