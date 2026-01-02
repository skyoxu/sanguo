using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Utilities;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;

namespace Game.Core.Services;

/// <summary>
/// Sanguo economy settlement manager.
/// Responsibilities: month-end settlement, yearly land price adjustments, and quarterly environment event emission.
/// Economy rules follow ADR-0021; event publishing follows ADR-0004 (CloudEvents-like contracts).
/// </summary>
/// <remarks>
/// Related ADRs:
/// - ADR-0005: Quality gates (coverage, docs)
/// - ADR-0015: Performance budgets (complexity O(players * cities))
/// - ADR-0018: Testing strategy (unit tests, boundary tests)
/// - ADR-0021: Economy rules (monthly settlement, yearly adjustment, quarterly events)
/// - ADR-0024: Event tracing (CorrelationId/CausationId)
/// </remarks>
public sealed class SanguoEconomyManager
{
    private readonly IEventBus _bus;
    private ActiveSeasonYieldAdjustment? _activeSeasonYieldAdjustment;

    private sealed record ActiveSeasonYieldAdjustment(
        int Year,
        int Season,
        HashSet<string> AffectedRegionIds,
        decimal YieldMultiplier
    );

    /// <summary>
    /// Creates a new <see cref="SanguoEconomyManager"/>.
    /// </summary>
    /// <param name="bus">Event bus used to publish domain events (must not be null).</param>
    /// <exception cref="ArgumentNullException">Thrown when <paramref name="bus"/> is null.</exception>
    public SanguoEconomyManager(IEventBus bus)
    {
        _bus = bus ?? throw new ArgumentNullException(nameof(bus));
    }

    internal void SetActiveSeasonYieldAdjustment(
        int year,
        int season,
        IReadOnlyList<string> affectedRegionIds,
        decimal yieldMultiplier
    )
    {
        if (year < 0)
            throw new ArgumentOutOfRangeException(nameof(year), "Year must be non-negative.");

        if (season is < 1 or > 4)
            throw new ArgumentOutOfRangeException(nameof(season), "Season must be between 1 and 4.");

        ArgumentNullException.ThrowIfNull(affectedRegionIds, nameof(affectedRegionIds));

        if (yieldMultiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(yieldMultiplier), "Yield multiplier must be non-negative.");

        if (affectedRegionIds.Count == 0 || yieldMultiplier == 1.0m)
        {
            _activeSeasonYieldAdjustment = null;
            return;
        }

        var set = new HashSet<string>(StringComparer.Ordinal);
        foreach (var id in affectedRegionIds)
        {
            if (string.IsNullOrWhiteSpace(id))
                continue;

            set.Add(id);
        }

        if (set.Count == 0)
        {
            _activeSeasonYieldAdjustment = null;
            return;
        }

        _activeSeasonYieldAdjustment = new ActiveSeasonYieldAdjustment(
            Year: year,
            Season: season,
            AffectedRegionIds: set,
            YieldMultiplier: yieldMultiplier
        );
    }

    /// <summary>
    /// Calculates month-end settlement amounts for all non-eliminated players.
    /// Sums each owned city's <c>BaseToll</c> as monthly income.
    /// </summary>
    /// <param name="players">Player list (must not be null; eliminated players are skipped).</param>
    /// <param name="citiesById">City dictionary keyed by city id (must not be null; must contain all owned city ids).</param>
    /// <returns>A list of settlements (eliminated players are not included).</returns>
    /// <exception cref="ArgumentNullException">Thrown when <paramref name="players"/> or <paramref name="citiesById"/> is null.</exception>
    /// <exception cref="InvalidOperationException">Thrown when an owned city id is missing from <paramref name="citiesById"/>.</exception>
    /// <remarks>
    /// Complexity: O(players * cities), aligned with ADR-0015 performance budget.
    /// </remarks>
    public IReadOnlyList<PlayerSettlement> CalculateMonthSettlements(
        IReadOnlyList<ISanguoPlayerView> players,
        IReadOnlyDictionary<string, City> citiesById
    )
    {
        ArgumentNullException.ThrowIfNull(players, nameof(players));
        ArgumentNullException.ThrowIfNull(citiesById, nameof(citiesById));

        var settlements = new List<PlayerSettlement>(players.Count);
        foreach (var player in players)
        {
            if (player.IsEliminated)
                continue;

            var income = CalculateMonthlyIncome(player, citiesById);
            settlements.Add(new PlayerSettlement(player.PlayerId, income.ToDecimal()));
        }

        return settlements;
    }

