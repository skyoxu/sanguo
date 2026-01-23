using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Services;
using Game.Core.Utilities;
using System;
using System.Collections.Generic;
using System.Reflection;
using System.Threading.Tasks;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task56RandomEventCoverageTests
{
    // ACC:T56.1
    [Fact]
    public void ResolveTotalPositions_ShouldReturnZero_WhenNoHintAndNoCities()
    {
        var bus = new RecordingEventBus();
        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 500m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));
        var economy = new SanguoEconomyManager(bus);

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new DeterministicRandomNumberGenerator(seed: 1),
            randomSeed: 1,
            totalPositionsHint: 0,
            quarterEnvironmentEventTriggerChance: 0.0,
            randomEventsCatalog: null,
            globalEventIntervalTurns: 5,
            tileTypesByPositionIndex: new Dictionary<int, string>());

        var mi = typeof(SanguoTurnManager).GetMethod(
            "ResolveTotalPositions",
            BindingFlags.Instance | BindingFlags.NonPublic);

        mi.Should().NotBeNull();
        var value = (int)mi!.Invoke(mgr, Array.Empty<object>())!;
        value.Should().Be(0);
    }

    // ACC:T56.1
    [Fact]
    public async Task PublishPlayerStateChangedAsync_ShouldNoop_WhenGameIdNotSet()
    {
        var bus = new RecordingEventBus();
        var mgr = CreateManager(bus, randomEventsCatalog: null);

        var mi = typeof(SanguoTurnManager).GetMethod(
            "PublishPlayerStateChangedAsync",
            BindingFlags.Instance | BindingFlags.NonPublic);

        mi.Should().NotBeNull();

        var t = (Task)mi!.Invoke(
            mgr,
            new object?[]
            {
                "p1",
                "corr",
                "ui.menu.start",
                DateTimeOffset.UtcNow
            })!;

        await t;
        bus.Published.Should().BeEmpty();
    }

    // ACC:T56.1
    [Fact]
    public void TryPickRandomEvent_ShouldReturnFalse_WhenCatalogMissing()
    {
        var bus = new RecordingEventBus();
        var mgr = CreateManager(bus, randomEventsCatalog: null);

        var ok = InvokeTryPickRandomEvent(
            mgr,
            poolId: "default",
            playerId: "p1",
            roundNumber: 1,
            rngContextId: "rng.random_events:1:1:tile",
            out _);

        ok.Should().BeFalse();
    }

    // ACC:T56.1
    [Fact]
    public void TryPickRandomEvent_ShouldReturnFalse_WhenPoolIdBlank()
    {
        var bus = new RecordingEventBus();
        var mgr = CreateManager(bus, randomEventsCatalog: BuildSingleEventCatalog("e1", "moneyDelta", 1, null));

        var ok = InvokeTryPickRandomEvent(
            mgr,
            poolId: " ",
            playerId: "p1",
            roundNumber: 1,
            rngContextId: "rng.random_events:1:1:tile",
            out _);

        ok.Should().BeFalse();
    }

    // ACC:T56.1
    [Fact]
    public void TryPickRandomEvent_ShouldReturnFalse_WhenPoolHasNoValidCandidates()
    {
        var catalog = new SanguoRandomEventsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Events: Array.Empty<SanguoRandomEventCatalogEntry>(),
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(PoolId: "default", EventIds: new[] { "missing" }),
                new SanguoRandomEventPoolCatalogEntry(PoolId: "global", EventIds: new[] { "missing" }),
            });

        var bus = new RecordingEventBus();
        var mgr = CreateManager(bus, randomEventsCatalog: catalog);

        var ok = InvokeTryPickRandomEvent(
            mgr,
            poolId: "default",
            playerId: "p1",
            roundNumber: 1,
            rngContextId: "rng.random_events:1:1:tile",
            out _);

        ok.Should().BeFalse();
    }

    // ACC:T56.1
    [Fact]
    public async Task ShouldNotPublishTileRandomEvent_WhenCatalogMissing()
    {
        var bus = new RecordingEventBus();
        var mgr = CreateManager(bus, randomEventsCatalog: null);

        await StartSinglePlayerGameAsync(mgr);

        var before = bus.Published.Count;
        await InvokeTryTriggerTileRandomEventAsync(mgr, occurredAt: DateTimeOffset.UtcNow);

        bus.Published
            .GetRange(before, bus.Published.Count - before)
            .Should()
            .NotContain(e => e.Type == SanguoRandomEventApplied.EventType || e.Type == SanguoRandomEventRejected.EventType);
    }

    // ACC:T56.1
    [Fact]
    public async Task ShouldNotPublishTileRandomEvent_WhenTilePoolMissing()
    {
        var catalog = new SanguoRandomEventsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Events: new[]
            {
                new SanguoRandomEventCatalogEntry(
                    EventId: "e1",
                    NameKey: "event.e1.name",
                    DescriptionKey: "event.e1.desc",
                    EffectKind: "moneyDelta",
                    MoneyDelta: 10,
                    StepDelta: null,
                    CooldownRounds: 0,
                    UniqueOnce: false),
            },
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(PoolId: "global", EventIds: new[] { "e1" }),
            });

        var bus = new RecordingEventBus();
        var mgr = CreateManager(bus, randomEventsCatalog: catalog);

        await StartSinglePlayerGameAsync(mgr);

        var before = bus.Published.Count;
        await InvokeTryTriggerTileRandomEventAsync(mgr, occurredAt: DateTimeOffset.UtcNow);

        bus.Published
            .GetRange(before, bus.Published.Count - before)
            .Should()
            .NotContain(e => e.Type == SanguoRandomEventApplied.EventType || e.Type == SanguoRandomEventRejected.EventType);
    }

    // ACC:T56.1
    [Fact]
    public async Task ShouldPublishRejected_WhenEffectKindNotAllowlisted()
    {
        var catalog = BuildSingleEventCatalog(
            eventId: "invalid",
            effectKind: "combat",
            moneyDelta: null,
            stepDelta: null);

        var bus = new RecordingEventBus();
        var mgr = CreateManager(bus, randomEventsCatalog: catalog);

        await StartSinglePlayerGameAsync(mgr);

        var before = bus.Published.Count;
        await InvokeTryTriggerTileRandomEventAsync(mgr, occurredAt: DateTimeOffset.UtcNow);

        var evts = bus.Published.GetRange(before, bus.Published.Count - before);
        evts.Should().Contain(e => e.Type == SanguoRandomEventRejected.EventType);

        var rejected = evts.Find(e => e.Type == SanguoRandomEventRejected.EventType);
        rejected.Should().NotBeNull();
        rejected!.Data.Should().BeOfType<JsonElementEventData>();

        var root = ((JsonElementEventData)rejected.Data!).Value;
        root.GetProperty("RejectReason").GetString().Should().Be("invalid_effect_kind");
        root.GetProperty("PickedId").GetString().Should().Be("invalid");

        evts.Should().NotContain(e => e.Type == SanguoPlayerStateChanged.EventType);
    }

    // ACC:T56.1
    [Theory]
    [InlineData(10)]
    [InlineData(-10)]
    [InlineData(-999)]
    public async Task ShouldPublishPlayerStateChanged_WhenMoneyDeltaNonZero(int delta)
    {
        var catalog = BuildSingleEventCatalog(
            eventId: "money_delta",
            effectKind: "moneyDelta",
            moneyDelta: delta,
            stepDelta: null);

        var bus = new RecordingEventBus();
        var mgr = CreateManager(bus, randomEventsCatalog: catalog, startingMoney: 50m);

        await StartSinglePlayerGameAsync(mgr);

        var before = bus.Published.Count;
        await InvokeTryTriggerTileRandomEventAsync(mgr, occurredAt: DateTimeOffset.UtcNow);

        var evts = bus.Published.GetRange(before, bus.Published.Count - before);
        evts.Should().Contain(e => e.Type == SanguoRandomEventApplied.EventType);
        evts.Should().Contain(e => e.Type == SanguoPlayerStateChanged.EventType);
    }

    // ACC:T56.1
    [Fact]
    public async Task ShouldNotPublishPlayerStateChanged_WhenMoneyDeltaZero()
    {
        var catalog = BuildSingleEventCatalog(
            eventId: "money_zero",
            effectKind: "moneyDelta",
            moneyDelta: 0,
            stepDelta: null);

        var bus = new RecordingEventBus();
        var mgr = CreateManager(bus, randomEventsCatalog: catalog, startingMoney: 50m);

        await StartSinglePlayerGameAsync(mgr);

        var before = bus.Published.Count;
        await InvokeTryTriggerTileRandomEventAsync(mgr, occurredAt: DateTimeOffset.UtcNow);

        var evts = bus.Published.GetRange(before, bus.Published.Count - before);
        evts.Should().Contain(e => e.Type == SanguoRandomEventApplied.EventType);
        evts.Should().NotContain(e => e.Type == SanguoPlayerStateChanged.EventType);
    }

    // ACC:T56.1
    [Fact]
    public async Task ShouldPublishRejected_WhenMoneyDeltaMissing()
    {
        var catalog = BuildSingleEventCatalog(
            eventId: "missing_money",
            effectKind: "moneyDelta",
            moneyDelta: null,
            stepDelta: null);

        var bus = new RecordingEventBus();
        var mgr = CreateManager(bus, randomEventsCatalog: catalog);

        await StartSinglePlayerGameAsync(mgr);

        var before = bus.Published.Count;
        await InvokeTryTriggerTileRandomEventAsync(mgr, occurredAt: DateTimeOffset.UtcNow);

        var evts = bus.Published.GetRange(before, bus.Published.Count - before);
        var rejected = evts.Find(e => e.Type == SanguoRandomEventRejected.EventType);
        rejected.Should().NotBeNull();

        var root = ((JsonElementEventData)rejected!.Data!).Value;
        root.GetProperty("RejectReason").GetString().Should().Be("missing_money_delta");
        root.GetProperty("PickedId").GetString().Should().Be("missing_money");
    }

    // ACC:T56.1
    [Fact]
    public async Task ShouldPublishRejected_WhenStepDeltaMissing()
    {
        var catalog = BuildSingleEventCatalog(
            eventId: "missing_step",
            effectKind: "economyStepDelta",
            moneyDelta: null,
            stepDelta: null);

        var bus = new RecordingEventBus();
        var mgr = CreateManager(bus, randomEventsCatalog: catalog);

        await StartSinglePlayerGameAsync(mgr);

        var before = bus.Published.Count;
        await InvokeTryTriggerTileRandomEventAsync(mgr, occurredAt: DateTimeOffset.UtcNow);

        var evts = bus.Published.GetRange(before, bus.Published.Count - before);
        var rejected = evts.Find(e => e.Type == SanguoRandomEventRejected.EventType);
        rejected.Should().NotBeNull();

        var root = ((JsonElementEventData)rejected!.Data!).Value;
        root.GetProperty("RejectReason").GetString().Should().Be("missing_step_delta");
        root.GetProperty("PickedId").GetString().Should().Be("missing_step");
    }

    private static SanguoTurnManager CreateManager(
        RecordingEventBus bus,
        SanguoRandomEventsCatalog? randomEventsCatalog,
        decimal startingMoney = 500m)
    {
        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: startingMoney, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));
        var economy = new SanguoEconomyManager(bus);

        return new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new DeterministicRandomNumberGenerator(seed: 1),
            randomSeed: 1,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            randomEventsCatalog: randomEventsCatalog,
            globalEventIntervalTurns: 5,
            tileTypesByPositionIndex: new Dictionary<int, string> { [0] = SanguoTileDefinition.TileTypeEvent });
    }

    private static SanguoRandomEventsCatalog BuildSingleEventCatalog(
        string eventId,
        string effectKind,
        int? moneyDelta,
        int? stepDelta)
        => new(
            SchemaVersion: 1,
            Version: 1,
            Events: new[]
            {
                new SanguoRandomEventCatalogEntry(
                    EventId: eventId,
                    NameKey: $"event.{eventId}.name",
                    DescriptionKey: $"event.{eventId}.desc",
                    EffectKind: effectKind,
                    MoneyDelta: moneyDelta,
                    StepDelta: stepDelta,
                    CooldownRounds: 0,
                    UniqueOnce: false),
            },
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(PoolId: "default", EventIds: new[] { eventId }),
                new SanguoRandomEventPoolCatalogEntry(PoolId: "global", EventIds: new[] { eventId }),
            });

    private static Task InvokeTryTriggerTileRandomEventAsync(
        SanguoTurnManager mgr,
        DateTimeOffset occurredAt)
    {
        var mi = typeof(SanguoTurnManager).GetMethod(
            "TryTriggerTileRandomEventAsync",
            BindingFlags.Instance | BindingFlags.NonPublic);

        mi.Should().NotBeNull();

        var t = (Task)mi!.Invoke(
            mgr,
            new object?[]
            {
                "g1", // gameId
                "p1", // activePlayerId
                0, // positionIndex (event tile)
                "corr",
                "ui.menu.start",
                occurredAt
            })!;

        return t;
    }

    private static Task StartSinglePlayerGameAsync(SanguoTurnManager mgr)
        => mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

    private static bool InvokeTryPickRandomEvent(
        SanguoTurnManager mgr,
        string poolId,
        string playerId,
        int roundNumber,
        string rngContextId,
        out string? rejectReason)
    {
        var mi = typeof(SanguoTurnManager).GetMethod(
            "TryPickRandomEvent",
            BindingFlags.Instance | BindingFlags.NonPublic);

        mi.Should().NotBeNull();

        object?[] args =
        {
            poolId,
            playerId,
            roundNumber,
            rngContextId,
            null, // out picked
            null, // out candidatesSortedIdsHash
            -1,   // out pickedIndex
            null, // out pickedId
            null, // out rejectReason
        };

        var ok = (bool)mi!.Invoke(mgr, args)!;
        rejectReason = args[8] as string;
        return ok;
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
