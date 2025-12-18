using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class SanguoTurnManagerTests
{
    [Fact]
    public void StartNewGame_ThenAdvanceTurn_PublishesTurnEventsAndRotatesActivePlayer()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(bus, economy);

        var gameId = "game-1";
        var playerOrder = new[] { "p1", "p2" };
        var correlationId = "corr-1";
        string? startCausationId = null;

        mgr.StartNewGame(gameId, playerOrder, 1, 1, 1, correlationId, startCausationId);

        bus.Published.Should().ContainSingle("starting a game should publish a turn.started event");
        var started = bus.Published[0];
        started.Type.Should().Be(SanguoGameTurnStarted.EventType);
        started.Source.Should().Be(nameof(SanguoTurnManager));
        started.Data.Should().BeOfType<JsonElementEventData>();

        var startedPayload = ((JsonElementEventData)started.Data!).Value;
        startedPayload.GetProperty("GameId").GetString().Should().Be(gameId);
        startedPayload.GetProperty("TurnNumber").GetInt32().Should().Be(1);
        startedPayload.GetProperty("ActivePlayerId").GetString().Should().Be("p1");
        startedPayload.GetProperty("Year").GetInt32().Should().Be(1);
        startedPayload.GetProperty("Month").GetInt32().Should().Be(1);
        startedPayload.GetProperty("Day").GetInt32().Should().Be(1);
        startedPayload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);
        startedPayload.GetProperty("CausationId").ValueKind.Should().Be(JsonValueKind.Null);

        var advanceCommandId = Guid.NewGuid().ToString("N");
        mgr.AdvanceTurn(correlationId, advanceCommandId);

        bus.Published.Should().HaveCount(4, "advance should publish turn.ended, turn.advanced, and next turn.started");

        var ended = bus.Published[1];
        ended.Type.Should().Be(SanguoGameTurnEnded.EventType);
        ended.Source.Should().Be(nameof(SanguoTurnManager));
        ended.Data.Should().BeOfType<JsonElementEventData>();

        var endedPayload = ((JsonElementEventData)ended.Data!).Value;
        endedPayload.GetProperty("GameId").GetString().Should().Be(gameId);
        endedPayload.GetProperty("TurnNumber").GetInt32().Should().Be(1);
        endedPayload.GetProperty("ActivePlayerId").GetString().Should().Be("p1");
        endedPayload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);
        endedPayload.GetProperty("CausationId").GetString().Should().Be(advanceCommandId);

        var advanced = bus.Published[2];
        advanced.Type.Should().Be(SanguoGameTurnAdvanced.EventType);
        advanced.Source.Should().Be(nameof(SanguoTurnManager));
        advanced.Data.Should().BeOfType<JsonElementEventData>();

        var advancedPayload = ((JsonElementEventData)advanced.Data!).Value;
        advancedPayload.GetProperty("GameId").GetString().Should().Be(gameId);
        advancedPayload.GetProperty("TurnNumber").GetInt32().Should().Be(2);
        advancedPayload.GetProperty("ActivePlayerId").GetString().Should().Be("p2");
        advancedPayload.GetProperty("Year").GetInt32().Should().Be(1);
        advancedPayload.GetProperty("Month").GetInt32().Should().Be(1);
        advancedPayload.GetProperty("Day").GetInt32().Should().Be(2);
        advancedPayload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);
        advancedPayload.GetProperty("CausationId").GetString().Should().Be(advanceCommandId);

        var nextStarted = bus.Published[3];
        nextStarted.Type.Should().Be(SanguoGameTurnStarted.EventType);
        nextStarted.Source.Should().Be(nameof(SanguoTurnManager));
        nextStarted.Data.Should().BeOfType<JsonElementEventData>();

        var nextStartedPayload = ((JsonElementEventData)nextStarted.Data!).Value;
        nextStartedPayload.GetProperty("GameId").GetString().Should().Be(gameId);
        nextStartedPayload.GetProperty("TurnNumber").GetInt32().Should().Be(2);
        nextStartedPayload.GetProperty("ActivePlayerId").GetString().Should().Be("p2");
        nextStartedPayload.GetProperty("Year").GetInt32().Should().Be(1);
        nextStartedPayload.GetProperty("Month").GetInt32().Should().Be(1);
        nextStartedPayload.GetProperty("Day").GetInt32().Should().Be(2);
        nextStartedPayload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);
        nextStartedPayload.GetProperty("CausationId").GetString().Should().Be(advanceCommandId);
    }

    [Fact]
    public void AdvanceTurn_WhenMonthBoundaryReached_PublishesMonthSettledEvent()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(bus, economy);

        var gameId = "game-1";
        var playerOrder = new[] { "p1", "p2" };
        var correlationId = "corr-1";

        mgr.StartNewGame(
            gameId: gameId,
            playerOrder: playerOrder,
            year: 1,
            month: 1,
            day: 31,
            correlationId: correlationId,
            causationId: null);

        mgr.AdvanceTurn(correlationId, causationId: "cmd-advance");

        bus.Published.Should().Contain(
            e => e.Type == SanguoMonthSettled.EventType,
            "crossing a month boundary should trigger month settlement");

        var settled = bus.Published.Find(e => e.Type == SanguoMonthSettled.EventType)!;
        settled.Data.Should().BeOfType<JsonElementEventData>();

        var payload = ((JsonElementEventData)settled.Data!).Value;
        payload.GetProperty("GameId").GetString().Should().Be(gameId);
        payload.GetProperty("Year").GetInt32().Should().Be(1);
        payload.GetProperty("Month").GetInt32().Should().Be(1);
        payload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);
        payload.GetProperty("CausationId").GetString().Should().Be("cmd-advance");
        payload.GetProperty("PlayerSettlements").GetArrayLength().Should().Be(0);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void StartNewGame_WhenGameIdIsNullOrWhitespace_ThrowsArgumentException(string? gameId)
    {
        var mgr = new SanguoTurnManager(NullEventBus.Instance, new SanguoEconomyManager(NullEventBus.Instance));

        Action act = () => mgr.StartNewGame(
            gameId: gameId!,
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr",
            causationId: null);

        act.Should().Throw<ArgumentException>()
            .WithParameterName("gameId");
    }

    [Fact]
    public void StartNewGame_WhenPlayerOrderIsNull_ThrowsArgumentNullException()
    {
        var mgr = new SanguoTurnManager(NullEventBus.Instance, new SanguoEconomyManager(NullEventBus.Instance));

        Action act = () => mgr.StartNewGame(
            gameId: "g1",
            playerOrder: null!,
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr",
            causationId: null);

        act.Should().Throw<ArgumentNullException>()
            .WithParameterName("playerOrder");
    }

    [Fact]
    public void StartNewGame_WhenPlayerOrderIsEmpty_ThrowsArgumentException()
    {
        var mgr = new SanguoTurnManager(NullEventBus.Instance, new SanguoEconomyManager(NullEventBus.Instance));

        Action act = () => mgr.StartNewGame(
            gameId: "g1",
            playerOrder: Array.Empty<string>(),
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr",
            causationId: null);

        act.Should().Throw<ArgumentException>()
            .WithParameterName("playerOrder");
    }

    [Fact]
    public void StartNewGame_WhenPlayerOrderContainsEmptyPlayerId_ThrowsArgumentException()
    {
        var mgr = new SanguoTurnManager(NullEventBus.Instance, new SanguoEconomyManager(NullEventBus.Instance));

        Action act = () => mgr.StartNewGame(
            gameId: "g1",
            playerOrder: new[] { "p1", " " },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr",
            causationId: null);

        act.Should().Throw<ArgumentException>()
            .WithParameterName("playerOrder");
    }

    [Fact]
    public void StartNewGame_WhenPlayerOrderContainsDuplicatePlayerIds_ThrowsArgumentException()
    {
        var mgr = new SanguoTurnManager(NullEventBus.Instance, new SanguoEconomyManager(NullEventBus.Instance));

        Action act = () => mgr.StartNewGame(
            gameId: "g1",
            playerOrder: new[] { "p1", "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr",
            causationId: null);

        act.Should().Throw<ArgumentException>()
            .WithParameterName("playerOrder");
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void StartNewGame_WhenCorrelationIdIsNullOrWhitespace_ThrowsArgumentException(string? correlationId)
    {
        var mgr = new SanguoTurnManager(NullEventBus.Instance, new SanguoEconomyManager(NullEventBus.Instance));

        Action act = () => mgr.StartNewGame(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId!,
            causationId: null);

        act.Should().Throw<ArgumentException>()
            .WithParameterName("correlationId");
    }

    [Fact]
    public void AdvanceTurn_BeforeStart_ThrowsInvalidOperationException()
    {
        var mgr = new SanguoTurnManager(NullEventBus.Instance, new SanguoEconomyManager(NullEventBus.Instance));

        Action act = () => mgr.AdvanceTurn("corr", causationId: null);

        act.Should().Throw<InvalidOperationException>();
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
