using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Game.Core.Utilities;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task16YearEndPriceTests
{
    // ACC:T16.1
    [Fact]
    [Trait("acceptance", "ACC:T16.1")]
    public void ShouldApplyYearlyAdjustmentToBasePriceAndToll_WhenUnitTestingWithFixedRng()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        var cities = new List<City>
        {
            new(
                id: "c1",
                name: "City1",
                regionId: "r1",
                basePrice: Money.FromDecimal(100m),
                baseToll: Money.FromDecimal(10m),
                positionIndex: 0)
        };

        var rng = new FixedRng(intSequence: Array.Empty<int>(), doubleSequence: new[] { 0.1, 0.2 });
        var updated = economy.ApplyYearlyPriceAdjustment(cities, rng);

        updated.Should().HaveCount(1);
        updated[0].Id.Should().Be("c1");
        updated[0].BasePrice.Should().Be(Money.FromDecimal(60m)); // 100 * (0.5 + 0.1)
        updated[0].BaseToll.Should().Be(Money.FromDecimal(7m)); // 10 * (0.5 + 0.2)
    }

    // ACC:T16.2
    [Fact]
    [Trait("acceptance", "ACC:T16.2")]
    public async Task ShouldApplyYearlyAdjustmentOnceAndWriteToBoardState_WhenCrossingYearBoundary()
    {
        var published = new List<DomainEvent>();
        var bus = new InMemoryEventBus();
        using var sub = bus.Subscribe(evt =>
        {
            published.Add(evt);
            return Task.CompletedTask;
        });

        var rules = SanguoEconomyRules.Default;
        var players = new List<SanguoPlayer>
        {
            new(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules)
        };

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new(
                id: "c1",
                name: "City1",
                regionId: "r1",
                basePrice: Money.FromDecimal(100m),
                baseToll: Money.FromDecimal(10m),
                positionIndex: 0)
        };

        var boardState = new SanguoBoardState(players, citiesById);
        var treasury = new SanguoTreasury();
        var economy = new SanguoEconomyManager(bus);

        var rng = new FixedRng(intSequence: Array.Empty<int>(), doubleSequence: new[] { 0.99, 0.1, 0.2 });
        var turnManager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: rng,
            quarterEnvironmentEventTriggerChance: 0.0);

        await turnManager.StartNewGameAsync(
            gameId: "game-1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 12,
            day: 30,
            correlationId: "corr-1",
            causationId: null);

        var before = boardState.GetCitiesSnapshot()["c1"];
        await turnManager.AdvanceTurnAsync(correlationId: "corr-2", causationId: null);
        var after = boardState.GetCitiesSnapshot()["c1"];

        after.BasePrice.Should().Be(Money.FromDecimal(60m));
        after.BaseToll.Should().Be(Money.FromDecimal(7m));
        after.Name.Should().Be(before.Name);
        after.RegionId.Should().Be(before.RegionId);
        after.PositionIndex.Should().Be(before.PositionIndex);

        var yearEvents = published
            .Where(e => e.Type == SanguoYearPriceAdjusted.EventType)
            .ToArray();

        yearEvents.Should().HaveCount(1);
        yearEvents[0].Data.Should().BeOfType<JsonElementEventData>();
        var payload = ((JsonElementEventData)yearEvents[0].Data!).Value;
        payload.GetProperty("GameId").GetString().Should().Be("game-1");
        payload.GetProperty("Year").GetInt32().Should().Be(2);
        payload.GetProperty("CityId").GetString().Should().Be("c1");
        payload.GetProperty("OldPrice").GetDecimal().Should().Be(before.BasePrice.ToDecimal());
        payload.GetProperty("NewPrice").GetDecimal().Should().Be(after.BasePrice.ToDecimal());

        await turnManager.AdvanceTurnAsync(correlationId: "corr-3", causationId: null);
        var afterSecondAdvance = boardState.GetCitiesSnapshot()["c1"];
        afterSecondAdvance.BasePrice.Should().Be(after.BasePrice);
        afterSecondAdvance.BaseToll.Should().Be(after.BaseToll);

        published.Count(e => e.Type == SanguoYearPriceAdjusted.EventType).Should().Be(1);
    }

    // ACC:T16.3
    [Fact]
    [Trait("acceptance", "ACC:T16.3")]
    public void ShouldBeDeterministic_WhenApplyingYearlyAdjustmentWithSameRngSequence()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        var input = new List<City>
        {
            new(
                id: "c1",
                name: "city-1",
                regionId: "r1",
                basePrice: Money.FromDecimal(100m),
                baseToll: Money.FromDecimal(10m),
                positionIndex: 0)
        };

        var rngA1 = new FixedRng(intSequence: Array.Empty<int>(), doubleSequence: new[] { 0.1, 0.2 });
        var rngA2 = new FixedRng(intSequence: Array.Empty<int>(), doubleSequence: new[] { 0.1, 0.2 });
        var rngB = new FixedRng(intSequence: Array.Empty<int>(), doubleSequence: new[] { 0.9, 0.8 });

        var resultA1 = economy.ApplyYearlyPriceAdjustment(input, rngA1);
        var resultA2 = economy.ApplyYearlyPriceAdjustment(input, rngA2);
        resultA1.Should().BeEquivalentTo(resultA2, "same RNG sequence must lead to deterministic yearly adjustment results");

        var resultB = economy.ApplyYearlyPriceAdjustment(input, rngB);
        (resultB[0].BasePrice != resultA1[0].BasePrice || resultB[0].BaseToll != resultA1[0].BaseToll)
            .Should().BeTrue("different RNG input should be able to produce different price/toll results");
    }

    // ACC:T16.4
    [Fact]
    [Trait("acceptance", "ACC:T16.4")]
    public void ShouldOnlyChangeBasePriceAndBaseToll_WhenApplyingYearlyUpdatesToBoardState()
    {
        var rules = SanguoEconomyRules.Default;
        var players = new List<SanguoPlayer>
        {
            new(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules),
            new(playerId: "p2", money: 1000m, positionIndex: 0, economyRules: rules)
        };

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromDecimal(100m), baseToll: Money.FromDecimal(10m), positionIndex: 0),
            ["c2"] = new(id: "c2", name: "City2", regionId: "r2", basePrice: Money.FromDecimal(200m), baseToll: Money.FromDecimal(20m), positionIndex: 1),
        };

        var boardState = new SanguoBoardState(players, citiesById);
        boardState.TryBuyCity(buyerId: "p1", cityId: "c1", priceMultiplier: 1.0m).Should().BeTrue();

        boardState.TryGetOwnerOfCity("c1", out var ownerBefore).Should().BeTrue();
        ownerBefore!.PlayerId.Should().Be("p1");

        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        var updates = economy.ApplyYearlyPriceAdjustment(citiesById.Values.OrderBy(c => c.Id, StringComparer.Ordinal).ToList(), new FixedRng(Array.Empty<int>(), new[] { 0.1, 0.2, 0.3, 0.4 }));
        boardState.ApplyCityEconomyUpdates(updates);

        boardState.TryGetOwnerOfCity("c1", out var ownerAfter).Should().BeTrue();
        ownerAfter!.PlayerId.Should().Be("p1");

        var c1After = boardState.GetCitiesSnapshot()["c1"];
        c1After.Name.Should().Be("City1");
        c1After.RegionId.Should().Be("r1");
        c1After.PositionIndex.Should().Be(0);
    }

    [Fact]
    public void ShouldRejectDuplicateCityIds_WhenApplyingCityEconomyUpdates()
    {
        var rules = SanguoEconomyRules.Default;
        var players = new List<SanguoPlayer>
        {
            new(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules),
        };

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromDecimal(100m), baseToll: Money.FromDecimal(10m), positionIndex: 0),
            ["c2"] = new(id: "c2", name: "City2", regionId: "r2", basePrice: Money.FromDecimal(200m), baseToll: Money.FromDecimal(20m), positionIndex: 1),
        };

        var boardState = new SanguoBoardState(players, citiesById);
        var duplicated = new List<City>
        {
            citiesById["c1"],
            citiesById["c1"],
        };

        Action act = () => boardState.ApplyCityEconomyUpdates(duplicated);
        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void ShouldRejectMissingExistingCityId_WhenApplyingCityEconomyUpdates()
    {
        var rules = SanguoEconomyRules.Default;
        var players = new List<SanguoPlayer>
        {
            new(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules),
        };

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromDecimal(100m), baseToll: Money.FromDecimal(10m), positionIndex: 0),
            ["c2"] = new(id: "c2", name: "City2", regionId: "r2", basePrice: Money.FromDecimal(200m), baseToll: Money.FromDecimal(20m), positionIndex: 1),
        };

        var boardState = new SanguoBoardState(players, citiesById);
        var wrongSet = new List<City>
        {
            new(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromDecimal(101m), baseToll: Money.FromDecimal(10m), positionIndex: 0),
            new(id: "cx", name: "CityX", regionId: "r2", basePrice: Money.FromDecimal(200m), baseToll: Money.FromDecimal(20m), positionIndex: 1),
        };

        Action act = () => boardState.ApplyCityEconomyUpdates(wrongSet);
        act.Should().Throw<InvalidOperationException>()
            .WithMessage("*Updated city id not found*");
    }

    [Fact]
    public void ShouldRejectNonEconomyFieldMismatch_WhenApplyingCityEconomyUpdates()
    {
        var rules = SanguoEconomyRules.Default;
        var players = new List<SanguoPlayer>
        {
            new(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules),
        };

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromDecimal(100m), baseToll: Money.FromDecimal(10m), positionIndex: 0),
        };

        var boardState = new SanguoBoardState(players, citiesById);
        var mismatched = new List<City>
        {
            new(id: "c1", name: "City1-mismatch", regionId: "r1", basePrice: Money.FromDecimal(101m), baseToll: Money.FromDecimal(11m), positionIndex: 0),
        };

        Action act = () => boardState.ApplyCityEconomyUpdates(mismatched);
        act.Should().Throw<InvalidOperationException>()
            .WithMessage("*name mismatch*");
    }

    [Fact]
    public void ShouldCapPriceAndTollAtMoneyMax_WhenApplyingYearlyAdjustmentWouldOverflow()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        var cities = new List<City>
        {
            new(
                id: "c1",
                name: "city-1",
                regionId: "r1",
                basePrice: Money.FromMajorUnits(Money.MaxMajorUnits - 1),
                baseToll: Money.FromMajorUnits(Money.MaxMajorUnits - 1),
                positionIndex: 0)
        };

        var rng = new FixedRng(intSequence: Array.Empty<int>(), doubleSequence: new[] { 1.0 });
        var result = economy.ApplyYearlyPriceAdjustment(cities, rng);

        result.Should().HaveCount(1);
        result[0].BasePrice.Should().Be(Money.FromMajorUnits(Money.MaxMajorUnits));
        result[0].BaseToll.Should().Be(Money.FromMajorUnits(Money.MaxMajorUnits));
    }

    [Fact]
    public void ShouldThrowInvalidOperationException_WhenApplyingYearlyAdjustmentAndRngReturnsOutOfRangeDouble()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        var cities = new List<City>
        {
            new(
                id: "c1",
                name: "city-1",
                regionId: "r1",
                basePrice: Money.FromDecimal(100m),
                baseToll: Money.FromDecimal(10m),
                positionIndex: 0)
        };

        var rng = new OutOfRangeDoubleRng();
        Action act = () => _ = economy.ApplyYearlyPriceAdjustment(cities, rng);
        act.Should().Throw<InvalidOperationException>();
    }

    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenCalculatingYearlyAdjustmentsWithRngAndMultiplierIsNegative()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        var cities = new List<City>
        {
            new(
                id: "c1",
                name: "city-1",
                regionId: "r1",
                basePrice: Money.FromDecimal(100m),
                baseToll: Money.FromDecimal(10m),
                positionIndex: 0)
        };

        Action act = () => _ = economy.CalculateYearlyPriceAdjustments(cities, yearlyMultiplier: -0.01m, rng: new FixedRng(Array.Empty<int>(), new[] { 0.1 }));
        act.Should().Throw<ArgumentOutOfRangeException>()
            .WithParameterName("yearlyMultiplier");
    }

    [Fact]
    public void ShouldThrowArgumentNullException_WhenApplyingYearlyAdjustmentAndRngIsNull()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        var cities = new List<City>
        {
            new(
                id: "c1",
                name: "city-1",
                regionId: "r1",
                basePrice: Money.FromDecimal(100m),
                baseToll: Money.FromDecimal(10m),
                positionIndex: 0)
        };

        Action act = () => _ = economy.ApplyYearlyPriceAdjustment(cities, rng: null!);
        act.Should().Throw<ArgumentNullException>()
            .WithParameterName("rng");
    }

    private sealed class FixedRng : IRandomNumberGenerator
    {
        private readonly int[] _ints;
        private readonly double[] _doubles;
        private int _intIndex;
        private int _doubleIndex;

        public FixedRng(int[] intSequence, double[] doubleSequence)
        {
            _ints = intSequence ?? Array.Empty<int>();
            _doubles = doubleSequence ?? Array.Empty<double>();
        }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            if (_ints.Length == 0)
                return minInclusive;

            var value = _ints[_intIndex % _ints.Length];
            _intIndex++;
            return Math.Clamp(value, minInclusive, maxExclusive - 1);
        }

        public double NextDouble()
        {
            if (_doubles.Length == 0)
                return 0.0;

            var value = _doubles[_doubleIndex % _doubles.Length];
            _doubleIndex++;
            return Math.Clamp(value, 0.0, 1.0);
        }
    }

    private sealed class OutOfRangeDoubleRng : IRandomNumberGenerator
    {
        public int NextInt(int minInclusive, int maxExclusive) => minInclusive;

        public double NextDouble() => -0.1;
    }
}
