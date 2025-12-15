namespace Game.Core.Domain;

public sealed record City(
    string Id,
    string Name,
    string RegionId,
    decimal BasePrice,
    decimal BaseToll
)
{
    public decimal GetPrice(decimal multiplier) => BasePrice * multiplier;

    public decimal GetToll(decimal multiplier) => BaseToll * multiplier;
}

