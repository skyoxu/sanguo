namespace Game.Core.Domain;

public sealed class SanguoPlayer
{
    private readonly HashSet<string> _ownedCityIds = new();

    public SanguoPlayer(string playerId, decimal money, int positionIndex)
    {
        if (string.IsNullOrWhiteSpace(playerId))
            throw new ArgumentException("PlayerId must be non-empty.", nameof(playerId));

        if (money < 0)
            throw new ArgumentOutOfRangeException(nameof(money), "Money must be non-negative.");

        if (positionIndex < 0)
            throw new ArgumentOutOfRangeException(nameof(positionIndex), "PositionIndex must be non-negative.");

        PlayerId = playerId;
        Money = money;
        PositionIndex = positionIndex;
    }

    public string PlayerId { get; }

    public decimal Money { get; private set; }

    public int PositionIndex { get; private set; }

    public IReadOnlyCollection<string> OwnedCityIds => _ownedCityIds;

    public bool TryBuyCity(City city, decimal priceMultiplier)
    {
        ArgumentNullException.ThrowIfNull(city, nameof(city));

        if (priceMultiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(priceMultiplier), "Price multiplier must be non-negative.");

        if (_ownedCityIds.Contains(city.Id))
            return false;

        var price = city.GetPrice(priceMultiplier);
        if (Money < price)
            return false;

        Money -= price;
        _ownedCityIds.Add(city.Id);
        return true;
    }

    public void PayTollTo(SanguoPlayer owner, City city, decimal tollMultiplier)
    {
        ArgumentNullException.ThrowIfNull(owner, nameof(owner));
        ArgumentNullException.ThrowIfNull(city, nameof(city));

        if (tollMultiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(tollMultiplier), "Toll multiplier must be non-negative.");

        if (owner.PlayerId == PlayerId)
            return;

        var toll = city.GetToll(tollMultiplier);
        Money -= toll;
        owner.Money += toll;
    }
}

