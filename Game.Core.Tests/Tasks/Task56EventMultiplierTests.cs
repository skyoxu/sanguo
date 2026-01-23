using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Xunit;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Game.Core.Utilities;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;

namespace Game.Core.Tests.Tasks;

public sealed class Task56EventMultiplierTests
{
    // ACC:T56.2
    [Fact]
    public async Task ShouldRejectAndNotChangeMoney_WhenEffectKindNotAllowlisted()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var rng = new QueueRng(nextInts: new[] { 0 }, fixedNextDouble: 1.0);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: rng,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            randomEventsCatalog: BuildCatalogWithInvalidFirst(),
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

        var moneyBefore = p1.Money.ToDecimal();
        await AdvanceUntilOneGlobalEventAsync(mgr, 5);
        var moneyAfter = p1.Money.ToDecimal();

        moneyAfter.Should().Be(moneyBefore);

        var rejected = bus.Published
            .Where(e => e.Type == SanguoRandomEventRejected.EventType)
            .Select(ReadRandomEventAppliedJson)
            .Single();

        rejected.TryGetProperty("RejectReason", out var reason).Should().BeTrue();
        reason.GetString().Should().Be("invalid_effect_kind");

        rejected.TryGetProperty("EffectKind", out var kind).Should().BeTrue();
        kind.GetString().Should().Be("teleport");
        rejected.TryGetProperty("MoneyDelta", out var md).Should().BeTrue();
        md.GetInt32().Should().Be(999);
        rejected.TryGetProperty("AppliedMultipliersAfter", out _).Should().BeFalse();
    }

    // ACC:T56.2
    [Fact]
    public async Task ShouldPublishRejectedEvent_WhenTileTriggerSelectsInvalidEffectKind()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var catalog = new SanguoRandomEventsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Events: new[]
            {
                new SanguoRandomEventCatalogEntry(
                    EventId: "bad_tile",
                    NameKey: "event.bad.name",
                    DescriptionKey: "event.bad.desc",
                    EffectKind: "teleport",
                    MoneyDelta: 999,
                    StepDelta: null,
                    CooldownRounds: 0,
                    UniqueOnce: false),
            },
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(PoolId: "default", EventIds: new[] { "bad_tile" }),
                new SanguoRandomEventPoolCatalogEntry(PoolId: "global", EventIds: new[] { "bad_tile" }),
            });

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new DeterministicRandomNumberGenerator(seed: 1),
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            randomEventsCatalog: catalog,
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

        var moneyBefore = p1.Money.ToDecimal();
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-roll", causationId: "ui.hud.dice.roll");
        p1.Money.ToDecimal().Should().Be(moneyBefore);

        var rejected = bus.Published
            .Where(e => e.Type == SanguoRandomEventRejected.EventType)
            .Select(ReadRandomEventAppliedJson)
            .FirstOrDefault();

        rejected.ValueKind.Should().Be(JsonValueKind.Object);
        rejected.TryGetProperty("RejectReason", out var reason).Should().BeTrue();
        reason.GetString().Should().Be("invalid_effect_kind");
        rejected.TryGetProperty("RngContextId", out var ctx).Should().BeTrue();
        (ctx.GetString() ?? string.Empty).Should().Contain(":tile");
    }

    // ACC:T56.3
    [Fact]
    public async Task ShouldApplyMoneyDeltaDirectly_WhenEffectKindIsMoneyDelta()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        // Pick index=1 => b_money in sorted candidates: a_bad, b_money, c_step
        var rng = new QueueRng(nextInts: new[] { 1 }, fixedNextDouble: 1.0);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: rng,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            randomEventsCatalog: BuildCatalogWithInvalidFirst(),
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

        await AdvanceUntilOneGlobalEventAsync(mgr, 5);

        p1.Money.ToDecimal().Should().Be(1200m);

        var applied = bus.Published
            .Where(e => e.Type == SanguoRandomEventApplied.EventType)
            .Select(ReadRandomEventAppliedJson)
            .Single();

        applied.TryGetProperty("EffectKind", out var kind).Should().BeTrue();
        kind.GetString().Should().Be("moneyDelta");
        applied.TryGetProperty("MoneyDelta", out var md).Should().BeTrue();
        md.GetInt32().Should().Be(200);
    }

    // ACC:T56.3
    [Fact]
    public async Task ShouldWriteEventStepDeltaAndClampEffectiveSteps_WhenEffectKindIsEconomyStepDelta()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        // Pick index=2 => c_step in sorted candidates: a_bad, b_money, c_step
        var rng = new QueueRng(nextInts: new[] { 2 }, fixedNextDouble: 1.0);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: rng,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            randomEventsCatalog: BuildCatalogWithInvalidFirst(),
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

        await AdvanceUntilOneGlobalEventAsync(mgr, 5);

        var applied = bus.Published
            .Where(e => e.Type == SanguoRandomEventApplied.EventType)
            .Select(ReadRandomEventAppliedJson)
            .Single();

        applied.TryGetProperty("EffectKind", out var kind).Should().BeTrue();
        kind.GetString().Should().Be("economyStepDelta");
        applied.TryGetProperty("StepDelta", out var sd).Should().BeTrue();
        sd.GetInt32().Should().Be(1);

        applied.TryGetProperty("AppliedMultipliersAfter", out var after).Should().BeTrue();
        after.ValueKind.Should().Be(JsonValueKind.Object);

        after.TryGetProperty("EventStepDelta", out var eventDelta).Should().BeTrue();
        eventDelta.GetInt32().Should().Be(1);

        after.TryGetProperty("EffectiveSteps", out var effectiveSteps).Should().BeTrue();
        var effective = effectiveSteps.GetInt32();
        effective.Should().BeInRange(1, 6);

        after.TryGetProperty("Sources", out var sources).Should().BeTrue();
        sources.GetInt32().Should().NotBe(0);
    }

    // ACC:T56.3
    [Fact]
    public async Task ShouldEliminatePlayerAndClampMoneyToZero_WhenMoneyDeltaWouldGoNegative()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var catalog = new SanguoRandomEventsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Events: new[]
            {
                new SanguoRandomEventCatalogEntry(
                    EventId: "money_penalty",
                    NameKey: "event.penalty.name",
                    DescriptionKey: "event.penalty.desc",
                    EffectKind: "moneyDelta",
                    MoneyDelta: -2000,
                    StepDelta: null,
                    CooldownRounds: 0,
                    UniqueOnce: false),
            },
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(PoolId: "default", EventIds: new[] { "money_penalty" }),
                new SanguoRandomEventPoolCatalogEntry(PoolId: "global", EventIds: new[] { "money_penalty" }),
            });

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new QueueRng(nextInts: new[] { 0 }, fixedNextDouble: 1.0),
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            randomEventsCatalog: catalog,
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

        await AdvanceUntilOneGlobalEventAsync(mgr, 5);

        p1.Money.ToDecimal().Should().Be(0m);
        p1.IsEliminated.Should().BeTrue();
    }

    private static async Task AdvanceUntilOneGlobalEventAsync(SanguoTurnManager mgr, int intervalTurns)
    {
        for (var i = 0; i < intervalTurns; i++)
        {
            await mgr.AdvanceTurnAsync(correlationId: $"corr-adv-{i}", causationId: "ut.advance");
        }
    }

    private static JsonElement ReadRandomEventAppliedJson(DomainEvent evt)
    {
        evt.Data.Should().BeOfType<JsonElementEventData>();
        return ((JsonElementEventData)evt.Data!).Value;
    }

    private static SanguoRandomEventsCatalog BuildCatalogWithInvalidFirst()
    {
        return new SanguoRandomEventsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Events: new[]
            {
                new SanguoRandomEventCatalogEntry(
                    EventId: "a_bad",
                    NameKey: "event.bad.name",
                    DescriptionKey: "event.bad.desc",
                    EffectKind: "teleport",
                    MoneyDelta: 999,
                    StepDelta: null,
                    CooldownRounds: 0,
                    UniqueOnce: false),
                new SanguoRandomEventCatalogEntry(
                    EventId: "b_money",
                    NameKey: "event.money.name",
                    DescriptionKey: "event.money.desc",
                    EffectKind: "moneyDelta",
                    MoneyDelta: 200,
                    StepDelta: null,
                    CooldownRounds: 0,
                    UniqueOnce: false),
                new SanguoRandomEventCatalogEntry(
                    EventId: "c_step",
                    NameKey: "event.step.name",
                    DescriptionKey: "event.step.desc",
                    EffectKind: "economyStepDelta",
                    MoneyDelta: null,
                    StepDelta: 1,
                    CooldownRounds: 0,
                    UniqueOnce: false),
            },
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(
                    PoolId: "default",
                    EventIds: new[] { "c_step", "b_money", "a_bad" }),
                new SanguoRandomEventPoolCatalogEntry(
                    PoolId: "global",
                    EventIds: new[] { "c_step", "b_money", "a_bad" }),
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

    private sealed class QueueRng : IRandomNumberGenerator
    {
        private readonly Queue<int> _nextInts;
        private readonly double _fixedNextDouble;

        public QueueRng(IEnumerable<int> nextInts, double fixedNextDouble)
        {
            _nextInts = new Queue<int>(nextInts ?? Array.Empty<int>());
            _fixedNextDouble = fixedNextDouble;
        }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            if (_nextInts.Count == 0)
            {
                return minInclusive;
            }

            var requested = _nextInts.Dequeue();
            var range = maxExclusive - minInclusive;
            if (range <= 0)
            {
                return minInclusive;
            }

            var normalized = Math.Abs(requested) % range;
            return minInclusive + normalized;
        }

        public double NextDouble() => _fixedNextDouble;
    }
}

