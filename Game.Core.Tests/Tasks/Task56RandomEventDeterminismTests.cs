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
using System.Text.Json;
using System.Threading.Tasks;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task56RandomEventDeterminismTests
{
    // ACC:T56.1
    [Fact]
    public async Task ShouldPublishSamePickRecord_WhenTileTriggerUsesSameSeedAndSequence()
    {
        var seed = 12345;

        var first = await RunOneTileTriggerAsync(seed);
        var second = await RunOneTileTriggerAsync(seed);

        first.CandidatesSortedIdsHash.Should().NotBeNullOrWhiteSpace();
        first.PickedId.Should().NotBeNullOrWhiteSpace();
        first.PickedIndex.Should().BeGreaterOrEqualTo(0);
        first.RngContextId.Should().NotBeNullOrWhiteSpace();
        first.RngContextId!.Should().Contain(":tile");

        second.CandidatesSortedIdsHash.Should().Be(first.CandidatesSortedIdsHash);
        second.PickedId.Should().Be(first.PickedId);
        second.PickedIndex.Should().Be(first.PickedIndex);
        second.RngContextId.Should().Be(first.RngContextId);
    }

    // ACC:T56.1
    [Fact]
    public async Task ShouldNotPublishRandomEvent_WhenLandingOnNonEventTile()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 500m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new DeterministicRandomNumberGenerator(seed: 1),
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            randomEventsCatalog: BuildCatalog(),
            globalEventIntervalTurns: 5,
            tileTypesByPositionIndex: new Dictionary<int, string> { [0] = SanguoTileDefinition.TileTypeEmpty });

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-roll", causationId: "ui.hud.dice.roll");

        bus.Published.Skip(before).Should().NotContain(e => e.Type == SanguoRandomEventApplied.EventType);
    }

    // ACC:T56.2
    [Theory]
    [InlineData(5)]
    [InlineData(10)]
    [InlineData(20)]
    public async Task ShouldBeDeterministic_WhenGlobalTriggerAtConfiguredInterval(int intervalTurns)
    {
        var seed = 777;
        var first = await RunUntilOneGlobalTriggerAsync(seed, intervalTurns);
        var second = await RunUntilOneGlobalTriggerAsync(seed, intervalTurns);

        first.CandidatesSortedIdsHash.Should().NotBeNullOrWhiteSpace();
        first.PickedId.Should().NotBeNullOrWhiteSpace();
        first.PickedIndex.Should().BeGreaterOrEqualTo(0);
        first.RngContextId.Should().NotBeNullOrWhiteSpace();
        first.RngContextId!.Should().Contain(":global");

        second.CandidatesSortedIdsHash.Should().Be(first.CandidatesSortedIdsHash);
        second.PickedId.Should().Be(first.PickedId);
        second.PickedIndex.Should().Be(first.PickedIndex);
        second.RngContextId.Should().Be(first.RngContextId);
    }

    private static async Task<(string? CandidatesSortedIdsHash, int? PickedIndex, string? PickedId, string? RngContextId)> RunOneTileTriggerAsync(int seed)
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 500m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var rng = new DeterministicRandomNumberGenerator(seed);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: rng,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            randomEventsCatalog: BuildCatalog(),
            globalEventIntervalTurns: 5,
            tileTypesByPositionIndex: new Dictionary<int, string> { [0] = SanguoTileDefinition.TileTypeEvent });

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-roll", causationId: "ui.hud.dice.roll");

        var tileEvent = bus.Published
            .Skip(before)
            .Where(e => e.Type == SanguoRandomEventApplied.EventType)
            .Select(ReadRandomEventApplied)
            .FirstOrDefault(x => x.RngContextId != null && x.RngContextId.Contains(":tile", StringComparison.Ordinal));

        tileEvent.Should().NotBeNull();
        return tileEvent;
    }

    private static async Task<(string? CandidatesSortedIdsHash, int? PickedIndex, string? PickedId, string? RngContextId)> RunUntilOneGlobalTriggerAsync(int seed, int intervalTurns)
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 500m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var rng = new DeterministicRandomNumberGenerator(seed);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: rng,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            randomEventsCatalog: BuildCatalog(),
            globalEventIntervalTurns: intervalTurns,
            tileTypesByPositionIndex: new Dictionary<int, string> { [0] = SanguoTileDefinition.TileTypeEvent });

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        for (var i = 0; i < intervalTurns; i++)
        {
            await mgr.AdvanceTurnAsync(correlationId: $"corr-adv-{i}", causationId: "ut.advance");
        }

        var globalEvent = bus.Published
            .Where(e => e.Type == SanguoRandomEventApplied.EventType)
            .Select(ReadRandomEventApplied)
            .FirstOrDefault(x => x.RngContextId != null && x.RngContextId.Contains(":global", StringComparison.Ordinal));

        globalEvent.Should().NotBeNull();
        return globalEvent;
    }

    private static (string? CandidatesSortedIdsHash, int? PickedIndex, string? PickedId, string? RngContextId) ReadRandomEventApplied(DomainEvent evt)
    {
        evt.Data.Should().BeOfType<JsonElementEventData>();
        var root = ((JsonElementEventData)evt.Data!).Value;

        string? rngContextId = null;
        if (root.TryGetProperty("RngContextId", out var ctx) && ctx.ValueKind == JsonValueKind.String)
        {
            rngContextId = ctx.GetString();
        }

        string? candidatesHash = null;
        if (root.TryGetProperty("CandidatesSortedIdsHash", out var h) && h.ValueKind == JsonValueKind.String)
        {
            candidatesHash = h.GetString();
        }

        int? pickedIndex = null;
        if (root.TryGetProperty("PickedIndex", out var pi) && pi.ValueKind == JsonValueKind.Number && pi.TryGetInt32(out var parsed))
        {
            pickedIndex = parsed;
        }

        string? pickedId = null;
        if (root.TryGetProperty("PickedId", out var pid) && pid.ValueKind == JsonValueKind.String)
        {
            pickedId = pid.GetString();
        }

        return (candidatesHash, pickedIndex, pickedId, rngContextId);
    }

    private static SanguoRandomEventsCatalog BuildCatalog()
    {
        return new SanguoRandomEventsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Events: new[]
            {
                new SanguoRandomEventCatalogEntry(
                    EventId: "event_economy_boost",
                    NameKey: "event.name",
                    DescriptionKey: "event.desc",
                    EffectKind: "economyStepDelta",
                    MoneyDelta: null,
                    StepDelta: 1,
                    CooldownRounds: 0,
                    UniqueOnce: false),
                new SanguoRandomEventCatalogEntry(
                    EventId: "event_money_small",
                    NameKey: "event.name2",
                    DescriptionKey: "event.desc2",
                    EffectKind: "moneyDelta",
                    MoneyDelta: 200,
                    StepDelta: null,
                    CooldownRounds: 0,
                    UniqueOnce: false),
            },
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(
                    PoolId: "default",
                    EventIds: new[] { "event_money_small", "event_economy_boost" }),
            });
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
