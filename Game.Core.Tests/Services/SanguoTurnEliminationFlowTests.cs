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

public sealed class SanguoTurnEliminationFlowTests
{
    // ACC:T26.5
    [Fact]
    public async Task ShouldPublishTollAndEndGame_WhenExecuteHumanRollDiceAndLandingOnOwnedCityWithInsufficientFunds()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var city = new City(
            id: "c-toll",
            name: "TollCity",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(100),
            baseToll: Money.FromMajorUnits(20),
            positionIndex: 3);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };

        var rules = SanguoEconomyRules.Default;
        var human = new SanguoPlayer(playerId: "p1", money: 5m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: "ai-1", money: 500m, positionIndex: 0, economyRules: rules);
        ai.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var treasury = new SanguoTreasury();
        var boardState = new SanguoBoardState(players: new[] { human, ai }, citiesById: cities);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new FixedRng(fixedNextInt: 3),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-human", causationId: "ui.hud.dice.roll");
        var published = bus.Published.Skip(before).ToList();

        published.Should().NotContain(e => e.Type == SanguoGameTurnAdvanced.EventType);
        published.Should().Contain(e => e.Type == SanguoDiceRolled.EventType);
        published.Should().Contain(e => e.Type == SanguoTokenMoved.EventType);
        published.Should().Contain(e => e.Type == SanguoCityTollPaid.EventType);
        published.Last().Type.Should().Be(SanguoGameEnded.EventType);

        human.IsEliminated.Should().BeTrue();
        human.Money.Should().Be(Money.Zero);

        var tollEvt = published.Single(e => e.Type == SanguoCityTollPaid.EventType);
        tollEvt.Data.Should().BeOfType<JsonElementEventData>();
        var tollPayload = ((JsonElementEventData)tollEvt.Data!).Value;
        tollPayload.GetProperty("PayerId").GetString().Should().Be("p1");
        tollPayload.GetProperty("OwnerId").GetString().Should().Be("ai-1");
        tollPayload.GetProperty("CityId").GetString().Should().Be("c-toll");
        tollPayload.GetProperty("Amount").GetDecimal().Should().Be(5m);
    }

    // ACC:T26.6
    [Fact]
    public async Task ShouldPruneAndAdvanceToNextHuman_WhenAdvanceTurnAfterActiveAiIsEliminatedDuringItsTurn()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var city = new City(
            id: "c-toll",
            name: "TollCity",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(100),
            baseToll: Money.FromMajorUnits(10),
            positionIndex: 2);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 500m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: "ai-1", money: 5m, positionIndex: 0, economyRules: rules);
        var p2 = new SanguoPlayer(playerId: "p2", money: 0m, positionIndex: 0, economyRules: rules);

        p1.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var treasury = new SanguoTreasury();
        var boardState = new SanguoBoardState(players: new[] { p1, ai, p2 }, citiesById: cities);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new FixedRng(fixedNextInt: 2),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1", "p2" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        // End p1 turn -> start AI turn; AI should roll and be eliminated by toll in the same call.
        await mgr.AdvanceTurnAsync(correlationId: "corr-to-ai", causationId: "cmd.advance");
        ai.IsEliminated.Should().BeTrue();

        // End AI turn -> prune eliminated AI -> advance to next human (p2).
        await mgr.AdvanceTurnAsync(correlationId: "corr-end-ai", causationId: "runtime.ai.auto.advance");

        var lastAdvanced = bus.Published.Last(e => e.Type == SanguoGameTurnAdvanced.EventType);
        lastAdvanced.Data.Should().BeOfType<JsonElementEventData>();
        JsonElement advancedPayload = ((JsonElementEventData)lastAdvanced.Data!).Value;
        advancedPayload.GetProperty("ActivePlayerId").GetString().Should().Be("p2");

        // Sanity: never end the whole game for AI elimination.
        bus.Published.Should().NotContain(e => e.Type == SanguoGameEnded.EventType && IsHumanEliminatedReason(e));
    }

    private static bool IsHumanEliminatedReason(DomainEvent evt)
    {
        if (evt.Data is not JsonElementEventData data)
            return false;

        if (!data.Value.TryGetProperty("EndReason", out var reason))
            return false;

        return string.Equals(reason.GetString(), SanguoGameEnded.ReasonPlayerBankrupt, StringComparison.Ordinal);
    }

    private sealed class FixedRng : IRandomNumberGenerator
    {
        private readonly int _fixedNextInt;

        public FixedRng(int fixedNextInt)
        {
            _fixedNextInt = fixedNextInt;
        }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            if (_fixedNextInt < minInclusive)
                return minInclusive;
            if (_fixedNextInt >= maxExclusive)
                return maxExclusive - 1;
            return _fixedNextInt;
        }

        public double NextDouble() => 0.0;
    }

    private sealed class RecordingEventBus : IEventBus
    {
        public List<DomainEvent> Published { get; } = new();

        public Task PublishAsync(DomainEvent evt)
        {
            Published.Add(evt);
            return Task.CompletedTask;
        }

        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => new NoopDisposable();

        private sealed class NoopDisposable : IDisposable
        {
            public void Dispose() { }
        }
    }
}
