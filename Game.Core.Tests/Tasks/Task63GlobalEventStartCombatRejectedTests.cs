using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Services;
using Game.Core.Utilities;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task63GlobalEventStartCombatRejectedTests
{
    [Fact]
    public async Task ShouldRejectStartCombatEffectKind_WhenGlobalRoundEventTriggers()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;

        var players = new[]
        {
            new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0, economyRules: rules),
            new SanguoPlayer(playerId: "p2", money: 100m, positionIndex: 0, economyRules: rules),
            new SanguoPlayer(playerId: "p3", money: 100m, positionIndex: 0, economyRules: rules),
            new SanguoPlayer(playerId: "p4", money: 100m, positionIndex: 0, economyRules: rules),
        };

        var boardState = new SanguoBoardState(players: players, citiesById: new Dictionary<string, City>());
        var treasury = new SanguoTreasury();

        var catalog = new SanguoRandomEventsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Events: new[]
            {
                new SanguoRandomEventCatalogEntry(
                    EventId: "event_combat_small",
                    NameKey: "event.event_combat_small.name",
                    DescriptionKey: "event.event_combat_small.desc",
                    EffectKind: SanguoEffectKinds.StartCombat,
                    MoneyDelta: null,
                    StepDelta: null,
                    CooldownRounds: 0,
                    UniqueOnce: false,
                    EncounterId: "enc_event_combat_small",
                    EncounterTarget: 10),
            },
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(PoolId: "global", NameKey: "event.pool.test", EventIds: new[] { "event_combat_small" }),
                new SanguoRandomEventPoolCatalogEntry(PoolId: "default", NameKey: "event.pool.test", EventIds: new[] { "event_combat_small" }),
            });

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new DeterministicRandomNumberGenerator(seed: 7),
            randomSeed: 7,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            randomEventsCatalog: catalog,
            globalEventIntervalTurns: 5,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global",
            tileTypesByPositionIndex: new Dictionary<int, string> { [0] = SanguoTileDefinition.TileTypeEmpty },
            combatRatingByPlayerId: new Dictionary<string, int>(StringComparer.Ordinal));

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "p2", "p3", "p4" },
            year: 2026,
            month: 1,
            day: 1,
            correlationId: "corr_start",
            causationId: "ut.start");

        bus.Published.Should().NotContain(e => e.Type == SanguoCombatStarted.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoCombatEnded.EventType);

        var rejected = bus.Published.FirstOrDefault(e => e.Type == SanguoRandomEventRejected.EventType);
        rejected.Should().NotBeNull();

        var rejectedJson = ((JsonElementEventData)rejected!.Data!).Value;
        rejectedJson.GetProperty("RejectReason").GetString().Should().Be("effect_kind_not_allowed_for_global_events");
        rejectedJson.GetProperty("EventId").GetString().Should().StartWith("global:");
    }

    [Fact]
    public async Task ShouldRejectStartCombatEffectKind_WhenGlobalTurnBoundaryTriggers()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;

        var player = new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { player }, citiesById: new Dictionary<string, City>());
        var treasury = new SanguoTreasury();

        var catalog = new SanguoRandomEventsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Events: new[]
            {
                new SanguoRandomEventCatalogEntry(
                    EventId: "event_combat_small",
                    NameKey: "event.event_combat_small.name",
                    DescriptionKey: "event.event_combat_small.desc",
                    EffectKind: SanguoEffectKinds.StartCombat,
                    MoneyDelta: null,
                    StepDelta: null,
                    CooldownRounds: 0,
                    UniqueOnce: false,
                    EncounterId: "enc_event_combat_small",
                    EncounterTarget: 10),
            },
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(PoolId: "global", NameKey: "event.pool.test", EventIds: new[] { "event_combat_small" }),
                new SanguoRandomEventPoolCatalogEntry(PoolId: "default", NameKey: "event.pool.test", EventIds: new[] { "event_combat_small" }),
            });

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new DeterministicRandomNumberGenerator(seed: 7),
            randomSeed: 7,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            randomEventsCatalog: catalog,
            globalEventIntervalTurns: 5,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global",
            tileTypesByPositionIndex: new Dictionary<int, string> { [0] = SanguoTileDefinition.TileTypeEmpty },
            combatRatingByPlayerId: new Dictionary<string, int>(StringComparer.Ordinal));

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 2026,
            month: 1,
            day: 1,
            correlationId: "corr_start",
            causationId: "ut.start");

        bus.Published.Clear();

        for (var i = 0; i < 4; i++)
        {
            await mgr.AdvanceTurnAsync(correlationId: $"corr_adv_{i}", causationId: null);
        }

        bus.Published.Should().NotContain(e => e.Type == SanguoRandomEventRejected.EventType);

        await mgr.AdvanceTurnAsync(correlationId: "corr_adv_boundary", causationId: null);

        var rejected = bus.Published.FirstOrDefault(e => e.Type == SanguoRandomEventRejected.EventType);
        rejected.Should().NotBeNull();

        var rejectedJson = ((JsonElementEventData)rejected!.Data!).Value;
        rejectedJson.GetProperty("RejectReason").GetString().Should().Be("effect_kind_not_allowed_for_global_events");
        rejectedJson.GetProperty("EventId").GetString().Should().StartWith("global:");
        bus.Published.Should().NotContain(e => e.Type == SanguoCombatStarted.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoCombatEnded.EventType);
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
