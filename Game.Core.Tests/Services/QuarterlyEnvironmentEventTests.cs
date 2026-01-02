using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Game.Core.Utilities;
using Xunit;

namespace Game.Core.Tests.Services;

public class QuarterlyEnvironmentEventTests
{
    private static readonly SanguoEconomyRules Rules = SanguoEconomyRules.Default;

    // ACC:T15.4
    [Fact]
    public async Task ShouldAllowDeterministicTriggerAndNoTriggerPaths_WhenCrossingQuarterBoundary()
    {
        var noTriggerRng = DeterministicRandomNumberGenerator.NoTrigger();
        var noTriggerCount = await RunAndCountSeasonEventsAfterCrossingQuarterBoundaryAsync(noTriggerRng, triggerChance: 0.5);

        noTriggerRng.TotalCalls.Should().BeGreaterThan(0, "quarterly trigger evaluation must consult an injected RNG to be testable");
        noTriggerCount.Should().Be(0, "when the trigger roll fails, no seasonal environment event should be emitted");

        var triggerRng = DeterministicRandomNumberGenerator.Trigger();
        var triggerCount = await RunAndCountSeasonEventsAfterCrossingQuarterBoundaryAsync(triggerRng, triggerChance: 0.5);

        triggerRng.TotalCalls.Should().BeGreaterThan(0, "quarterly trigger evaluation must consult an injected RNG to be testable");
        triggerCount.Should().Be(1, "when the trigger roll succeeds, a seasonal environment event should be emitted exactly once at the boundary");

        var alwaysTriggerRng = DeterministicRandomNumberGenerator.NoTrigger();
        var alwaysTriggerCount = await RunAndCountSeasonEventsAfterCrossingQuarterBoundaryAsync(alwaysTriggerRng, triggerChance: 1.0);
        alwaysTriggerRng.TotalCalls.Should().BeGreaterThan(0, "even for triggerChance=1, the injected RNG should still be consulted for testability and reproducibility");
        alwaysTriggerCount.Should().Be(1, "when triggerChance=1, the seasonal environment event should be emitted regardless of the random roll");

        var neverTriggerRng = DeterministicRandomNumberGenerator.Trigger();
        var neverTriggerCount = await RunAndCountSeasonEventsAfterCrossingQuarterBoundaryAsync(neverTriggerRng, triggerChance: 0.0);
        neverTriggerRng.TotalCalls.Should().BeGreaterThan(0, "even for triggerChance=0, the injected RNG should still be consulted for testability and reproducibility");
        neverTriggerCount.Should().Be(0, "when triggerChance=0, the seasonal environment event should not be emitted regardless of the random roll");
    }

    // ACC:T15.5
    [Fact]
    public async Task ShouldNotPublishSeasonEventAndKeepBaselineMonthSettlement_WhenQuarterStartNotTriggered()
    {
        var rng = DeterministicRandomNumberGenerator.NoTrigger();
        var bus = new CapturingEventBus();
        var (boardState, treasury) = CreateBoardStateWithOwnedCities();
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(bus, economy, boardState, treasury, rng: rng, totalPositionsHint: 1);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 3,
            day: 30,
            correlationId: "corr",
            causationId: null);

        await mgr.AdvanceTurnAsync(correlationId: "corr", causationId: "cmd-qstart");

        bus.Published.Should().NotContain(e => e.Type == SanguoSeasonEventApplied.EventType,
            "when the quarter start is evaluated as not triggered, no seasonal event should be emitted");

        for (var i = 0; i < 30; i++)
            await mgr.AdvanceTurnAsync(correlationId: "corr", causationId: $"cmd-apr-{i}");

        var aprilSettlement = TryGetMonthSettledPayload(bus.Published, month: 4);
        aprilSettlement.Should().NotBeNull("April month settlement must be published at the month boundary");

