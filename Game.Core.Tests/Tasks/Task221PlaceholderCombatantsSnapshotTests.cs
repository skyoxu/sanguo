using System;
using System.Collections.Generic;
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

public sealed class Task221PlaceholderCombatantsSnapshotTests
{
    // ACC:T221.1
    // ACC:T221.2
    // ACC:T221.3
    // ACC:T221.4
    // ACC:T221.5
    // ACC:T221.6
    // ACC:T221.7
    // ACC:T221.8
    // ACC:T221.9
    [Fact]
    public async Task ShouldPublishCombatSnapshotsWithPlaceholderFields_WhenStartCombatActionIsExecuted()
    {
        var bus = new CapturingEventBus();
        var manager = await CreateStartedManagerAsync(bus);

        await manager.ExecuteHumanTileActionAsync(
            action: "start_combat",
            correlationId: "corr-221-start",
            causationId: "ut.task221");

        var started = FindEvent(bus, SanguoCombatStarted.EventType);
        var startedPayload = ((JsonElementEventData)started.Data!).Value;

        var playerSnapshot = startedPayload.GetProperty("PlayerSnapshot");
        var enemySnapshot = startedPayload.GetProperty("EnemySnapshot");
        var playerMainUnit = playerSnapshot.GetProperty("MainUnit");
        var enemyMainUnit = enemySnapshot.GetProperty("MainUnit");

        playerMainUnit.GetProperty("DisplayName").GetString().Should().Be("Player Placeholder");
        enemyMainUnit.GetProperty("DisplayName").GetString().Should().Be("Enemy Placeholder");

        playerMainUnit.GetProperty("UnitRole").GetString().Should().Be("player");
        enemyMainUnit.GetProperty("UnitRole").GetString().Should().Be("enemy");

        playerMainUnit.GetProperty("SkillIds").GetArrayLength().Should().BeGreaterThan(0);
        playerMainUnit.GetProperty("PassiveSkillIds").GetArrayLength().Should().Be(0);
        playerMainUnit.GetProperty("RelicIds").GetArrayLength().Should().Be(0);
        playerMainUnit.GetProperty("BuffIds").GetArrayLength().Should().BeGreaterThan(0);
        playerMainUnit.GetProperty("DebuffIds").GetArrayLength().Should().Be(0);

        enemyMainUnit.GetProperty("SkillIds").GetArrayLength().Should().Be(0);
        enemyMainUnit.GetProperty("PassiveSkillIds").GetArrayLength().Should().Be(0);
        enemyMainUnit.GetProperty("RelicIds").GetArrayLength().Should().Be(0);
        enemyMainUnit.GetProperty("BuffIds").GetArrayLength().Should().Be(0);
        enemyMainUnit.GetProperty("DebuffIds").GetArrayLength().Should().BeGreaterThan(0);

        playerMainUnit.GetProperty("Stats").GetProperty("CurrentHP").GetInt32().Should().BeGreaterThan(0);
        enemyMainUnit.GetProperty("Stats").GetProperty("CurrentHP").GetInt32().Should().BeGreaterThan(0);
    }

    // ACC:T221.10
    // ACC:T221.11
    [Fact]
    public async Task ShouldCarryRuntimeSnapshotsInCombatEndedResult_WhenCombatResolves()
    {
        var bus = new CapturingEventBus();
        var manager = await CreateStartedManagerAsync(bus);

        await manager.ExecuteHumanTileActionAsync(
            action: "start_combat",
            correlationId: "corr-221-end",
            causationId: "ut.task221");

        var ended = FindEvent(bus, SanguoCombatEnded.EventType);
        var endedPayload = ((JsonElementEventData)ended.Data!).Value;
        var result = endedPayload.GetProperty("Result");

        result.GetProperty("PlayerSnapshot").ValueKind.Should().Be(JsonValueKind.Object);
        result.GetProperty("EnemySnapshot").ValueKind.Should().Be(JsonValueKind.Object);

        var resultPlayerMain = result.GetProperty("PlayerSnapshot").GetProperty("MainUnit");
        var resultEnemyMain = result.GetProperty("EnemySnapshot").GetProperty("MainUnit");

        resultPlayerMain.GetProperty("DisplayName").GetString().Should().Be("Player Placeholder");
        resultEnemyMain.GetProperty("DisplayName").GetString().Should().Be("Enemy Placeholder");
    }

    private static DomainEvent FindEvent(CapturingEventBus bus, string eventType)
    {
        foreach (var item in bus.Published)
        {
            if (string.Equals(item.Type, eventType, StringComparison.Ordinal))
            {
                return item;
            }
        }

        throw new InvalidOperationException($"Expected event not found: {eventType}");
    }

    private static async Task<SanguoTurnManager> CreateStartedManagerAsync(CapturingEventBus bus)
    {
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var player = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>());
        var treasury = new SanguoTreasury();

        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new DeterministicRandomNumberGenerator(seed: 7),
            randomSeed: 7,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            tileTypesByPositionIndex: new Dictionary<int, string>
            {
                [0] = SanguoTileDefinition.TileTypePass,
            },
            combatRatingByPlayerId: new Dictionary<string, int>(StringComparer.Ordinal)
            {
                ["p1"] = 100,
            });

        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-221-bootstrap",
            causationId: "ut.start");
        bus.Published.Clear();
        return manager;
    }

    private sealed class CapturingEventBus : IEventBus
    {
        public List<DomainEvent> Published { get; } = new();

        public Task PublishAsync(DomainEvent evt)
        {
            Published.Add(evt);
            return Task.CompletedTask;
        }

        public IDisposable Subscribe(Func<DomainEvent, Task> handler)
        {
            return new DummySubscription();
        }

        private sealed class DummySubscription : IDisposable
        {
            public void Dispose()
            {
            }
        }
    }
}