    public IReadOnlyList<PlayerSettlement> SettleMonth(
        SanguoBoardState boardState,
        IReadOnlyList<string> playerOrder,
        SanguoTreasury treasury
    )
    {
        ArgumentNullException.ThrowIfNull(boardState, nameof(boardState));
        ArgumentNullException.ThrowIfNull(playerOrder, nameof(playerOrder));
        ArgumentNullException.ThrowIfNull(treasury, nameof(treasury));

        var citiesById = boardState.GetCitiesSnapshot();

        var orderedPlayers = new List<SanguoPlayer>(playerOrder.Count);
        var orderedPlayerViews = new List<ISanguoPlayerView>(playerOrder.Count);

        foreach (var playerId in playerOrder)
        {
            if (!boardState.TryGetPlayer(playerId, out var player))
                throw new InvalidOperationException($"Player not found in board state: {playerId}");

            orderedPlayers.Add(player!);
            orderedPlayerViews.Add(player!);
        }

        var computed = CalculateMonthSettlements(orderedPlayerViews, citiesById);
        var computedById = new Dictionary<string, decimal>(StringComparer.Ordinal);
        foreach (var settlement in computed)
            computedById[settlement.PlayerId] = settlement.AmountDelta;

        var results = new List<PlayerSettlement>(playerOrder.Count);
        for (var index = 0; index < playerOrder.Count; index++)
        {
            var playerId = playerOrder[index];
            var delta = computedById.TryGetValue(playerId, out var v) ? v : 0m;
            results.Add(new PlayerSettlement(playerId, delta));

            if (delta <= 0m)
                continue;

            orderedPlayers[index].CreditIncome(MoneyValue.FromDecimal(delta), treasury);
        }

        return results;
    }

    /// <summary>
    /// Attempts to buy a city for the given buyer, using global board state rules (unique ownership),
    /// and publishes <see cref="SanguoCityBought"/> on success.
    /// </summary>
    /// <param name="gameId">Game id (must be non-empty).</param>
    /// <param name="players">Player list (must not be null; player objects may be mutated).</param>
    /// <param name="citiesById">City dictionary keyed by city id (must not be null).</param>
    /// <param name="buyerId">Buyer player id (must be non-empty).</param>
    /// <param name="cityId">City id to buy (must be non-empty).</param>
    /// <param name="priceMultiplier">Price multiplier (0..Max; 1.0 = base price).</param>
    /// <param name="correlationId">Correlation id (must be non-empty).</param>
    /// <param name="causationId">Causation id (optional).</param>
    /// <param name="occurredAt">Occurrence timestamp.</param>
    /// <returns>True if the purchase succeeds; otherwise false.</returns>
    /// <exception cref="ArgumentException">Thrown when <paramref name="gameId"/>, <paramref name="buyerId"/>, <paramref name="cityId"/> or <paramref name="correlationId"/> is empty/whitespace.</exception>
    /// <exception cref="ArgumentNullException">Thrown when <paramref name="players"/> or <paramref name="citiesById"/> is null.</exception>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when <paramref name="priceMultiplier"/> is out of allowed range (enforced by buyer economy rules).</exception>
    public async Task<bool> TryBuyCityAndPublishEventAsync(
        string gameId,
        IReadOnlyList<SanguoPlayer> players,
        IReadOnlyDictionary<string, City> citiesById,
        string buyerId,
        string cityId,
        decimal priceMultiplier,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt
    )
    {
        if (string.IsNullOrWhiteSpace(gameId))
            throw new ArgumentException("GameId must be non-empty.", nameof(gameId));

        if (string.IsNullOrWhiteSpace(buyerId))
            throw new ArgumentException("BuyerId must be non-empty.", nameof(buyerId));

        if (string.IsNullOrWhiteSpace(cityId))
            throw new ArgumentException("CityId must be non-empty.", nameof(cityId));

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        ArgumentNullException.ThrowIfNull(players, nameof(players));
        ArgumentNullException.ThrowIfNull(citiesById, nameof(citiesById));

        var buyer = players.FirstOrDefault(p => p.PlayerId == buyerId);
        if (buyer is null)
            return false;

        var buyerSnapshot = buyer.CaptureRollbackSnapshot();
        var moneyBefore = buyer.Money;

        var boardState = new SanguoBoardState(players, citiesById);
        var bought = boardState.TryBuyCity(buyerId, cityId, priceMultiplier);
        if (!bought)
            return false;

        var price = (moneyBefore - buyer.Money).ToDecimal();

        var evt = new DomainEvent(
            Type: SanguoCityBought.EventType,
            Source: nameof(SanguoEconomyManager),
            Data: JsonElementEventData.FromObject(new SanguoCityBought(
                GameId: gameId,
                BuyerId: buyerId,
                CityId: cityId,
                Price: price,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId
            )),
            Timestamp: occurredAt.UtcDateTime,
            Id: Guid.NewGuid().ToString("N")
        );

        try
        {
            await _bus.PublishAsync(evt);
            return true;
        }
        catch (Exception ex)
        {
            buyer.RestoreRollbackSnapshot(buyerSnapshot);
            throw new InvalidOperationException(
                $"Event publish failed after city purchase. State has been rolled back (gameId={gameId}, buyerId={buyerId}, cityId={cityId}).",
                ex);
        }
    }

