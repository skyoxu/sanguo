using Game.Core.Domain.Threading;

namespace Game.Core.Domain;

/// <summary>
/// Pure C# state container for the Sanguo board loop.
/// Owns the authoritative "who can do what now" decisions that require
/// global context (players + cities), such as land purchase eligibility.
/// </summary>
/// <remarks>
/// This class intentionally avoids duplicating city ownership state.
/// The single source of truth is still <see cref="SanguoPlayer.OwnedCityIds"/>.
/// </remarks>
public sealed class SanguoBoardState
{
    private readonly ThreadAccessGuard _threadGuard;
    private readonly IReadOnlyDictionary<string, City> _citiesById;
    private readonly IReadOnlyDictionary<string, SanguoPlayer> _playersById;

    public SanguoBoardState(
        IReadOnlyList<SanguoPlayer> players,
        IReadOnlyDictionary<string, City> citiesById
    )
    {
        _threadGuard = ThreadAccessGuard.CaptureCurrentThread();

        ArgumentNullException.ThrowIfNull(players, nameof(players));
        ArgumentNullException.ThrowIfNull(citiesById, nameof(citiesById));

        var playersById = new Dictionary<string, SanguoPlayer>(StringComparer.Ordinal);
        foreach (var player in players)
        {
            ArgumentNullException.ThrowIfNull(player, nameof(player));
            try
            {
                _ = player.Money;
            }
            catch (InvalidOperationException ex)
            {
                throw new InvalidOperationException(
                    $"Player thread guard mismatch for playerId={player.PlayerId}. Ensure players and SanguoBoardState are created and used on the same thread.",
                    ex);
            }

            if (playersById.ContainsKey(player.PlayerId))
                throw new ArgumentException($"Duplicate player id: {player.PlayerId}", nameof(players));
            playersById.Add(player.PlayerId, player);
        }

        _playersById = playersById;

        var citiesSnapshot = new Dictionary<string, City>(StringComparer.Ordinal);
        foreach (var (cityId, city) in citiesById)
        {
            ArgumentNullException.ThrowIfNull(city, nameof(city));
            if (citiesSnapshot.ContainsKey(cityId))
                throw new ArgumentException($"Duplicate city id: {cityId}", nameof(citiesById));
            citiesSnapshot.Add(cityId, city);
        }

        _citiesById = citiesSnapshot;
    }

    /// <summary>
    /// Attempts to buy a city for the given buyer.
    /// Returns false when the buyer or city is not found, when the city is already owned by another player,
    /// when the buyer is eliminated, or when the buyer has insufficient funds.
    /// </summary>
    /// <param name="buyerId">Buyer player id.</param>
    /// <param name="cityId">City id to buy.</param>
    /// <param name="priceMultiplier">Price multiplier (1.0 = base price).</param>
    /// <returns>True if the purchase succeeds; otherwise false.</returns>
    /// <exception cref="ArgumentException">Thrown when <paramref name="buyerId"/> or <paramref name="cityId"/> is empty/whitespace.</exception>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when <paramref name="priceMultiplier"/> is out of allowed range.</exception>
    public bool TryBuyCity(string buyerId, string cityId, decimal priceMultiplier)
    {
        AssertThread();

        if (string.IsNullOrWhiteSpace(buyerId))
            throw new ArgumentException("BuyerId must be non-empty.", nameof(buyerId));

        if (string.IsNullOrWhiteSpace(cityId))
            throw new ArgumentException("CityId must be non-empty.", nameof(cityId));

        if (!_playersById.TryGetValue(buyerId, out var buyer))
            return false;

        if (!_citiesById.TryGetValue(cityId, out var city))
            return false;

        foreach (var player in _playersById.Values)
        {
            if (player.PlayerId == buyerId)
                continue;

            if (player.OwnsCityId(cityId))
                return false;
        }

        return buyer.TryBuyCity(city, priceMultiplier);
    }

    private void AssertThread() => _threadGuard.AssertCurrentThread();
}
