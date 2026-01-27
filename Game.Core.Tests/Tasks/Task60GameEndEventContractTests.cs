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
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task60GameEndEventContractTests
{
    [Fact]
    public void ShouldExposeWinnerReasonAndStatsSnapshot_WhenGameEndedEventIsCreated()
    {
        var evt = new SanguoGameEnded(
            "g1",
            "max_turns",
            DateTimeOffset.UtcNow,
            "corr-1",
            null,
            "p1",
            new SanguoGameEndStatsSnapshot(
                10,
                0,
                new[]
                {
                    new SanguoGameEndPlayerStats("p1", 10000m),
                    new SanguoGameEndPlayerStats("ai-1", 5000m),
                }));

        evt.WinnerPlayerId.Should().Be("p1");
        evt.EndReason.Should().Be("max_turns");
        evt.StatsSnapshot.Should().NotBeNull();
        evt.StatsSnapshot!.TurnNumber.Should().Be(10);
        evt.StatsSnapshot.TreasuryMinorUnits.Should().Be(0);
        evt.StatsSnapshot.Players.Should().HaveCount(2);
        evt.StatsSnapshot.Players[0].PlayerId.Should().Be("p1");
        evt.StatsSnapshot.Players[0].Money.Should().Be(10000m);
    }

    // ACC:T60.2
    [Fact]
    public void ShouldSerializeWinnerReasonAndStatsSnapshot_WhenGameEndedEventIsSerialized()
    {
        var evt = new SanguoGameEnded(
            "g1",
            "max_turns",
            DateTimeOffset.UtcNow,
            "corr-1",
            null,
            "p1",
            new SanguoGameEndStatsSnapshot(
                10,
                0,
                new[]
                {
                    new SanguoGameEndPlayerStats("p1", 10000m),
                }));

        var json = JsonSerializer.Serialize(evt);
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;

        root.GetProperty("WinnerPlayerId").GetString().Should().Be("p1");
        root.GetProperty("EndReason").GetString().Should().Be("max_turns");

        var stats = root.GetProperty("StatsSnapshot");
        stats.GetProperty("TurnNumber").GetInt32().Should().Be(10);
        stats.GetProperty("TreasuryMinorUnits").GetInt64().Should().Be(0);

        var players = stats.GetProperty("Players");
        players.ValueKind.Should().Be(JsonValueKind.Array);
        players.GetArrayLength().Should().Be(1);
        players[0].GetProperty("PlayerId").GetString().Should().Be("p1");
        players[0].GetProperty("Money").GetDecimal().Should().Be(10000m);

        SanguoGameEnded.EventType.Should().Be("core.sanguo.game.ended");
    }

    // ACC:T60.1
    [Fact]
    public async Task ShouldPublishGameEndedOnlyWhenGameOverIsTriggered_WhenAdvancingTurns()
    {
        {
            var bus = new RecordingEventBus();
            var economy = new SanguoEconomyManager(bus);

            var city = new City("toll", "TollCity", "r1", Money.Zero, Money.FromMajorUnits(10));
            var cities = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };

            var rules = SanguoEconomyRules.Default;
            var human = new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0, economyRules: rules);
            var ai = new SanguoPlayer(playerId: "ai-1", money: 100m, positionIndex: 0, economyRules: rules);

            var treasury = new SanguoTreasury();
            var boardState = new SanguoBoardState(players: new[] { human, ai }, citiesById: cities);
            var mgr = new SanguoTurnManager(bus: bus, economy: economy, boardState: boardState, treasury: treasury);

            await mgr.StartNewGameAsync(
                gameId: "g1",
                playerOrder: new[] { "p1", "ai-1" },
                year: 1,
                month: 1,
                day: 1,
                correlationId: "corr-start",
                causationId: null);

            var before = bus.Published.Count;
            await mgr.AdvanceTurnAsync(correlationId: "corr-advance-1", causationId: "cmd-advance-1");
            bus.Published.Skip(before).Should().NotContain(e => e.Type == SanguoGameEnded.EventType);
        }

        {
            var bus = new RecordingEventBus();
            var economy = new SanguoEconomyManager(bus);

            var city = new City("toll", "TollCity", "r1", Money.Zero, Money.FromMajorUnits(10));
            var cities = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };

            var rules = SanguoEconomyRules.Default;
            var human = new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0, economyRules: rules);
            var ai = new SanguoPlayer(playerId: "ai-1", money: 5m, positionIndex: 0, economyRules: rules);

            var treasury = new SanguoTreasury();

            ai.TryPayTollTo(human, city, tollMultiplier: 1.0m, treasury: treasury).Should().BeTrue();
            ai.IsEliminated.Should().BeTrue();

            var boardState = new SanguoBoardState(players: new[] { human, ai }, citiesById: cities);
            var mgr = new SanguoTurnManager(bus: bus, economy: economy, boardState: boardState, treasury: treasury);

            await mgr.StartNewGameAsync(
                gameId: "g1",
                playerOrder: new[] { "p1", "ai-1" },
                year: 1,
                month: 1,
                day: 1,
                correlationId: "corr-start",
                causationId: null);

            var before = bus.Published.Count;
            await mgr.AdvanceTurnAsync(correlationId: "corr-advance-2", causationId: "cmd-advance-2");

            var ended = bus.Published.Skip(before).Single(e => e.Type == SanguoGameEnded.EventType);
            ended.Data.Should().BeOfType<JsonElementEventData>();

            var payload = ((JsonElementEventData)ended.Data!).Value;
            payload.GetProperty("EndReason").GetString().Should().Be(SanguoGameEnded.ReasonLastActorStanding);
            payload.GetProperty("WinnerPlayerId").GetString().Should().Be("p1");
        }
    }

    private sealed class RecordingEventBus : IEventBus
    {
        public List<Game.Core.Contracts.DomainEvent> Published { get; } = new();

        public Task PublishAsync(Game.Core.Contracts.DomainEvent evt)
        {
            Published.Add(evt);
            return Task.CompletedTask;
        }

        public IDisposable Subscribe(Func<Game.Core.Contracts.DomainEvent, Task> handler) => new NoopDisposable();

        private sealed class NoopDisposable : IDisposable
        {
            public void Dispose() { }
        }
    }
}