    /// <summary>
    /// Attempts to pay toll for the given payer when landing on a city owned by another player,
    /// and publishes <see cref="SanguoCityTollPaid"/> on success.
    /// </summary>
    /// <param name="gameId">Game id (must be non-empty).</param>
    /// <param name="players">Player list (must not be null; player objects may be mutated).</param>
    /// <param name="citiesById">City dictionary keyed by city id (must not be null).</param>
    /// <param name="payerId">Paying player id (must be non-empty).</param>
    /// <param name="cityId">City id that the payer is on (must be non-empty).</param>
    /// <param name="tollMultiplier">Toll multiplier (0..Max; 1.0 = base toll).</param>
    /// <param name="treasury">Treasury used to collect overflow (must not be null).</param>
    /// <param name="correlationId">Correlation id (must be non-empty).</param>
    /// <param name="causationId">Causation id (optional).</param>
    /// <param name="occurredAt">Occurrence timestamp.</param>
    /// <returns>True if toll was paid; otherwise false.</returns>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when <paramref name="tollMultiplier"/> is out of allowed range (enforced by payer economy rules).</exception>
    /// <exception cref="InvalidOperationException">Thrown when resolving city ownership detects corrupted board state.</exception>
    public async Task<bool> TryPayTollAndPublishEventAsync(
        string gameId,
        IReadOnlyList<SanguoPlayer> players,
        IReadOnlyDictionary<string, City> citiesById,
        string payerId,
        string cityId,
        decimal tollMultiplier,
        SanguoTreasury treasury,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt
    )
    {
        if (string.IsNullOrWhiteSpace(gameId))
            throw new ArgumentException("GameId must be non-empty.", nameof(gameId));

        if (string.IsNullOrWhiteSpace(payerId))
            throw new ArgumentException("PayerId must be non-empty.", nameof(payerId));

        if (string.IsNullOrWhiteSpace(cityId))
            throw new ArgumentException("CityId must be non-empty.", nameof(cityId));

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        ArgumentNullException.ThrowIfNull(players, nameof(players));
        ArgumentNullException.ThrowIfNull(citiesById, nameof(citiesById));
        ArgumentNullException.ThrowIfNull(treasury, nameof(treasury));

        var payer = players.FirstOrDefault(p => p.PlayerId == payerId);
        if (payer is null)
            return false;

        if (!citiesById.TryGetValue(cityId, out var city))
            return false;

        if (payer.PositionIndex != city.PositionIndex)
            return false;

        SanguoPlayer? owner;
        try
        {
            var boardState = new SanguoBoardState(players, citiesById);
            if (!boardState.TryGetOwnerOfCity(cityId, out owner) || owner is null)
                return false;
        }
        catch (InvalidOperationException ex)
        {
            throw new InvalidOperationException(
                $"Invalid board state while resolving city owner (gameId={gameId}, cityId={cityId}).",
                ex);
        }

        if (owner.PlayerId == payerId)
            return false;

        var payerSnapshot = payer.CaptureRollbackSnapshot();
        var ownerSnapshot = owner.CaptureRollbackSnapshot();
        var treasurySnapshot = treasury.CaptureRollbackSnapshot();

        var payerMoneyBefore = payer.Money;
        var ownerMoneyBefore = owner.Money;
        var treasuryMinorUnitsBefore = treasury.MinorUnits;
        var paid = payer.TryPayTollTo(owner, city, tollMultiplier, treasury);
        if (!paid)
            return false;

        var amountPaidMinorUnits = payerMoneyBefore.MinorUnits - payer.Money.MinorUnits;
        var ownerAmountMinorUnits = owner.Money.MinorUnits - ownerMoneyBefore.MinorUnits;
        var overflowMinorUnits = treasury.MinorUnits - treasuryMinorUnitsBefore;

        if (amountPaidMinorUnits != checked(ownerAmountMinorUnits + overflowMinorUnits))
            throw new InvalidOperationException($"Invariant violation for toll payment amounts (gameId={gameId}, cityId={cityId}).");

        var amountPaid = new MoneyValue(amountPaidMinorUnits).ToDecimal();
        var ownerAmount = new MoneyValue(ownerAmountMinorUnits).ToDecimal();
        var treasuryOverflow = new MoneyValue(overflowMinorUnits).ToDecimal();

        var evt = new DomainEvent(
            Type: SanguoCityTollPaid.EventType,
            Source: nameof(SanguoEconomyManager),
            Data: JsonElementEventData.FromObject(new SanguoCityTollPaid(
                GameId: gameId,
                PayerId: payerId,
                OwnerId: owner.PlayerId,
                CityId: cityId,
                Amount: amountPaid,
                OwnerAmount: ownerAmount,
                TreasuryOverflow: treasuryOverflow,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId
            )),
            Timestamp: occurredAt.UtcDateTime,
            Id: Guid.NewGuid().ToString("N")
        );

        try
        {
            await _bus.PublishAsync(evt);
            return true;
        }
        catch (Exception ex)
        {
            payer.RestoreRollbackSnapshot(payerSnapshot);
            owner.RestoreRollbackSnapshot(ownerSnapshot);
            treasury.RestoreRollbackSnapshot(treasurySnapshot);

            throw new InvalidOperationException(
                $"Event publish failed after toll payment. State has been rolled back (gameId={gameId}, payerId={payerId}, cityId={cityId}).",
                ex);
        }
    }

