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

public class Task8RedTests
{
    [Fact]
    public void AdvanceTurn_WhenCrossingQuarterBoundary_PublishesSeasonEventApplied()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(bus, economy);

        mgr.StartNewGame(
            gameId: "game-1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 3,
            day: 31,
            correlationId: "corr-1",
            causationId: null);

        mgr.AdvanceTurn(correlationId: "corr-1", causationId: "cmd-1");

        bus.Published.Should().Contain(e => e.Type == SanguoSeasonEventApplied.EventType, "Task 8 requires publishing a quarterly environment event on quarter boundary");

        var seasonEvt = bus.Published.Find(e => e.Type == SanguoSeasonEventApplied.EventType);
        seasonEvt.Should().NotBeNull();
        seasonEvt!.Source.Should().Be(nameof(SanguoEconomyManager));
        seasonEvt.Data.Should().BeOfType<JsonElementEventData>();

        var payload = ((JsonElementEventData)seasonEvt.Data!).Value;
        payload.GetProperty("GameId").GetString().Should().Be("game-1");
        payload.GetProperty("Year").GetInt32().Should().Be(1);
        payload.GetProperty("Season").GetInt32().Should().Be(2, "April is season 2 when season = ((month-1)/3)+1");
        payload.GetProperty("AffectedRegionIds").ValueKind.Should().Be(JsonValueKind.Array);
        payload.GetProperty("YieldMultiplier").GetDecimal().Should().BeGreaterOrEqualTo(0m);
        payload.GetProperty("CorrelationId").GetString().Should().Be("corr-1");
        payload.GetProperty("CausationId").GetString().Should().Be("cmd-1");
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
