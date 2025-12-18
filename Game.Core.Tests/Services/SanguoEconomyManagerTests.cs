using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class SanguoEconomyManagerTests
{
    [Fact]
    public void Constructor_WhenBusIsNull_ThrowsArgumentNullException()
    {
        Action act = () => _ = new SanguoEconomyManager(null!);
        act.Should().Throw<ArgumentNullException>().WithParameterName("bus");
    }

    [Fact]
    public void PublishMonthSettlementIfBoundary_WhenMonthUnchanged_DoesNotPublish()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        economy.PublishMonthSettlementIfBoundary(
            gameId: "game-1",
            previousDate: new DateTime(1, 1, 1),
            currentDate: new DateTime(1, 1, 2),
            settlements: Array.Empty<PlayerSettlement>(),
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);

        bus.Published.Should().BeEmpty();
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void PublishMonthSettlementIfBoundary_WhenGameIdIsEmpty_ThrowsArgumentException(string? gameId)
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        Action act = () => economy.PublishMonthSettlementIfBoundary(
            gameId: gameId!,
            previousDate: new DateTime(1, 1, 31),
            currentDate: new DateTime(1, 2, 1),
            settlements: Array.Empty<PlayerSettlement>(),
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);

        act.Should().Throw<ArgumentException>().WithParameterName("gameId");
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void PublishMonthSettlementIfBoundary_WhenCorrelationIdIsEmpty_ThrowsArgumentException(string? correlationId)
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        Action act = () => economy.PublishMonthSettlementIfBoundary(
            gameId: "game-1",
            previousDate: new DateTime(1, 1, 31),
            currentDate: new DateTime(1, 2, 1),
            settlements: Array.Empty<PlayerSettlement>(),
            correlationId: correlationId!,
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);

        act.Should().Throw<ArgumentException>().WithParameterName("correlationId");
    }

    [Fact]
    public void PublishMonthSettlementIfBoundary_WhenMonthChanged_PublishesMonthSettled()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        economy.PublishMonthSettlementIfBoundary(
            gameId: "game-1",
            previousDate: new DateTime(1, 1, 31),
            currentDate: new DateTime(1, 2, 1),
            settlements: Array.Empty<PlayerSettlement>(),
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);

        bus.Published.Should().ContainSingle(e => e.Type == SanguoMonthSettled.EventType);
        var evt = bus.Published[0];
        evt.Source.Should().Be(nameof(SanguoEconomyManager));
        evt.Data.Should().BeOfType<JsonElementEventData>();

        var payload = ((JsonElementEventData)evt.Data!).Value;
        payload.GetProperty("GameId").GetString().Should().Be("game-1");
        payload.GetProperty("Year").GetInt32().Should().Be(1);
        payload.GetProperty("Month").GetInt32().Should().Be(1);
        payload.GetProperty("CorrelationId").GetString().Should().Be("corr-1");
        payload.GetProperty("CausationId").GetString().Should().Be("cmd-1");
        payload.GetProperty("PlayerSettlements").GetArrayLength().Should().Be(0);
    }

    [Fact]
    public void PublishSeasonEventIfBoundary_WhenMonthUnchanged_DoesNotPublish()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        economy.PublishSeasonEventIfBoundary(
            gameId: "game-1",
            previousDate: new DateTime(1, 1, 1),
            currentDate: new DateTime(1, 1, 2),
            season: 1,
            affectedRegionIds: Array.Empty<string>(),
            yieldMultiplier: 1.0m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);

        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public void PublishSeasonEventIfBoundary_WhenMonthChanged_PublishesSeasonEventApplied()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        economy.PublishSeasonEventIfBoundary(
            gameId: "game-1",
            previousDate: new DateTime(1, 1, 31),
            currentDate: new DateTime(1, 2, 1),
            season: 2,
            affectedRegionIds: new[] { "r1", "r2" },
            yieldMultiplier: 0.8m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);

        bus.Published.Should().ContainSingle(e => e.Type == SanguoSeasonEventApplied.EventType);
        var evt = bus.Published[0];
        evt.Source.Should().Be(nameof(SanguoEconomyManager));
        evt.Data.Should().BeOfType<JsonElementEventData>();

        var payload = ((JsonElementEventData)evt.Data!).Value;
        payload.GetProperty("GameId").GetString().Should().Be("game-1");
        payload.GetProperty("Year").GetInt32().Should().Be(1);
        payload.GetProperty("Season").GetInt32().Should().Be(2);
        payload.GetProperty("YieldMultiplier").GetDecimal().Should().Be(0.8m);
        payload.GetProperty("AffectedRegionIds").GetArrayLength().Should().Be(2);
    }

    [Fact]
    public void PublishSeasonEventIfBoundary_WhenSeasonOutOfRange_ThrowsArgumentOutOfRangeException()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        Action act = () => economy.PublishSeasonEventIfBoundary(
            gameId: "game-1",
            previousDate: new DateTime(1, 1, 31),
            currentDate: new DateTime(1, 2, 1),
            season: 0,
            affectedRegionIds: Array.Empty<string>(),
            yieldMultiplier: 1.0m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);

        act.Should().Throw<ArgumentOutOfRangeException>().WithParameterName("season");
    }

    [Fact]
    public void PublishSeasonEventIfBoundary_WhenYieldMultiplierNegative_ThrowsArgumentOutOfRangeException()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        Action act = () => economy.PublishSeasonEventIfBoundary(
            gameId: "game-1",
            previousDate: new DateTime(1, 1, 31),
            currentDate: new DateTime(1, 2, 1),
            season: 1,
            affectedRegionIds: Array.Empty<string>(),
            yieldMultiplier: -0.1m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);

        act.Should().Throw<ArgumentOutOfRangeException>().WithParameterName("yieldMultiplier");
    }

    [Fact]
    public void PublishYearlyPriceAdjustmentIfBoundary_WhenYearUnchanged_DoesNotPublish()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var cities = new[]
        {
            new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10)),
        };

        economy.PublishYearlyPriceAdjustmentIfBoundary(
            gameId: "game-1",
            previousDate: new DateTime(1, 12, 31),
            currentDate: new DateTime(1, 1, 1),
            cities: cities,
            yearlyMultiplier: 1.10m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);

        bus.Published.Should().BeEmpty();
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void PublishYearlyPriceAdjustmentIfBoundary_WhenGameIdIsEmpty_ThrowsArgumentException(string? gameId)
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        Action act = () => economy.PublishYearlyPriceAdjustmentIfBoundary(
            gameId: gameId!,
            previousDate: new DateTime(1, 12, 31),
            currentDate: new DateTime(2, 1, 1),
            cities: Array.Empty<City>(),
            yearlyMultiplier: 1.10m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);

        act.Should().Throw<ArgumentException>().WithParameterName("gameId");
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void PublishYearlyPriceAdjustmentIfBoundary_WhenCorrelationIdIsEmpty_ThrowsArgumentException(string? correlationId)
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        Action act = () => economy.PublishYearlyPriceAdjustmentIfBoundary(
            gameId: "game-1",
            previousDate: new DateTime(1, 12, 31),
            currentDate: new DateTime(2, 1, 1),
            cities: Array.Empty<City>(),
            yearlyMultiplier: 1.10m,
            correlationId: correlationId!,
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);

        act.Should().Throw<ArgumentException>().WithParameterName("correlationId");
    }

    [Fact]
    public void PublishYearlyPriceAdjustmentIfBoundary_WhenYearChanged_PublishesPriceAdjustedPerCity()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var cities = new[]
        {
            new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10)),
            new City("c2", "City2", "r2", Money.FromMajorUnits(200), Money.FromMajorUnits(20)),
        };

        economy.PublishYearlyPriceAdjustmentIfBoundary(
            gameId: "game-1",
            previousDate: new DateTime(1, 12, 31),
            currentDate: new DateTime(2, 1, 1),
            cities: cities,
            yearlyMultiplier: 1.10m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);

        bus.Published.Should().HaveCount(2);
        bus.Published.Should().OnlyContain(e => e.Type == SanguoYearPriceAdjusted.EventType);

        foreach (var evt in bus.Published)
        {
            evt.Source.Should().Be(nameof(SanguoEconomyManager));
            evt.Data.Should().BeOfType<JsonElementEventData>();
            var payload = ((JsonElementEventData)evt.Data!).Value;
            payload.GetProperty("GameId").GetString().Should().Be("game-1");
            payload.GetProperty("Year").GetInt32().Should().Be(1);
            payload.GetProperty("CorrelationId").GetString().Should().Be("corr-1");
            payload.GetProperty("CausationId").GetString().Should().Be("cmd-1");
        }
    }

    [Fact]
    public void CalculateMonthSettlements_SumsBaseTollOfOwnedCities()
    {
        var bus = NullEventBus.Instance;
        var economy = new SanguoEconomyManager(bus);

        var cities = new Dictionary<string, City>
        {
            ["c1"] = new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10)),
            ["c2"] = new City("c2", "City2", "r1", Money.FromMajorUnits(200), Money.FromMajorUnits(15)),
        };

        var player = new PlayerView(
            playerId: "p1",
            ownedCityIds: new[] { "c1", "c2" });

        var settlements = economy.CalculateMonthSettlements(new[] { player }, cities);
        settlements.Should().ContainSingle();
        settlements[0].PlayerId.Should().Be("p1");
        settlements[0].AmountDelta.Should().Be(25m);
    }

    [Fact]
    public void CalculateMonthSettlements_WhenPlayersIsNull_ThrowsArgumentNullException()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        Action act = () => _ = economy.CalculateMonthSettlements(
            players: null!,
            citiesById: new Dictionary<string, City>());

        act.Should().Throw<ArgumentNullException>().WithParameterName("players");
    }

    [Fact]
    public void CalculateMonthSettlements_WhenCitiesByIdIsNull_ThrowsArgumentNullException()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        var player = new PlayerView(playerId: "p1", ownedCityIds: Array.Empty<string>());

        Action act = () => _ = economy.CalculateMonthSettlements(
            players: new[] { player },
            citiesById: null!);

        act.Should().Throw<ArgumentNullException>().WithParameterName("citiesById");
    }

    [Fact]
    public void CalculateMonthSettlements_WhenPlayerEliminated_IsSkipped()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        var cities = new Dictionary<string, City>
        {
            ["c1"] = new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10)),
        };

        var eliminated = new PlayerView(
            playerId: "p1",
            ownedCityIds: new[] { "c1" },
            isEliminated: true);

        var settlements = economy.CalculateMonthSettlements(new[] { eliminated }, cities);
        settlements.Should().BeEmpty();
    }

    [Fact]
    public void CalculateMonthSettlements_WhenOwnedCityMissing_ThrowsInvalidOperationException()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        var cities = new Dictionary<string, City>();
        var player = new PlayerView(
            playerId: "p1",
            ownedCityIds: new[] { "missing-city" });

        Action act = () => _ = economy.CalculateMonthSettlements(new[] { player }, cities);
        act.Should().Throw<InvalidOperationException>()
            .WithMessage("Owned city id not found:*");
    }

    [Fact]
    public void CalculateYearlyPriceAdjustments_ComputesNewPriceUsingMultiplier()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        var cities = new[]
        {
            new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10)),
        };

        var adjustments = economy.CalculateYearlyPriceAdjustments(cities, yearlyMultiplier: 1.10m);
        adjustments.Should().ContainSingle();
        adjustments[0].CityId.Should().Be("c1");
        adjustments[0].OldPrice.ToDecimal().Should().Be(100m);
        adjustments[0].NewPrice.ToDecimal().Should().Be(110m);
    }

    [Fact]
    public void CalculateYearlyPriceAdjustments_WhenMultiplierIsNegative_ThrowsArgumentOutOfRangeException()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        Action act = () => _ = economy.CalculateYearlyPriceAdjustments(
            cities: Array.Empty<City>(),
            yearlyMultiplier: -0.1m);

        act.Should().Throw<ArgumentOutOfRangeException>()
            .WithParameterName("yearlyMultiplier");
    }

    private sealed class PlayerView : ISanguoPlayerView
    {
        public PlayerView(string playerId, IReadOnlyCollection<string> ownedCityIds, bool isEliminated = false)
        {
            PlayerId = playerId;
            OwnedCityIds = ownedCityIds;
            IsEliminated = isEliminated;
        }

        public string PlayerId { get; }
        public Money Money => Money.Zero;
        public int PositionIndex => 0;
        public IReadOnlyCollection<string> OwnedCityIds { get; }
        public bool IsEliminated { get; }
    }

    private sealed class CapturingEventBus : IEventBus
    {
        public List<DomainEvent> Published { get; } = new();

        public Task PublishAsync(DomainEvent evt)
        {
            Published.Add(evt);
            return Task.CompletedTask;
        }

        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => new DummySubscription();

        private sealed class DummySubscription : IDisposable
        {
            public void Dispose()
            {
            }
        }
    }
}