    /// <summary>
    /// Publishes a month-end settlement event when crossing a month boundary.
    /// Emits <see cref="SanguoMonthSettled"/> only when year or month differs between <paramref name="previousDate"/> and <paramref name="currentDate"/>.
    /// </summary>
    /// <param name="gameId">Game id (must be non-empty).</param>
    /// <param name="previousDate">Previous date (used for month boundary detection).</param>
    /// <param name="currentDate">Current date (used for month boundary detection).</param>
    /// <param name="settlements">Player settlements (must not be null).</param>
    /// <param name="correlationId">Correlation id (must be non-empty).</param>
    /// <param name="causationId">Causation id (optional).</param>
    /// <param name="occurredAt">Occurrence timestamp.</param>
    /// <exception cref="ArgumentException">Thrown when <paramref name="gameId"/> or <paramref name="correlationId"/> is empty/whitespace.</exception>
    /// <exception cref="ArgumentNullException">Thrown when <paramref name="settlements"/> is null.</exception>
    /// <remarks>
    /// Aligned with ADR-0004 (CloudEvents-like contract) and ADR-0024 (event tracing).
    /// Boundary check: do not publish when <c>previousDate.Year == currentDate.Year</c> and <c>previousDate.Month == currentDate.Month</c>.
    /// </remarks>
    public async Task PublishMonthSettlementIfBoundaryAsync(
        string gameId,
        SanguoCalendarDate previousDate,
        SanguoCalendarDate currentDate,
        IReadOnlyList<PlayerSettlement> settlements,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt
    )
    {
        if (string.IsNullOrWhiteSpace(gameId))
            throw new ArgumentException("GameId must be non-empty.", nameof(gameId));

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        ArgumentNullException.ThrowIfNull(settlements, nameof(settlements));

        if (previousDate.Year == currentDate.Year && previousDate.Month == currentDate.Month)
            return;

        var evt = new DomainEvent(
            Type: SanguoMonthSettled.EventType,
            Source: nameof(SanguoEconomyManager),
            Data: JsonElementEventData.FromObject(new SanguoMonthSettled(
                GameId: gameId,
                Year: previousDate.Year,
                Month: previousDate.Month,
                PlayerSettlements: settlements,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId
            )),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        );

        await _bus.PublishAsync(evt);
    }

