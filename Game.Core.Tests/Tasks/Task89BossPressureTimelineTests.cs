using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task89BossPressureTimelineTests
{
    // ACC:T89.1
    [Fact]
    [Trait("acceptance", "ACC:T89.1")]
    public void ShouldExposeDeterministicPressureEscalation_WhenReplayingTurnAdvancedAndCombatStartedStream()
    {
        var timelineType = FindTypeOrNull("Game.Core.Services.Sanguo.BossPressureTimeline");
        timelineType.Should().NotBeNull(
            "T89 requires an independent R6 boss pressure timeline module split from T76.");

        var replayMethod = timelineType!.GetMethod(
            "ReplayEventTypes",
            BindingFlags.Public | BindingFlags.Static,
            binder: null,
            types: new[] { typeof(IEnumerable<string>) },
            modifiers: null);

        replayMethod.Should().NotBeNull(
            "T89 should expose deterministic timeline replay from core.sanguo.game.turn.advanced/core.sanguo.combat.started.");

        var eventTypes = new[]
        {
            SanguoGameTurnAdvanced.EventType,
            SanguoGameTurnAdvanced.EventType,
            SanguoCombatStarted.EventType,
            SanguoGameTurnAdvanced.EventType,
        };

        var replayResult = replayMethod!.Invoke(null, new object[] { eventTypes });
        replayResult.Should().NotBeNull();

        var pressureByStep = ReadIntSequenceProperty(replayResult!, "PressureByStep");
        pressureByStep.Should().Equal(1, 2, 0, 1);
    }

    [Fact]
    public async Task ShouldNotPublishCombatStarted_WhenAdvancingDefaultTurnOutsideR6SplitScope()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var boardState = new SanguoBoardState(
            players: new[]
            {
                new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0, economyRules: SanguoEconomyRules.Default),
            },
            citiesById: new Dictionary<string, City>());
        var treasury = new SanguoTreasury();

        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            totalPositionsHint: 1);

        await manager.StartNewGameAsync(
            gameId: "g-t89-scope",
            playerOrder: new[] { "p1" },
            year: 2026,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: "ut.start");
        bus.Published.Clear();

        await manager.AdvanceTurnAsync(correlationId: "corr-advance", causationId: "ut.advance");

        bus.Published.Should().ContainSingle(e => e.Type == SanguoGameTurnAdvanced.EventType);
        bus.Published.Should().NotContain(
            e => e.Type == SanguoCombatStarted.EventType,
            "T89 scope must not change non-combat turn-advance behavior outside the split boundary.");

        var advancedEvent = bus.Published.Single(e => e.Type == SanguoGameTurnAdvanced.EventType);
        var advancedPayload = ((JsonElementEventData)advancedEvent.Data!).Value;
        advancedPayload.GetProperty("TurnNumber").GetInt32().Should().Be(2);
        advancedPayload.GetProperty("ActivePlayerId").GetString().Should().Be("p1");
    }

    private static Type? FindTypeOrNull(string fullName)
    {
        foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            var type = assembly.GetType(fullName, throwOnError: false, ignoreCase: false);
            if (type is not null)
            {
                return type;
            }
        }

        return null;
    }

    private static int[] ReadIntSequenceProperty(object instance, string propertyName)
    {
        var property = instance.GetType().GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
        property.Should().NotBeNull($"Replay result must expose public property '{propertyName}'.");

        var raw = property!.GetValue(instance);
        raw.Should().NotBeNull();
        raw.Should().BeAssignableTo<IEnumerable<int>>();

        return ((IEnumerable<int>)raw!).ToArray();
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
