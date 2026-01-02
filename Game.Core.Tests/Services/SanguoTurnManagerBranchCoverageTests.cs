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

public sealed class SanguoTurnManagerBranchCoverageTests
{
    [Fact]
    public async Task ShouldDeriveTotalPositions_WhenHintIsNotProvided()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var aiId = "ai-1";
        var correlationId = "corr-bc-1";
        var rules = SanguoEconomyRules.Default;

        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c7"] = new City(id: "c7", name: "City7", regionId: "r1", basePrice: Money.FromMajorUnits(1), baseToll: Money.FromMajorUnits(1), positionIndex: 7),
        };

        var ai = new SanguoPlayer(playerId: aiId, money: 200m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { ai }, citiesById: cities);
        var treasury = new SanguoTreasury();

        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            rng: new FixedRng(1),
            totalPositionsHint: 0);

        await mgr.StartNewGameAsync(
            gameId: "game-1",
            playerOrder: new[] { aiId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId,
            causationId: null);

        bus.Published.Should().Contain(e => e.Type == SanguoTokenMoved.EventType);
    }

    [Fact]
    public async Task ShouldNormalizeFromIndex_WhenAiPositionIsBeyondTotalPositionsHint()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var aiId = "ai-1";
        var correlationId = "corr-bc-2";
        var rules = SanguoEconomyRules.Default;

        var cities = new Dictionary<string, City>(StringComparer.Ordinal);
        var ai = new SanguoPlayer(playerId: aiId, money: 200m, positionIndex: 12, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { ai }, citiesById: cities);
        var treasury = new SanguoTreasury();

        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            rng: new FixedRng(3),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "game-1",
            playerOrder: new[] { aiId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId,
            causationId: null);

        var moved = bus.Published.Last(e => e.Type == SanguoTokenMoved.EventType);
        var payload = GetJsonPayload(moved);
        payload.GetProperty("FromIndex").GetInt32().Should().Be(2);
        payload.GetProperty("ToIndex").GetInt32().Should().Be(5);
        payload.GetProperty("PassedStart").GetBoolean().Should().BeFalse();
    }

    [Fact]
    public async Task ShouldSetPassedStart_WhenAiWrapsAround()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var aiId = "ai-1";
        var correlationId = "corr-bc-3";
        var rules = SanguoEconomyRules.Default;

        var cities = new Dictionary<string, City>(StringComparer.Ordinal);
        var ai = new SanguoPlayer(playerId: aiId, money: 200m, positionIndex: 8, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { ai }, citiesById: cities);
        var treasury = new SanguoTreasury();

        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            rng: new FixedRng(3),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "game-1",
            playerOrder: new[] { aiId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId,
            causationId: null);

        var moved = bus.Published.Last(e => e.Type == SanguoTokenMoved.EventType);
        var payload = GetJsonPayload(moved);
        payload.GetProperty("FromIndex").GetInt32().Should().Be(8);
        payload.GetProperty("ToIndex").GetInt32().Should().Be(1);
        payload.GetProperty("PassedStart").GetBoolean().Should().BeTrue();
    }

    [Fact]
    public async Task ShouldNotAttemptEconomy_WhenLandingOnCityOwnedBySelf()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var aiId = "ai-1";
        var correlationId = "corr-bc-4";
        var rules = SanguoEconomyRules.Default;

        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromMajorUnits(1), baseToll: Money.FromMajorUnits(1), positionIndex: 3);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };

        var ai = new SanguoPlayer(playerId: aiId, money: 200m, positionIndex: 0, economyRules: rules);
        ai.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var boardState = new SanguoBoardState(players: new[] { ai }, citiesById: cities);
        var treasury = new SanguoTreasury();

        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            rng: new FixedRng(3),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "game-1",
            playerOrder: new[] { aiId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId,
            causationId: null);

        bus.Published.Should().Contain(e => e.Type == SanguoDiceRolled.EventType);
        bus.Published.Should().Contain(e => e.Type == SanguoTokenMoved.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoCityBought.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoCityTollPaid.EventType);
    }

    [Fact]
    public async Task ShouldReturnEarlyFromAiExecution_WhenAiIsEliminated()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var aiId = "ai-1";
        var correlationId = "corr-bc-5";
        var rules = SanguoEconomyRules.Default;

        var owner = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: aiId, money: 0m, positionIndex: 0, economyRules: rules);
        var treasury = new SanguoTreasury();

        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromMajorUnits(1), baseToll: Money.FromMajorUnits(10), positionIndex: 0);
        ai.TryPayTollTo(owner, city, tollMultiplier: 1.0m, treasury: treasury).Should().BeTrue();
        ai.IsEliminated.Should().BeTrue();

        var boardState = new SanguoBoardState(players: new[] { ai }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            aiDecisionPolicy: new AlwaysRollDicePolicy(),
            rng: new FixedRng(1),
            totalPositionsHint: 2);

        await mgr.StartNewGameAsync(
            gameId: "game-1",
            playerOrder: new[] { aiId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId,
            causationId: null);

        bus.Published.Should().Contain(e => e.Type == SanguoAiDecisionMade.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoDiceRolled.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoTokenMoved.EventType);
    }

    private static JsonElement GetJsonPayload(DomainEvent evt)
    {
        evt.Data.Should().BeOfType<JsonElementEventData>();
        return ((JsonElementEventData)evt.Data!).Value;
    }

    private sealed class AlwaysRollDicePolicy : ISanguoAiDecisionPolicy
    {
        public SanguoAiDecision Decide(ISanguoPlayerView self) => new(SanguoAiDecisionType.RollDice);
    }

    private sealed class FixedRng : IRandomNumberGenerator
    {
        private readonly Queue<int> _nextInts;

        public FixedRng(params int[] nextInts)
        {
            _nextInts = new Queue<int>(nextInts ?? Array.Empty<int>());
        }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            if (_nextInts.Count == 0)
                return minInclusive;

            var value = _nextInts.Dequeue();
            if (value < minInclusive)
                return minInclusive;
            if (value >= maxExclusive)
                return maxExclusive - 1;
            return value;
        }

        public double NextDouble() => 0.0;
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

