using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Tasks;

public class Task6RedTests
{
    [Fact]
    public void StartNewGame_ThenAdvanceTurn_PublishesTurnEventsAndRotatesActivePlayer()
    {
        var turnManagerType = Type.GetType("Game.Core.Services.SanguoTurnManager, Game.Core");
        turnManagerType.Should().NotBeNull(
            "Task 6 requires a turn manager; implement Game.Core.Services.SanguoTurnManager to manage turn rotation and publish turn events");

        var bus = new CapturingEventBus();

        var ctor = turnManagerType!.GetConstructor(new[] { typeof(IEventBus) });
        ctor.Should().NotBeNull("SanguoTurnManager should take IEventBus as a required dependency");

        var mgr = ctor!.Invoke(new object[] { bus });

        var startMethod = turnManagerType.GetMethod(
            "StartNewGame",
            new[]
            {
                typeof(string),          // gameId
                typeof(string[]),        // playerOrder
                typeof(int),             // year
                typeof(int),             // month
                typeof(int),             // day
                typeof(string),          // correlationId
                typeof(string),          // causationId (nullable by convention; reflection uses string)
            });
        startMethod.Should().NotBeNull(
            "SanguoTurnManager.StartNewGame should exist with signature (string gameId, string[] playerOrder, int year, int month, int day, string correlationId, string? causationId)");

        var advanceMethod = turnManagerType.GetMethod(
            "AdvanceTurn",
            new[] { typeof(string), typeof(string) });
        advanceMethod.Should().NotBeNull(
            "SanguoTurnManager.AdvanceTurn should exist with signature (string correlationId, string? causationId)");

        var gameId = "game-1";
        var playerOrder = new[] { "p1", "p2" };
        var correlationId = "corr-1";
        string? causationId = null;

        startMethod!.Invoke(mgr, new object?[] { gameId, playerOrder, 1, 1, 1, correlationId, causationId });

        bus.Published.Should().ContainSingle("starting a game should publish a turn.started event");
        var started = bus.Published[0];
        started.Type.Should().Be(SanguoGameTurnStarted.EventType);
        started.Source.Should().Be("SanguoTurnManager");
        started.Data.Should().BeOfType<JsonElementEventData>();

        var startedPayload = ((JsonElementEventData)started.Data!).Value;
        startedPayload.GetProperty("GameId").GetString().Should().Be(gameId);
        startedPayload.GetProperty("TurnNumber").GetInt32().Should().Be(1);
        startedPayload.GetProperty("ActivePlayerId").GetString().Should().Be("p1");
        startedPayload.GetProperty("Year").GetInt32().Should().Be(1);
        startedPayload.GetProperty("Month").GetInt32().Should().Be(1);
        startedPayload.GetProperty("Day").GetInt32().Should().Be(1);
        startedPayload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);

        var causationJson = startedPayload.GetProperty("CausationId");
        causationJson.ValueKind.Should().Be(JsonValueKind.Null);

        var advanceCommandId = Guid.NewGuid().ToString("N");
        advanceMethod!.Invoke(mgr, new object?[] { correlationId, advanceCommandId });

        bus.Published.Should().HaveCount(4, "advance should publish turn.ended, turn.advanced, and next turn.started");

        var ended = bus.Published[1];
        ended.Type.Should().Be(SanguoGameTurnEnded.EventType);
        ended.Source.Should().Be("SanguoTurnManager");
        ended.Data.Should().BeOfType<JsonElementEventData>();

        var endedPayload = ((JsonElementEventData)ended.Data!).Value;
        endedPayload.GetProperty("GameId").GetString().Should().Be(gameId);
        endedPayload.GetProperty("TurnNumber").GetInt32().Should().Be(1);
        endedPayload.GetProperty("ActivePlayerId").GetString().Should().Be("p1");
        endedPayload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);
        endedPayload.GetProperty("CausationId").GetString().Should().Be(advanceCommandId);

        var advanced = bus.Published[2];
        advanced.Type.Should().Be(SanguoGameTurnAdvanced.EventType);
        advanced.Source.Should().Be("SanguoTurnManager");
        advanced.Data.Should().BeOfType<JsonElementEventData>();

        var advancedPayload = ((JsonElementEventData)advanced.Data!).Value;
        advancedPayload.GetProperty("GameId").GetString().Should().Be(gameId);
        advancedPayload.GetProperty("TurnNumber").GetInt32().Should().Be(2);
        advancedPayload.GetProperty("ActivePlayerId").GetString().Should().Be("p2");
        advancedPayload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);
        advancedPayload.GetProperty("CausationId").GetString().Should().Be(advanceCommandId);

        var nextStarted = bus.Published[3];
        nextStarted.Type.Should().Be(SanguoGameTurnStarted.EventType);
        nextStarted.Source.Should().Be("SanguoTurnManager");
        nextStarted.Data.Should().BeOfType<JsonElementEventData>();

        var nextStartedPayload = ((JsonElementEventData)nextStarted.Data!).Value;
        nextStartedPayload.GetProperty("GameId").GetString().Should().Be(gameId);
        nextStartedPayload.GetProperty("TurnNumber").GetInt32().Should().Be(2);
        nextStartedPayload.GetProperty("ActivePlayerId").GetString().Should().Be("p2");
        nextStartedPayload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);
        nextStartedPayload.GetProperty("CausationId").GetString().Should().Be(advanceCommandId);
    }

    [Fact]
    public void StartNewGame_WithEmptyGameId_ShouldThrowArgumentException()
    {
        var mgr = new SanguoTurnManager(NullEventBus.Instance);

        Action act = () => mgr.StartNewGame(
            gameId: " ",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr",
            causationId: null);

        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void StartNewGame_WithNullPlayerOrder_ShouldThrowArgumentNullException()
    {
        var mgr = new SanguoTurnManager(NullEventBus.Instance);

        Action act = () => mgr.StartNewGame(
            gameId: "g1",
            playerOrder: null!,
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr",
            causationId: null);

        act.Should().Throw<ArgumentNullException>();
    }

    [Fact]
    public void StartNewGame_WithEmptyPlayerOrder_ShouldThrowArgumentException()
    {
        var mgr = new SanguoTurnManager(NullEventBus.Instance);

        Action act = () => mgr.StartNewGame(
            gameId: "g1",
            playerOrder: Array.Empty<string>(),
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr",
            causationId: null);

        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void StartNewGame_WithEmptyPlayerId_ShouldThrowArgumentException()
    {
        var mgr = new SanguoTurnManager(NullEventBus.Instance);

        Action act = () => mgr.StartNewGame(
            gameId: "g1",
            playerOrder: new[] { "p1", " " },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr",
            causationId: null);

        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void StartNewGame_WithDuplicatePlayerIds_ShouldThrowArgumentException()
    {
        var mgr = new SanguoTurnManager(NullEventBus.Instance);

        Action act = () => mgr.StartNewGame(
            gameId: "g1",
            playerOrder: new[] { "p1", "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr",
            causationId: null);

        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void StartNewGame_WithEmptyCorrelationId_ShouldThrowArgumentException()
    {
        var mgr = new SanguoTurnManager(NullEventBus.Instance);

        Action act = () => mgr.StartNewGame(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: " ",
            causationId: null);

        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void AdvanceTurn_BeforeStart_ShouldThrowInvalidOperationException()
    {
        var mgr = new SanguoTurnManager(NullEventBus.Instance);

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
