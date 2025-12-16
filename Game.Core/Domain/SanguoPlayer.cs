using Game.Core.Domain.Threading;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;

namespace Game.Core.Domain;

/// <summary>
/// T2 player entity for the Sanguo board-style gameplay loop.
/// Manages money, position index, and owned city ids in the domain layer (pure C#).
/// </summary>
/// <remarks>
/// Thread-safety: enforced single-threaded access; cross-thread calls throw <see cref="InvalidOperationException"/>.
/// </remarks>
public sealed class SanguoPlayer : IPlayer
{
    private readonly ThreadAccessGuard _threadGuard;
    private readonly HashSet<string> _ownedCityIds = new();
    private MoneyValue _money;
    private int _positionIndex;
    private bool _isEliminated;

    /// <summary>
    /// Creates a new player with an initial money balance and board position index.
    /// </summary>
    /// <param name="playerId">Unique player id.</param>
    /// <param name="money">Initial money. Must be non-negative.</param>
    /// <param name="positionIndex">Initial position index. Must be non-negative.</param>
    /// <exception cref="ArgumentException">Thrown when <paramref name="playerId"/> is empty.</exception>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when <paramref name="money"/> or <paramref name="positionIndex"/> is negative.</exception>
    public SanguoPlayer(string playerId, decimal money, int positionIndex)
    {
        _threadGuard = ThreadAccessGuard.CaptureCurrentThread();

        if (string.IsNullOrWhiteSpace(playerId))
            throw new ArgumentException("PlayerId must be non-empty.", nameof(playerId));

        if (positionIndex < 0)
            throw new ArgumentOutOfRangeException(nameof(positionIndex), "PositionIndex must be non-negative.");

        PlayerId = playerId;
        _money = MoneyValue.FromDecimal(money);
        _positionIndex = positionIndex;
    }

    /// <summary>
    /// Unique player identifier.
    /// </summary>
    public string PlayerId { get; }

    /// <summary>
    /// Current money balance. Must never be negative.
    /// </summary>
    public MoneyValue Money
    {
        get
        {
            AssertThread();
            return _money;
        }
        private set
        {
            AssertThread();
            _money = value;
        }
    }

    /// <summary>
    /// Current position on the board (0-based index).
    /// </summary>
    public int PositionIndex
    {
        get
        {
            AssertThread();
            return _positionIndex;
        }
        private set
        {
            AssertThread();
            _positionIndex = value;
        }
    }

    /// <summary>
    /// Owned city ids. When a player is eliminated, this collection is cleared.
    /// </summary>
    public IReadOnlyCollection<string> OwnedCityIds
    {
        get
        {
            AssertThread();
            return _ownedCityIds;
        }
    }

    /// <summary>
    /// True when this player has been eliminated and is locked from further actions.
    /// </summary>
    public bool IsEliminated
    {
        get
        {
            AssertThread();
            return _isEliminated;
        }
        private set
        {
            AssertThread();
            _isEliminated = value;
        }
    }

    private void AssertThread() => _threadGuard.AssertCurrentThread();

    /// <summary>
    /// Attempts to buy a city at the given price multiplier.
    /// Returns false when the city is already owned by this player, when funds are insufficient,
    /// or when the player has been eliminated.
    /// </summary>
    /// <param name="city">City to buy.</param>
    /// <param name="priceMultiplier">Price multiplier (1.0 = base price).</param>
    /// <returns>True if the purchase succeeds; otherwise false.</returns>
    /// <exception cref="ArgumentNullException">Thrown when <paramref name="city"/> is null.</exception>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when <paramref name="priceMultiplier"/> is negative.</exception>
    public bool TryBuyCity(City city, decimal priceMultiplier)
    {
        AssertThread();

        if (IsEliminated)
            return false;

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

    /// <summary>
    /// Attempts to pay toll to the owner of a city.
    /// </summary>
    /// <remarks>
    /// Bankruptcy rule: if funds are insufficient to cover the full toll, the remaining money is transferred
    /// to the creditor, the payer money becomes 0, the payer is marked eliminated, and all owned cities are released
    /// (OwnedCityIds cleared). This method returns false when no action is performed
    /// (payer eliminated, owner eliminated, or owner is self).
    /// </remarks>
    /// <param name="owner">City owner receiving the payment.</param>
    /// <param name="city">City to calculate toll from.</param>
    /// <param name="tollMultiplier">Toll multiplier (1.0 = base toll).</param>
    /// <returns>True if a payment/elimination action was performed; otherwise false.</returns>
    /// <exception cref="ArgumentNullException">Thrown when <paramref name="owner"/> or <paramref name="city"/> is null.</exception>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when <paramref name="tollMultiplier"/> is negative.</exception>
    public bool TryPayTollTo(SanguoPlayer owner, City city, decimal tollMultiplier, out MoneyValue overflowToTreasury)
    {
        AssertThread();
        owner.AssertThread();

        overflowToTreasury = MoneyValue.Zero;

        if (IsEliminated)
            return false;

        ArgumentNullException.ThrowIfNull(owner, nameof(owner));
        ArgumentNullException.ThrowIfNull(city, nameof(city));

        if (tollMultiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(tollMultiplier), "Toll multiplier must be non-negative.");

        if (owner.IsEliminated)
            return false;

        if (owner.PlayerId == PlayerId)
            return false;

        var toll = city.GetToll(tollMultiplier);
        if (Money >= toll)
        {
            var newPayerMoney = Money - toll;
            Money = newPayerMoney;

            var newOwnerMoney = owner.Money.AddCapped(toll, out overflowToTreasury);
            owner.Money = newOwnerMoney;
            return true;
        }

        var remaining = Money;
        Money = MoneyValue.Zero;
        var newOwnerMoneyAfterBankruptcy = owner.Money.AddCapped(remaining, out overflowToTreasury);
        owner.Money = newOwnerMoneyAfterBankruptcy;

        _ownedCityIds.Clear();
        IsEliminated = true;
        return true;
    }
}
