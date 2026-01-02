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

public sealed class SanguoAiExecutionTests
{
    // ACC:T11.4
    // ACC:T11.5
    [Fact]
    public async Task ShouldRollDiceMoveAndBuyCity_WhenAiLandsOnUnownedCityAndHasFunds()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var gameId = "game-1";
        var humanId = "p1";
        var aiId = "ai-1";
        var correlationId = "corr-10";

        var rules = SanguoEconomyRules.Default;
        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromMajorUnits(100), baseToll: Money.FromMajorUnits(10), positionIndex: 3);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };

        var human = new SanguoPlayer(playerId: humanId, money: 200m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: aiId, money: 200m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { human, ai }, citiesById: cities);
        var treasury = new SanguoTreasury();

        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            rng: new FixedRng(3),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: gameId,
            playerOrder: new[] { humanId, aiId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId,
            causationId: null);

        await mgr.AdvanceTurnAsync(correlationId, causationId: "cmd-advance");

        bus.Published.Should().Contain(e => e.Type == SanguoDiceRolled.EventType);
        bus.Published.Should().Contain(e => e.Type == SanguoTokenMoved.EventType);
        bus.Published.Should().Contain(e => e.Type == SanguoCityBought.EventType);
        ai.PositionIndex.Should().Be(3);
        ai.OwnsCityId(city.Id).Should().BeTrue();

        var cityBought = bus.Published.Last(e => e.Type == SanguoCityBought.EventType);
        var payload = GetJsonPayload(cityBought);
        payload.GetProperty("GameId").GetString().Should().Be(gameId);
        payload.GetProperty("BuyerId").GetString().Should().Be(aiId);
        payload.GetProperty("CityId").GetString().Should().Be(city.Id);
        payload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);
    }

    // ACC:T11.4
    // ACC:T11.5
    [Fact]
    public async Task ShouldPayToll_WhenAiLandsOnOwnedCity()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var gameId = "game-1";
        var humanId = "p1";
        var aiId = "ai-1";
        var correlationId = "corr-11";

        var rules = SanguoEconomyRules.Default;
        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromMajorUnits(1), baseToll: Money.FromMajorUnits(10), positionIndex: 3);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };

        var human = new SanguoPlayer(playerId: humanId, money: 200m, positionIndex: 0, economyRules: rules);
        human.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var ai = new SanguoPlayer(playerId: aiId, money: 200m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { human, ai }, citiesById: cities);
        var treasury = new SanguoTreasury();

        var aiMoneyBefore = ai.Money.ToDecimal();
        var humanMoneyBefore = human.Money.ToDecimal();

        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            rng: new FixedRng(3),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: gameId,
            playerOrder: new[] { humanId, aiId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId,
            causationId: null);

        await mgr.AdvanceTurnAsync(correlationId, causationId: "cmd-advance");

        bus.Published.Should().Contain(e => e.Type == SanguoCityTollPaid.EventType);
        ai.Money.ToDecimal().Should().Be(aiMoneyBefore - 10m);
        human.Money.ToDecimal().Should().Be(humanMoneyBefore + 10m);

        var tollPaid = bus.Published.Last(e => e.Type == SanguoCityTollPaid.EventType);
        var payload = GetJsonPayload(tollPaid);
        payload.GetProperty("GameId").GetString().Should().Be(gameId);
        payload.GetProperty("PayerId").GetString().Should().Be(aiId);
        payload.GetProperty("OwnerId").GetString().Should().Be(humanId);
        payload.GetProperty("CityId").GetString().Should().Be(city.Id);
        payload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);
    }

    // ACC:T11.7
    [Fact]
    public async Task ShouldBeStableAcrossManyAiTurns_WhenInsufficientFundsToBuy()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var gameId = "game-1";
        var humanId = "p1";
        var aiId = "ai-1";
        var correlationId = "corr-12";

        var rules = SanguoEconomyRules.Default;
        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromMajorUnits(100), baseToll: Money.FromMajorUnits(10), positionIndex: 1);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };

        var human = new SanguoPlayer(playerId: humanId, money: 200m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: aiId, money: 0m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { human, ai }, citiesById: cities);
        var treasury = new SanguoTreasury();

        var rng = new FixedRng(1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1);
        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            rng: rng,
            totalPositionsHint: 2);

        await mgr.StartNewGameAsync(
            gameId: gameId,
            playerOrder: new[] { humanId, aiId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId,
            causationId: null);

        var humanMoneyBefore = human.Money;
        var humanPositionBefore = human.PositionIndex;
        var humanOwnedBefore = human.OwnedCityIds.ToArray();

        for (var i = 0; i < 20; i++)
        {
            await mgr.AdvanceTurnAsync(correlationId, causationId: $"cmd-{i}-to-ai");
            await mgr.AdvanceTurnAsync(correlationId, causationId: $"cmd-{i}-to-human");
        }

        bus.Published.Count(e => e.Type == SanguoAiDecisionMade.EventType).Should().BeGreaterOrEqualTo(20);
        bus.Published.Should().NotContain(e => e.Type == SanguoCityBought.EventType, "AI has 0 money so it must never buy");
        bus.Published.Should().NotContain(e => e.Type == SanguoCityTollPaid.EventType);
        ai.OwnsCityId(city.Id).Should().BeFalse();

        human.Money.Should().Be(humanMoneyBefore, "AI must not mutate other players unless via explicit rule entrypoints");
        human.PositionIndex.Should().Be(humanPositionBefore);
        human.OwnedCityIds.Should().BeEquivalentTo(humanOwnedBefore);
    }

    // ACC:T11.7
    [Fact]
    public async Task ShouldBeStableAcrossManyAiTurns_WhenNoCitiesAreBuyable()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var gameId = "game-1";
        var humanId = "p1";
        var aiId = "ai-1";
        var correlationId = "corr-13";

        var rules = SanguoEconomyRules.Default;
        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromMajorUnits(1), baseToll: Money.FromMajorUnits(0), positionIndex: 1);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };

        var human = new SanguoPlayer(playerId: humanId, money: 200m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: aiId, money: 200m, positionIndex: 0, economyRules: rules);
        ai.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var boardState = new SanguoBoardState(players: new[] { human, ai }, citiesById: cities);
        var treasury = new SanguoTreasury();

        var rng = new FixedRng(1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1);
        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            rng: rng,
            totalPositionsHint: 2);

        await mgr.StartNewGameAsync(
            gameId: gameId,
            playerOrder: new[] { humanId, aiId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId,
            causationId: null);

        var humanMoneyBefore = human.Money;
        var humanPositionBefore = human.PositionIndex;
        var humanOwnedBefore = human.OwnedCityIds.ToArray();

        for (var i = 0; i < 20; i++)
        {
            await mgr.AdvanceTurnAsync(correlationId, causationId: $"cmd-{i}-to-ai");
            await mgr.AdvanceTurnAsync(correlationId, causationId: $"cmd-{i}-to-human");
        }

        bus.Published.Count(e => e.Type == SanguoAiDecisionMade.EventType).Should().BeGreaterOrEqualTo(20);
        bus.Published.Should().NotContain(e => e.Type == SanguoCityBought.EventType, "AI already owns all cities so it must never buy again");
        bus.Published.Should().NotContain(e => e.Type == SanguoCityTollPaid.EventType);
        ai.OwnsCityId(city.Id).Should().BeTrue();

        human.Money.Should().Be(humanMoneyBefore, "AI must not mutate other players unless via explicit rule entrypoints");
        human.PositionIndex.Should().Be(humanPositionBefore);
        human.OwnedCityIds.Should().BeEquivalentTo(humanOwnedBefore);
    }

    private static JsonElement GetJsonPayload(DomainEvent evt)
    {
        evt.Data.Should().BeOfType<JsonElementEventData>();
        return ((JsonElementEventData)evt.Data!).Value;
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
