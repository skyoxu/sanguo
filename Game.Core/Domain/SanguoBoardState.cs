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
    private readonly Dictionary<string, City> _citiesById;
    private readonly IReadOnlyDictionary<string, SanguoPlayer> _playersById;

    /// <summary>
    /// Read-only view of players keyed by player id.
    /// Intended for read access (UI/AI) without allowing mutation through this API.
    /// </summary>
    public IReadOnlyDictionary<string, ISanguoPlayerView> Players
    {
        get
        {
            AssertThread();
            var snapshot = new Dictionary<string, ISanguoPlayerView>(StringComparer.Ordinal);
            foreach (var (id, player) in _playersById)
                snapshot[id] = player;
            return snapshot;
        }
    }

    /// <summary>
    /// Read-only view of cities keyed by city id.
    /// </summary>
    public IReadOnlyDictionary<string, City> CitiesById
    {
        get
        {
            AssertThread();
            return new Dictionary<string, City>(_citiesById, StringComparer.Ordinal);
        }
    }

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
            if (!StringComparer.Ordinal.Equals(cityId, city.Id))
                throw new ArgumentException($"citiesById key does not match City.Id (key={cityId}, city.Id={city.Id}).", nameof(citiesById));
            citiesSnapshot.Add(cityId, city);
        }

        _citiesById = citiesSnapshot;

        foreach (var player in _playersById.Values)
        {
            foreach (var ownedCityId in player.OwnedCityIds)
            {
                if (!_citiesById.ContainsKey(ownedCityId))
                    throw new InvalidOperationException($"OwnedCityId not found in citiesById (playerId={player.PlayerId}, cityId={ownedCityId}).");
            }
        }
    }

    /// <summary>
    /// Attempts to buy a city for the given buyer.
    /// Returns false when the buyer or city is not found, when the city is already owned by another player,
    /// when the buyer is eliminated, or when the buyer has insufficient funds.
    /// </summary>
    /// <param name="buyerId">Buyer player id.</param>
    /// <param name="cityId">City id to buy.</param>
    /// <param name="priceMultiplier">Price multiplier (0..Max; 1.0 = base price).</param>
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

        if (buyer.PositionIndex != city.PositionIndex)
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

    /// <summary>
    /// Attempts to resolve the unique owner of the specified city.
    /// Returns false when the city does not exist or is currently unowned.
    /// </summary>
    /// <param name="cityId">City id to resolve.</param>
    /// <param name="owner">Resolved owner when found; otherwise null.</param>
    /// <returns>True when a unique owner exists; otherwise false.</returns>
    /// <exception cref="ArgumentException">Thrown when <paramref name="cityId"/> is empty/whitespace.</exception>
    /// <exception cref="InvalidOperationException">Thrown when multiple players claim ownership of the same city.</exception>
    public bool TryGetOwnerOfCity(string cityId, out SanguoPlayer? owner)
    {
        AssertThread();

        if (string.IsNullOrWhiteSpace(cityId))
            throw new ArgumentException("CityId must be non-empty.", nameof(cityId));

        owner = null;

        if (!_citiesById.ContainsKey(cityId))
            return false;

        foreach (var player in _playersById.Values)
        {
            if (!player.OwnsCityId(cityId))
                continue;

            if (owner is not null)
                throw new InvalidOperationException($"Multiple owners detected for cityId={cityId}.");

            owner = player;
        }

        return owner is not null;
    }

    public bool TryGetPlayer(string playerId, out SanguoPlayer? player)
    {
        AssertThread();

        if (string.IsNullOrWhiteSpace(playerId))
            throw new ArgumentException("PlayerId must be non-empty.", nameof(playerId));

        return _playersById.TryGetValue(playerId, out player);
    }

    public IReadOnlyDictionary<string, City> GetCitiesSnapshot()
    {
        AssertThread();
        return new Dictionary<string, City>(_citiesById, StringComparer.Ordinal);
    }

    /// <summary>
    /// Applies updated city economy values to the existing board state.
    /// Only <see cref="City.BasePrice"/> and <see cref="City.BaseToll"/> may change; all other fields must match.
    /// </summary>
    /// <param name="updatedCities">Updated city list keyed by <see cref="City.Id"/>.</param>
    /// <exception cref="ArgumentNullException">Thrown when <paramref name="updatedCities"/> is null.</exception>
    /// <exception cref="ArgumentException">Thrown when <paramref name="updatedCities"/> contains duplicate ids.</exception>
    /// <exception cref="InvalidOperationException">
    /// Thrown when any city is missing, unknown, or differs in non-economy fields.
    /// </exception>
    public void ApplyCityEconomyUpdates(IReadOnlyList<City> updatedCities)
    {
        AssertThread();
        ArgumentNullException.ThrowIfNull(updatedCities, nameof(updatedCities));

        var updatedById = new Dictionary<string, City>(StringComparer.Ordinal);
        foreach (var city in updatedCities)
        {
            ArgumentNullException.ThrowIfNull(city, nameof(updatedCities));
            if (!updatedById.TryAdd(city.Id, city))
                throw new ArgumentException($"Duplicate city id: {city.Id}", nameof(updatedCities));
        }

        if (updatedById.Count != _citiesById.Count)
            throw new InvalidOperationException("Updated city count does not match the current board state.");

        foreach (var (cityId, existing) in _citiesById)
        {
            if (!updatedById.TryGetValue(cityId, out var updated))
                throw new InvalidOperationException($"Updated city id not found: {cityId}");

            if (!StringComparer.Ordinal.Equals(existing.Id, updated.Id))
                throw new InvalidOperationException($"City id mismatch for cityId={cityId}.");
            if (!StringComparer.Ordinal.Equals(existing.Name, updated.Name))
                throw new InvalidOperationException($"City name mismatch for cityId={cityId}.");
            if (!StringComparer.Ordinal.Equals(existing.RegionId, updated.RegionId))
                throw new InvalidOperationException($"City region mismatch for cityId={cityId}.");
            if (existing.PositionIndex != updated.PositionIndex)
                throw new InvalidOperationException($"City position mismatch for cityId={cityId}.");

            _citiesById[cityId] = new City(
                id: existing.Id,
                name: existing.Name,
                regionId: existing.RegionId,
                basePrice: updated.BasePrice,
                baseToll: updated.BaseToll,
                positionIndex: existing.PositionIndex);
        }
    }

    private void AssertThread() => _threadGuard.AssertCurrentThread();
}