    /// <summary>
    /// Calculates yearly land price adjustments per city.
    /// New price is computed by multiplying the base price by <paramref name="yearlyMultiplier"/>.
    /// </summary>
    /// <param name="cities">Cities (must not be null).</param>
    /// <param name="yearlyMultiplier">Yearly price multiplier (must be non-negative).</param>
    /// <returns>A list of adjustments: city id, old price, and new price.</returns>
    /// <exception cref="ArgumentNullException">Thrown when <paramref name="cities"/> is null.</exception>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when <paramref name="yearlyMultiplier"/> is negative.</exception>
    /// <remarks>
    /// Aligned with ADR-0021 (economy rules: yearly land price adjustment). Complexity: O(cities).
    /// </remarks>
    public IReadOnlyList<(string CityId, MoneyValue OldPrice, MoneyValue NewPrice)> CalculateYearlyPriceAdjustments(
        IReadOnlyList<City> cities,
        decimal yearlyMultiplier
    )
    {
        ArgumentNullException.ThrowIfNull(cities, nameof(cities));

        if (yearlyMultiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(yearlyMultiplier), "Yearly price multiplier must be non-negative.");

        var results = new List<(string CityId, MoneyValue OldPrice, MoneyValue NewPrice)>(cities.Count);
        foreach (var city in cities)
        {
            var oldPrice = city.BasePrice;
            var newPrice = MoneyValue.FromDecimal(oldPrice.ToDecimal() * yearlyMultiplier);
            results.Add((city.Id, oldPrice, newPrice));
        }

        return results;
    }

    public IReadOnlyList<(string CityId, MoneyValue OldPrice, MoneyValue NewPrice)> CalculateYearlyPriceAdjustments(
        IReadOnlyList<City> cities,
        decimal yearlyMultiplier,
        IRandomNumberGenerator rng
    )
    {
        ArgumentNullException.ThrowIfNull(cities, nameof(cities));
        ArgumentNullException.ThrowIfNull(rng, nameof(rng));

        if (yearlyMultiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(yearlyMultiplier), "Yearly price multiplier must be non-negative.");

        var results = new List<(string CityId, MoneyValue OldPrice, MoneyValue NewPrice)>(cities.Count);
        foreach (var city in cities)
        {
            var oldPrice = city.BasePrice;
            var multiplier = yearlyMultiplier * SampleYearlyMultiplier(rng);
            var newPrice = MoneyValue.FromDecimal(CapMoneyDecimal(oldPrice.ToDecimal() * multiplier));
            results.Add((city.Id, oldPrice, newPrice));
        }

        return results;
    }

    public IReadOnlyList<City> ApplyYearlyPriceAdjustment(IReadOnlyList<City> cities, IRandomNumberGenerator rng)
    {
        ArgumentNullException.ThrowIfNull(cities, nameof(cities));
        ArgumentNullException.ThrowIfNull(rng, nameof(rng));

        var updated = new List<City>(cities.Count);
        foreach (var city in cities)
        {
            var priceMultiplier = SampleYearlyMultiplier(rng);
            var tollMultiplier = SampleYearlyMultiplier(rng);

            var newPrice = MoneyValue.FromDecimal(CapMoneyDecimal(city.BasePrice.ToDecimal() * priceMultiplier));
            var newToll = MoneyValue.FromDecimal(CapMoneyDecimal(city.BaseToll.ToDecimal() * tollMultiplier));

            updated.Add(new City(
                id: city.Id,
                name: city.Name,
                regionId: city.RegionId,
                basePrice: newPrice,
                baseToll: newToll,
                positionIndex: city.PositionIndex));
        }

        return updated;
    }

