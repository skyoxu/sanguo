using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Game.Core.Utilities;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class SanguoTurnActionFlowTests
{
    // Acceptance anchors:
    // ACC:T17.10
    [Fact]
    public async Task ExecuteHumanRollDice_ForHumanTurn_ShouldPublishDiceBeforeTokenMove()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10), positionIndex: 2),
        };

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 500m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: "ai-1", money: 500m, positionIndex: 0, economyRules: rules);
        var players = new[] { p1, ai };

        var boardState = new SanguoBoardState(players: players, citiesById: cities);
        var treasury = new SanguoTreasury();

        var rng = new FixedRng(fixedNextInt: 6, fixedNextDouble: 1.0);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: rng,
            totalPositionsHint: 10,
            quarterEnvironmentEventTriggerChance: 0.0);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-turn", causationId: "ui.hud.dice.roll");

        var published = bus.Published.Skip(before).ToList();
        published.Should().Contain(e => e.Type == SanguoDiceRolled.EventType);
        published.Should().Contain(e => e.Type == SanguoTokenMoved.EventType);

        var diceIndex = published.FindIndex(e => e.Type == SanguoDiceRolled.EventType);
        var movedIndex = published.FindIndex(e => e.Type == SanguoTokenMoved.EventType);
        diceIndex.Should().BeGreaterOrEqualTo(0);
        movedIndex.Should().BeGreaterOrEqualTo(0);
        diceIndex.Should().BeLessThan(movedIndex);

        var moved = published.Where(e => e.Type == SanguoTokenMoved.EventType).ToList();
        moved.Should().HaveCount(1);
        var movedPayload = ((JsonElementEventData)moved[0].Data!).Value;
        movedPayload.GetProperty("PlayerId").GetString().Should().Be("p1");
        movedPayload.GetProperty("CorrelationId").GetString().Should().Be("corr-turn");
        movedPayload.GetProperty("CausationId").GetString().Should().Be("ui.hud.dice.roll");
    }

    [Fact]
    public async Task ExecuteHumanRollDice_WhenActivePlayerIsAi_ShouldNotPublishDiceOrTokenMoved()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var ai = new SanguoPlayer(playerId: "ai-1", money: 100m, positionIndex: 0, economyRules: rules);
        var p1 = new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { ai, p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            aiDecisionPolicy: new AlwaysSkipAiDecisionPolicy(),
            rng: new FixedRng(fixedNextInt: 6, fixedNextDouble: 1.0),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "ai-1", "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-human", causationId: "ui.hud.dice.roll");
        var published = bus.Published.Skip(before).ToList();
        published.Should().NotContain(e => e.Type == SanguoDiceRolled.EventType);
        published.Should().NotContain(e => e.Type == SanguoTokenMoved.EventType);
    }

    [Fact]
    public async Task ExecuteHumanRollDice_WhenTotalPositionsIsUnknown_ShouldNotPublishDiceOrTokenMoved()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 6, fixedNextDouble: 1.0),
            totalPositionsHint: 0);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-human", causationId: "ui.hud.dice.roll");
        var published = bus.Published.Skip(before).ToList();
        published.Should().NotContain(e => e.Type == SanguoDiceRolled.EventType);
        published.Should().NotContain(e => e.Type == SanguoTokenMoved.EventType);
    }

    [Fact]
    public async Task ExecuteHumanRollDice_WhenHumanLandsOnOwnedCity_ShouldPublishTollPaidAndPlayerStateChanged()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10), positionIndex: 6),
        };

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 50m, positionIndex: 0, economyRules: rules);
        var p2 = new SanguoPlayer(playerId: "p2", money: 0m, positionIndex: 0, economyRules: rules);
        p2.OwnsCityId("c1").Should().BeFalse();
        p2.TryBuyCity(cities["c1"], priceMultiplier: 1.0m).Should().BeFalse("p2 does not have enough money to buy in this setup");
        p2 = new SanguoPlayer(playerId: "p2", money: 200m, positionIndex: 0, economyRules: rules);
        p2.TryBuyCity(cities["c1"], priceMultiplier: 1.0m).Should().BeTrue();

        var boardState = new SanguoBoardState(players: new[] { p1, p2 }, citiesById: cities);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 6, fixedNextDouble: 1.0),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "p2" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-human", causationId: "ui.hud.dice.roll");
        var published = bus.Published.Skip(before).ToList();

        published.Should().Contain(e => e.Type == SanguoCityTollPaid.EventType);
        published.Should().Contain(e => e.Type == SanguoPlayerStateChanged.EventType && ((JsonElementEventData)e.Data!).Value.GetProperty("PlayerId").GetString() == "p1");
        published.Should().Contain(e => e.Type == SanguoPlayerStateChanged.EventType && ((JsonElementEventData)e.Data!).Value.GetProperty("PlayerId").GetString() == "p2");
    }

    [Fact]
    public async Task ExecuteHumanRollDice_WhenHumanLandsOnOwnCity_ShouldNotPublishTollPaidOrCityBought()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City1", "r1", Money.FromMajorUnits(10), Money.FromMajorUnits(1), positionIndex: 6),
        };

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0, economyRules: rules);
        p1.TryBuyCity(cities["c1"], priceMultiplier: 1.0m).Should().BeTrue();

        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: cities);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 6, fixedNextDouble: 1.0),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-human", causationId: "ui.hud.dice.roll");
        var published = bus.Published.Skip(before).ToList();

        published.Should().NotContain(e => e.Type == SanguoCityTollPaid.EventType);
        published.Should().NotContain(e => e.Type == SanguoCityBought.EventType);
    }

    [Fact]
    public async Task ExecuteHumanRollDice_WhenNoCityAtLandingPosition_ShouldNotPublishCityEvents()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10), positionIndex: 9),
        };

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: cities);

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 1, fixedNextDouble: 1.0),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-human", causationId: "ui.hud.dice.roll");
        var published = bus.Published.Skip(before).ToList();

        published.Should().Contain(e => e.Type == SanguoDiceRolled.EventType);
        published.Should().Contain(e => e.Type == SanguoTokenMoved.EventType);
        published.Should().NotContain(e => e.Type == SanguoCityTollPaid.EventType);
        published.Should().NotContain(e => e.Type == SanguoCityBought.EventType);
    }

    [Fact]
    public async Task ExecuteHumanRollDice_WhenRngOutOfRange_ShouldClampToD6()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 99, fixedNextDouble: 1.0),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-human", causationId: "ui.hud.dice.roll");
        var published = bus.Published.Skip(before).ToList();

        var dice = published.Single(e => e.Type == SanguoDiceRolled.EventType);
        var payload = ((JsonElementEventData)dice.Data!).Value;
        payload.GetProperty("Value").GetInt32().Should().Be(6);
    }

    [Fact]
    public async Task ExecuteHumanRollDice_WhenPlayerPositionExceedsTotalPositions_ShouldNormalizeFromIndex()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 12, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 1, fixedNextDouble: 1.0),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-human", causationId: "ui.hud.dice.roll");
        var published = bus.Published.Skip(before).ToList();

        var moved = published.Single(e => e.Type == SanguoTokenMoved.EventType);
        var payload = ((JsonElementEventData)moved.Data!).Value;
        payload.GetProperty("FromIndex").GetInt32().Should().Be(2);
        payload.GetProperty("ToIndex").GetInt32().Should().Be(3);
    }

    [Fact]
    public async Task ExecuteHumanRollDice_WhenHumanInsufficientFunds_ShouldNotPublishCityBought()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10), positionIndex: 6),
        };

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: cities);

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 6, fixedNextDouble: 1.0),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-human", causationId: "ui.hud.dice.roll");
        var published = bus.Published.Skip(before).ToList();

        published.Should().Contain(e => e.Type == SanguoDiceRolled.EventType);
        published.Should().Contain(e => e.Type == SanguoTokenMoved.EventType);
        published.Should().NotContain(e => e.Type == SanguoCityBought.EventType);
        published.Should().NotContain(e => e.Type == SanguoCityTollPaid.EventType);
    }

    [Fact]
    public async Task ExecuteHumanRollDice_WhenHumanAlreadyEliminated_ShouldEndGameAndSkipDice()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var city = new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10), positionIndex: 0);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { ["c1"] = city };

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 1m, positionIndex: 0, economyRules: rules);
        var p2 = new SanguoPlayer(playerId: "p2", money: 0m, positionIndex: 0, economyRules: rules);
        p1.TryPayTollTo(p2, city, tollMultiplier: 1.0m, treasury: new SanguoTreasury()).Should().BeTrue();
        p1.IsEliminated.Should().BeTrue();

        var boardState = new SanguoBoardState(players: new[] { p1, p2 }, citiesById: cities);

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 6, fixedNextDouble: 1.0),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "p2" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-human", causationId: "ui.hud.dice.roll");
        var published = bus.Published.Skip(before).ToList();

        published.Should().Contain(e => e.Type == SanguoGameEnded.EventType);
        published.Should().NotContain(e => e.Type == SanguoDiceRolled.EventType);
        published.Should().NotContain(e => e.Type == SanguoTokenMoved.EventType);
    }

    [Fact]
    public async Task ExecuteHumanRollDice_WhenGameNotStarted_ShouldThrowInvalidOperationException()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));
        var mgr = new SanguoTurnManager(bus, economy, boardState, new SanguoTreasury());

        Func<Task> act = async () => await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr", causationId: null);
        await act.Should().ThrowAsync<InvalidOperationException>();
    }

    [Fact]
    public async Task ExecuteHumanRollDice_WhenCorrelationIdBlank_ShouldThrowArgumentException()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 6, fixedNextDouble: 1.0),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        Func<Task> act = async () => await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "  ", causationId: null);
        await act.Should().ThrowAsync<ArgumentException>();
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

    private sealed class FixedRng : IRandomNumberGenerator
    {
        private readonly int _fixedNextInt;
        private readonly double _fixedNextDouble;

        public FixedRng(int fixedNextInt, double fixedNextDouble)
        {
            _fixedNextInt = fixedNextInt;
            _fixedNextDouble = fixedNextDouble;
        }

        public int NextInt(int minInclusive, int maxExclusive) => _fixedNextInt;

        public double NextDouble() => _fixedNextDouble;
    }

    private sealed class AlwaysSkipAiDecisionPolicy : ISanguoAiDecisionPolicy
    {
        public SanguoAiDecision Decide(ISanguoPlayerView self)
        {
            return new SanguoAiDecision(
                DecisionType: SanguoAiDecisionType.Skip,
                DecisionNode: "ut.ai.skip",
                FromState: "Skip",
                ToState: "Skip",
                Reason: "unit_test");
        }
    }
}