        var aprilAmountDelta = GetSinglePlayerAmountDelta(aprilSettlement!.Value, playerId: "p1");
        var baseline = 10m + 20m;
        aprilAmountDelta.Should().Be(baseline,
            "when the quarterly event does not trigger, month settlement must follow baseline rules with no extra yield adjustment");
    }

    // ACC:T15.6
    [Fact]
    public async Task ShouldAdjustMonthSettlementOnlyForAffectedRegions_WhenQuarterEventTriggered()
    {
        var rng = DeterministicRandomNumberGenerator.Trigger();
        var bus = new CapturingEventBus();
        var (boardState, treasury) = CreateBoardStateWithOwnedCities();
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(bus, economy, boardState, treasury, rng: rng, totalPositionsHint: 1);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 3,
            day: 30,
            correlationId: "corr",
            causationId: null);

        await mgr.AdvanceTurnAsync(correlationId: "corr", causationId: "cmd-qstart");

        var seasonEvent = TryGetSingleSeasonEventPayload(bus.Published);
        seasonEvent.Should().NotBeNull("a seasonal environment event must be emitted when the trigger roll succeeds");

        var seasonPayload = seasonEvent!.Value;
        var yieldMultiplier = seasonPayload.GetProperty("YieldMultiplier").GetDecimal();
        var affectedRegions = seasonPayload.GetProperty("AffectedRegionIds").EnumerateArray()
            .Select(e => e.GetString())
            .Where(s => !string.IsNullOrWhiteSpace(s))
            .Select(s => s!)
            .ToArray();

        yieldMultiplier.Should().BeGreaterThan(0m);
        yieldMultiplier.Should().NotBe(1.0m, "a triggered quarterly environment event must adjust yields");
        affectedRegions.Should().NotBeEmpty("a triggered quarterly environment event must identify affected regions");
        affectedRegions.Should().OnlyContain(id => id == "r1" || id == "r2", "affected regions must come from the board state regions in this test");

        for (var i = 0; i < 30; i++)
            await mgr.AdvanceTurnAsync(correlationId: "corr", causationId: $"cmd-apr-{i}");

        var aprilSettlement = TryGetMonthSettledPayload(bus.Published, month: 4);
        aprilSettlement.Should().NotBeNull("April month settlement must be published at the month boundary");

        var aprilAmountDelta = GetSinglePlayerAmountDelta(aprilSettlement!.Value, playerId: "p1");

        var affected = new HashSet<string>(affectedRegions, StringComparer.Ordinal);
        var expected = (affected.Contains("r1") ? 10m * yieldMultiplier : 10m)
            + (affected.Contains("r2") ? 20m * yieldMultiplier : 20m);

        aprilAmountDelta.Should().Be(expected,
            "yield adjustment must apply only to cities in affected regions; unaffected cities must remain at baseline");
    }

    private static async Task<int> RunAndCountSeasonEventsAfterCrossingQuarterBoundaryAsync(
        DeterministicRandomNumberGenerator rng,
        double triggerChance)
    {
        var bus = new CapturingEventBus();
        var (boardState, treasury) = CreateBoardStateWithOwnedCities();
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            rng: rng,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: triggerChance,
            quarterEnvironmentEventYieldMultiplier: 0.9m);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 3,
            day: 30,
            correlationId: "corr",
            causationId: null);

        await mgr.AdvanceTurnAsync(correlationId: "corr", causationId: "cmd-qstart");

        return bus.Published.Count(e => e.Type == SanguoSeasonEventApplied.EventType);
    }

    private static (SanguoBoardState boardState, SanguoTreasury treasury) CreateBoardStateWithOwnedCities()
    {
        var player = new SanguoPlayer(playerId: "p1", money: 1_000m, positionIndex: 0, economyRules: Rules);

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City(
                id: "c1",
                name: "City1",
                regionId: "r1",
                basePrice: Money.FromMajorUnits(1),
                baseToll: Money.FromMajorUnits(10),
                positionIndex: 0),
            ["c2"] = new City(
                id: "c2",
                name: "City2",
                regionId: "r2",
                basePrice: Money.FromMajorUnits(1),
                baseToll: Money.FromMajorUnits(20),
                positionIndex: 0),
        };

        var boardState = new SanguoBoardState(players: new[] { player }, citiesById: citiesById);
        boardState.TryBuyCity(buyerId: "p1", cityId: "c1", priceMultiplier: 1.0m).Should().BeTrue();
        boardState.TryBuyCity(buyerId: "p1", cityId: "c2", priceMultiplier: 1.0m).Should().BeTrue();

        return (boardState, new SanguoTreasury());
    }

    private static JsonElement? TryGetSingleSeasonEventPayload(IReadOnlyList<DomainEvent> published)
    {
        var evt = published.SingleOrDefault(e => e.Type == SanguoSeasonEventApplied.EventType);
        if (evt is null)
            return null;

        evt.Data.Should().BeOfType<JsonElementEventData>();
        return ((JsonElementEventData)evt.Data!).Value;
    }

    private static JsonElement? TryGetMonthSettledPayload(IReadOnlyList<DomainEvent> published, int month)
    {
        foreach (var evt in published.Where(e => e.Type == SanguoMonthSettled.EventType))
        {
            evt.Data.Should().BeOfType<JsonElementEventData>();
            var payload = ((JsonElementEventData)evt.Data!).Value;
            if (payload.GetProperty("Month").GetInt32() == month)
                return payload;
        }

        return null;
    }

    private static decimal GetSinglePlayerAmountDelta(JsonElement monthSettledPayload, string playerId)
    {
        var settlements = monthSettledPayload.GetProperty("PlayerSettlements").EnumerateArray();
        foreach (var settlement in settlements)
        {
            if (string.Equals(settlement.GetProperty("PlayerId").GetString(), playerId, StringComparison.Ordinal))
                return settlement.GetProperty("AmountDelta").GetDecimal();
        }

        throw new InvalidOperationException($"Player settlement not found for playerId={playerId}.");
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

    private sealed class DeterministicRandomNumberGenerator : IRandomNumberGenerator
    {
        private readonly int _nextIntMode;
        private readonly double _nextDoubleValue;

        private DeterministicRandomNumberGenerator(int nextIntMode, double nextDoubleValue)
        {
            _nextIntMode = nextIntMode;
            _nextDoubleValue = nextDoubleValue;
        }

        public int TotalCalls { get; private set; }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            TotalCalls++;

            if (maxExclusive <= minInclusive)
                throw new ArgumentOutOfRangeException(nameof(maxExclusive), "maxExclusive must be > minInclusive.");

            return _nextIntMode == 0 ? minInclusive : maxExclusive - 1;
        }

        public double NextDouble()
        {
            TotalCalls++;
            return _nextDoubleValue;
        }

        public static DeterministicRandomNumberGenerator Trigger() => new(nextIntMode: 0, nextDoubleValue: 0.0);

        public static DeterministicRandomNumberGenerator NoTrigger() => new(nextIntMode: 1, nextDoubleValue: 0.999999);
    }
}