    private static decimal SampleYearlyMultiplier(IRandomNumberGenerator rng)
    {
        var roll = rng.NextDouble();
        if (roll < 0.0 || roll > 1.0)
            throw new InvalidOperationException("IRandomNumberGenerator.NextDouble must return a value between 0 and 1.");

        return 0.5m + (decimal)roll;
    }

    private static decimal CapMoneyDecimal(decimal amount)
    {
        if (amount < 0)
            return 0;

        var max = (decimal)MoneyValue.MaxMajorUnits;
        if (amount > max)
            return max;

        return amount;
    }

    /// <summary>
    /// Publishes yearly land price adjustment events when crossing a year boundary.
    /// Emits one <see cref="SanguoYearPriceAdjusted"/> per city only when <paramref name="previousDate"/> and <paramref name="currentDate"/> have different years.
    /// </summary>
    /// <param name="gameId">Game id (must be non-empty).</param>
    /// <param name="previousDate">Previous date (used for year boundary detection).</param>
    /// <param name="currentDate">Current date (used for year boundary detection).</param>
    /// <param name="cities">Cities (must not be null; emits one event per city).</param>
    /// <param name="yearlyMultiplier">Yearly price multiplier (must be non-negative; applied to all cities).</param>
    /// <param name="correlationId">Correlation id (must be non-empty).</param>
    /// <param name="causationId">Causation id (optional).</param>
    /// <param name="occurredAt">Occurrence timestamp.</param>
    /// <exception cref="ArgumentException">Thrown when <paramref name="gameId"/> or <paramref name="correlationId"/> is empty/whitespace.</exception>
    /// <exception cref="ArgumentNullException">Thrown when <paramref name="cities"/> is null.</exception>
    /// <remarks>
    /// Aligned with ADR-0004 (CloudEvents-like contract), ADR-0021 (economy rules: yearly land price adjustment) and ADR-0024 (event tracing).
    /// Boundary check: do not publish when <c>previousDate.Year == currentDate.Year</c>.
    /// Calls <see cref="CalculateYearlyPriceAdjustments"/> and emits one <see cref="SanguoYearPriceAdjusted"/> per city.
    /// </remarks>
    public async Task PublishYearlyPriceAdjustmentIfBoundaryAsync(
        string gameId,
        SanguoCalendarDate previousDate,
        SanguoCalendarDate currentDate,
        IReadOnlyList<City> previousCities,
        IReadOnlyList<City> currentCities,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt
    )
    {
        if (string.IsNullOrWhiteSpace(gameId))
            throw new ArgumentException("GameId must be non-empty.", nameof(gameId));

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        ArgumentNullException.ThrowIfNull(previousCities, nameof(previousCities));
        ArgumentNullException.ThrowIfNull(currentCities, nameof(currentCities));

        if (previousDate.Year == currentDate.Year)
            return;

        var currentById = new Dictionary<string, City>(StringComparer.Ordinal);
        foreach (var city in currentCities)
        {
            ArgumentNullException.ThrowIfNull(city, nameof(currentCities));
            if (!currentById.TryAdd(city.Id, city))
                throw new InvalidOperationException($"Duplicate city id in currentCities: {city.Id}");
        }

        foreach (var oldCity in previousCities)
        {
            ArgumentNullException.ThrowIfNull(oldCity, nameof(previousCities));

            if (!currentById.TryGetValue(oldCity.Id, out var newCity))
                throw new InvalidOperationException($"City id not found in currentCities: {oldCity.Id}");

            var evt = new DomainEvent(
                Type: SanguoYearPriceAdjusted.EventType,
                Source: nameof(SanguoEconomyManager),
                Data: JsonElementEventData.FromObject(new SanguoYearPriceAdjusted(
                    GameId: gameId,
                    Year: currentDate.Year,
                    CityId: oldCity.Id,
                    OldPrice: oldCity.BasePrice.ToDecimal(),
                    NewPrice: newCity.BasePrice.ToDecimal(),
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: DateTime.UtcNow,
                Id: Guid.NewGuid().ToString("N")
            );

            await _bus.PublishAsync(evt);
        }
    }

    /// <summary>
    /// Publishes a quarterly environment event when crossing a quarter boundary.
    /// Emits <see cref="SanguoSeasonEventApplied"/> only when the quarter of <paramref name="previousDate"/> differs from the quarter of <paramref name="currentDate"/>.
    /// </summary>
    /// <param name="gameId">Game id (must be non-empty).</param>
    /// <param name="previousDate">Previous date (used for quarter boundary detection).</param>
    /// <param name="currentDate">Current date (used for quarter boundary detection).</param>
    /// <param name="season">Quarter/season number (1-4) and must match <paramref name="currentDate"/>.</param>
    /// <param name="affectedRegionIds">Affected region ids (must not be null).</param>
    /// <param name="yieldMultiplier">Yield multiplier (must be non-negative).</param>
    /// <param name="correlationId">Correlation id (must be non-empty).</param>
    /// <param name="causationId">Causation id (optional).</param>
    /// <param name="occurredAt">Occurrence timestamp.</param>
    /// <exception cref="ArgumentException">Thrown when <paramref name="gameId"/> or <paramref name="correlationId"/> is empty/whitespace.</exception>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when <paramref name="season"/> is out of range or <paramref name="yieldMultiplier"/> is negative.</exception>
    /// <exception cref="ArgumentNullException">Thrown when <paramref name="affectedRegionIds"/> is null.</exception>
    /// <remarks>
    /// Aligned with ADR-0004 (CloudEvents-like contract), ADR-0021 (economy rules: quarterly environment events) and ADR-0024 (event tracing).
    /// Boundary check: no emission when <paramref name="previousDate"/> and <paramref name="currentDate"/> are in the same quarter.
    /// The event uses <paramref name="currentDate"/> year.
    /// </remarks>
    public async Task PublishSeasonEventIfBoundaryAsync(
        string gameId,
        SanguoCalendarDate previousDate,
        SanguoCalendarDate currentDate,
        int season,
        IReadOnlyList<string> affectedRegionIds,
        decimal yieldMultiplier,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt
    )
    {
        if (string.IsNullOrWhiteSpace(gameId))
            throw new ArgumentException("GameId must be non-empty.", nameof(gameId));

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        if (season is < 1 or > 4)
            throw new ArgumentOutOfRangeException(nameof(season), "Season must be between 1 and 4.");

        ArgumentNullException.ThrowIfNull(affectedRegionIds, nameof(affectedRegionIds));

        if (yieldMultiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(yieldMultiplier), "Yield multiplier must be non-negative.");

        var previousSeason = GetSeasonFromMonth(previousDate.Month);
        var currentSeason = GetSeasonFromMonth(currentDate.Month);
        if (previousSeason == currentSeason)
            return;

        if (season != currentSeason)
            throw new ArgumentOutOfRangeException(nameof(season), $"Season must match currentDate quarter: expected {currentSeason}.");

        var evt = new DomainEvent(
            Type: SanguoSeasonEventApplied.EventType,
            Source: nameof(SanguoEconomyManager),
            Data: JsonElementEventData.FromObject(new SanguoSeasonEventApplied(
                GameId: gameId,
                Year: currentDate.Year,
                Season: season,
                AffectedRegionIds: affectedRegionIds,
                YieldMultiplier: yieldMultiplier,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId
            )),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        );

        await _bus.PublishAsync(evt);
    }

    private static int GetSeasonFromMonth(int month)
    {
        if (month is < 1 or > 12)
            throw new ArgumentOutOfRangeException(nameof(month), "Month must be between 1 and 12.");

        return ((month - 1) / 3) + 1;
    }

    private MoneyValue CalculateMonthlyIncome(ISanguoPlayerView player, IReadOnlyDictionary<string, City> citiesById)
    {
        ArgumentNullException.ThrowIfNull(player, nameof(player));

        var adjustment = _activeSeasonYieldAdjustment;
        var totalMinorUnits = 0L;
        foreach (var cityId in player.OwnedCityIds)
        {
            if (!citiesById.TryGetValue(cityId, out var city))
                throw new InvalidOperationException($"Owned city id not found: {cityId}");

            var toll = city.BaseToll;
            if (adjustment is not null && adjustment.AffectedRegionIds.Contains(city.RegionId))
            {
                toll = city.GetToll(multiplier: adjustment.YieldMultiplier, rules: SanguoEconomyRules.Default);
            }

            totalMinorUnits = checked(totalMinorUnits + toll.MinorUnits);
        }

        return new MoneyValue(totalMinorUnits);
    }
}
