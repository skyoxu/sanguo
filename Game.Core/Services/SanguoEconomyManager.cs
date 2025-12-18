using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;

namespace Game.Core.Services;

public sealed class SanguoEconomyManager
{
    private readonly IEventBus _bus;

    public SanguoEconomyManager(IEventBus bus)
    {
        _bus = bus ?? throw new ArgumentNullException(nameof(bus));
    }

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

    public void PublishMonthSettlementIfBoundary(
        string gameId,
        DateTime previousDate,
        DateTime currentDate,
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

        _bus.PublishAsync(evt).GetAwaiter().GetResult();
    }

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

    public void PublishYearlyPriceAdjustmentIfBoundary(
        string gameId,
        DateTime previousDate,
        DateTime currentDate,
        IReadOnlyList<City> cities,
        decimal yearlyMultiplier,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt
    )
    {
        if (string.IsNullOrWhiteSpace(gameId))
            throw new ArgumentException("GameId must be non-empty.", nameof(gameId));

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        ArgumentNullException.ThrowIfNull(cities, nameof(cities));

        if (previousDate.Year == currentDate.Year)
            return;

        var adjustments = CalculateYearlyPriceAdjustments(cities, yearlyMultiplier);
        foreach (var (cityId, oldPrice, newPrice) in adjustments)
        {
            var evt = new DomainEvent(
                Type: SanguoYearPriceAdjusted.EventType,
                Source: nameof(SanguoEconomyManager),
                Data: JsonElementEventData.FromObject(new SanguoYearPriceAdjusted(
                    GameId: gameId,
                    Year: previousDate.Year,
                    CityId: cityId,
                    OldPrice: oldPrice.ToDecimal(),
                    NewPrice: newPrice.ToDecimal(),
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: DateTime.UtcNow,
                Id: Guid.NewGuid().ToString("N")
            );

            _bus.PublishAsync(evt).GetAwaiter().GetResult();
        }
    }

    public void PublishSeasonEventIfBoundary(
        string gameId,
        DateTime previousDate,
        DateTime currentDate,
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

        if (previousDate.Year == currentDate.Year && previousDate.Month == currentDate.Month)
            return;

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

        _bus.PublishAsync(evt).GetAwaiter().GetResult();
    }

    private static MoneyValue CalculateMonthlyIncome(ISanguoPlayerView player, IReadOnlyDictionary<string, City> citiesById)
    {
        ArgumentNullException.ThrowIfNull(player, nameof(player));

        var totalMinorUnits = 0L;
        foreach (var cityId in player.OwnedCityIds)
        {
            if (!citiesById.TryGetValue(cityId, out var city))
                throw new InvalidOperationException($"Owned city id not found: {cityId}");

            totalMinorUnits = checked(totalMinorUnits + city.BaseToll.MinorUnits);
        }

        return new MoneyValue(totalMinorUnits);
    }
}

