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

public sealed class Task59CombatTriggerAndReturnTests
{
    // ACC:T59.1
    [Fact]
    public void ShouldExposeStableEventType_WhenCombatStarts()
    {
        SanguoCombatStarted.EventType.Should().Be("core.sanguo.combat.started");
    }

    // ACC:T59.2
    [Fact]
    public void ShouldIncludeRandomSeed_WhenCombatStarts()
    {
        var evt = new SanguoCombatStarted(
            GameId: "g1",
            PlayerId: "p1",
            EncounterId: "enc_01",
            RandomSeed: 123,
            OccurredAt: DateTimeOffset.UnixEpoch,
            CorrelationId: "corr_01",
            CausationId: null
        );

        evt.RandomSeed.Should().Be(123);
        evt.EncounterId.Should().Be("enc_01");
    }

    // ACC:T59.4
    [Fact]
    public void ShouldAllowCorrelatingStartAndEnd_WhenSameEncounter()
    {
        var correlationId = "corr_01";
        var started = new SanguoCombatStarted(
            GameId: "g1",
            PlayerId: "p1",
            EncounterId: "enc_01",
            RandomSeed: 7,
            OccurredAt: DateTimeOffset.UnixEpoch,
            CorrelationId: correlationId,
            CausationId: "cause_01"
        );

        var ended = new SanguoCombatEnded(
            GameId: started.GameId,
            PlayerId: started.PlayerId,
            EncounterId: started.EncounterId,
            Result: new SanguoCombatResult("win", 50m, EncounterTarget: 10, EffectiveCombatRating: 12),
            OccurredAt: DateTimeOffset.UnixEpoch.AddSeconds(1),
            CorrelationId: started.CorrelationId,
            CausationId: started.CausationId
        );

        ended.CorrelationId.Should().Be(correlationId);
        ended.EncounterId.Should().Be("enc_01");
    }

    // ACC:T59.5
    [Fact]
    public void ShouldCarryOutcomeAndMoneyDelta_WhenCombatEnds()
    {
        var ended = new SanguoCombatEnded(
            GameId: "g1",
            PlayerId: "p1",
            EncounterId: "enc_01",
            Result: new SanguoCombatResult("win", 50m, EncounterTarget: 10, EffectiveCombatRating: 12),
            OccurredAt: DateTimeOffset.UnixEpoch,
            CorrelationId: "corr_01",
            CausationId: null
        );

        ended.Result.Outcome.Should().Be("win");
        ended.Result.MoneyDelta.Should().Be(50m);
    }

    // ACC:T59.6
    [Fact]
    public void ShouldExposeStableEventType_WhenCombatEnds()
    {
        SanguoCombatEnded.EventType.Should().Be("core.sanguo.combat.ended");
    }

    // ACC:T59.1
    // ACC:T59.2
    // ACC:T59.5
    [Fact]
    public async Task ShouldPublishCombatEventsAndApplyMoneyBackToPlayerState_WhenStartCombatActionIsExecuted()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var player = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { player }, citiesById: new Dictionary<string, City>());
        var treasury = new SanguoTreasury();

        var tileTypes = new Dictionary<int, string>
        {
            [0] = SanguoTileDefinition.TileTypePass,
        };

        var combatRating = new Dictionary<string, int>(StringComparer.Ordinal) { ["p1"] = 100 };

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new DeterministicRandomNumberGenerator(seed: 7),
            randomSeed: 7,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            tileTypesByPositionIndex: tileTypes,
            combatRatingByPlayerId: combatRating);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr_start",
            causationId: "ut.start");

        await mgr.ExecuteHumanTileActionAsync(action: "start_combat", correlationId: "corr_59", causationId: "ut.action");

        var started = bus.Published.SingleOrDefault(x => x.Type == SanguoCombatStarted.EventType);
        started.Should().NotBeNull();

        var ended = bus.Published.SingleOrDefault(x => x.Type == SanguoCombatEnded.EventType);
        ended.Should().NotBeNull();

        var startedJson = ((JsonElementEventData)started!.Data!).Value;
        var endedJson = ((JsonElementEventData)ended!.Data!).Value;

        var startedEncounterId = startedJson.GetProperty("EncounterId").GetString();
        startedEncounterId.Should().NotBeNullOrWhiteSpace();
        endedJson.GetProperty("EncounterId").GetString().Should().Be(startedEncounterId);

        startedJson.GetProperty("CorrelationId").GetString().Should().Be("corr_59");
        endedJson.GetProperty("CorrelationId").GetString().Should().Be("corr_59");

        startedJson.GetProperty("RandomSeed").GetInt32().Should().BeGreaterThan(0);

        var stateChanged = bus.Published
            .Where(x => x.Type == SanguoPlayerStateChanged.EventType)
            .Select(x => ((JsonElementEventData)x.Data!).Value)
            .LastOrDefault(x => x.TryGetProperty("PlayerId", out var pid) && pid.GetString() == "p1");

        stateChanged.ValueKind.Should().NotBe(JsonValueKind.Undefined);
        stateChanged.GetProperty("CorrelationId").GetString().Should().Be("corr_59");

        player.Money.ToDecimal().Should().BeGreaterThan(300m);
    }

    [Fact]
    public async Task ShouldPublishCombatEventsButNotChangeMoney_WhenCombatIsLost()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var player = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { player }, citiesById: new Dictionary<string, City>());
        var treasury = new SanguoTreasury();

        var tileTypes = new Dictionary<int, string> { [0] = SanguoTileDefinition.TileTypePass };
        var combatRating = new Dictionary<string, int>(StringComparer.Ordinal) { ["p1"] = 0 };

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new DeterministicRandomNumberGenerator(seed: 7),
            randomSeed: 7,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            tileTypesByPositionIndex: tileTypes,
            combatRatingByPlayerId: combatRating);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr_start",
            causationId: "ut.start");

        await mgr.ExecuteHumanTileActionAsync(action: "start_combat", correlationId: "corr_lose", causationId: "ut.action");

        bus.Published.Should().Contain(x => x.Type == SanguoCombatStarted.EventType);
        bus.Published.Should().Contain(x => x.Type == SanguoCombatEnded.EventType);

        player.Money.ToDecimal().Should().Be(300m);

        bus.Published
            .Where(x => x.Type == SanguoPlayerStateChanged.EventType)
            .Select(x => ((JsonElementEventData)x.Data!).Value)
            .Any(x => x.TryGetProperty("CorrelationId", out var c) && c.GetString() == "corr_lose")
            .Should().BeFalse();
    }

    [Fact]
    public async Task ShouldNotStartCombat_WhenNotOnFacilityTile()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var player = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { player }, citiesById: new Dictionary<string, City>());
        var treasury = new SanguoTreasury();

        var tileTypes = new Dictionary<int, string> { [0] = SanguoTileDefinition.TileTypeCity };
        var combatRating = new Dictionary<string, int>(StringComparer.Ordinal) { ["p1"] = 100 };

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new DeterministicRandomNumberGenerator(seed: 7),
            randomSeed: 7,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            tileTypesByPositionIndex: tileTypes,
            combatRatingByPlayerId: combatRating);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr_start",
            causationId: "ut.start");

        await mgr.ExecuteHumanTileActionAsync(action: "start_combat", correlationId: "corr_ignore", causationId: "ut.action");

        bus.Published.Should().NotContain(x => x.Type == SanguoCombatStarted.EventType);
        bus.Published.Should().NotContain(x => x.Type == SanguoCombatEnded.EventType);
    }

    [Fact]
    public async Task ShouldDepositOverflowToTreasury_WhenCombatRewardWouldExceedMoneyCap()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var player = new SanguoPlayer(playerId: "p1", money: 99_999_999m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { player }, citiesById: new Dictionary<string, City>());
        var treasury = new SanguoTreasury();

        var tileTypes = new Dictionary<int, string> { [0] = SanguoTileDefinition.TileTypePass };
        var combatRating = new Dictionary<string, int>(StringComparer.Ordinal) { ["p1"] = 100 };

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new DeterministicRandomNumberGenerator(seed: 7),
            randomSeed: 7,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            tileTypesByPositionIndex: tileTypes,
            combatRatingByPlayerId: combatRating);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr_start",
            causationId: "ut.start");

        treasury.MinorUnits.Should().Be(0);

        await mgr.ExecuteHumanTileActionAsync(action: "start_combat", correlationId: "corr_overflow", causationId: "ut.action");

        player.Money.ToDecimal().Should().Be(99_999_999m);
        treasury.MinorUnits.Should().BeGreaterThan(0);
    }

    [Fact]
    public async Task ShouldIgnoreStartCombat_WhenTileTypeMappingIsMissing()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var player = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { player }, citiesById: new Dictionary<string, City>());
        var treasury = new SanguoTreasury();

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new DeterministicRandomNumberGenerator(seed: 7),
            randomSeed: 7,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            tileTypesByPositionIndex: null,
            combatRatingByPlayerId: new Dictionary<string, int>(StringComparer.Ordinal) { ["p1"] = 100 });

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr_start",
            causationId: "ut.start");

        await mgr.ExecuteHumanTileActionAsync(action: "start_combat", correlationId: "corr_missing", causationId: "ut.action");

        bus.Published.Should().NotContain(x => x.Type == SanguoCombatStarted.EventType);
        bus.Published.Should().NotContain(x => x.Type == SanguoCombatEnded.EventType);
    }

    [Fact]
    public async Task ShouldIgnoreStartCombat_WhenTileTypeIsUnknownForCurrentPosition()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var player = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { player }, citiesById: new Dictionary<string, City>());
        var treasury = new SanguoTreasury();

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new DeterministicRandomNumberGenerator(seed: 7),
            randomSeed: 7,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            tileTypesByPositionIndex: new Dictionary<int, string>(),
            combatRatingByPlayerId: new Dictionary<string, int>(StringComparer.Ordinal) { ["p1"] = 100 });

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr_start",
            causationId: "ut.start");

        await mgr.ExecuteHumanTileActionAsync(action: "start_combat", correlationId: "corr_missing2", causationId: "ut.action");

        bus.Published.Should().NotContain(x => x.Type == SanguoCombatStarted.EventType);
        bus.Published.Should().NotContain(x => x.Type == SanguoCombatEnded.EventType);
    }

    [Fact]
    public async Task ShouldTriggerCombat_WhenTileRandomEventEffectIsStartCombat()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var player = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { player }, citiesById: new Dictionary<string, City>());
        var treasury = new SanguoTreasury();

        var tileTypes = new Dictionary<int, string>
        {
            [0] = SanguoTileDefinition.TileTypeEmpty,
            [1] = SanguoTileDefinition.TileTypeEvent,
        };

        var randomEventsCatalog = new SanguoRandomEventsCatalog(
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
                new SanguoRandomEventPoolCatalogEntry(PoolId: "default", EventIds: new[] { "event_combat_small" }),
                new SanguoRandomEventPoolCatalogEntry(PoolId: "global", EventIds: new[] { "event_combat_small" }),
            });

        var combatRating = new Dictionary<string, int>(StringComparer.Ordinal) { ["p1"] = 100 };

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new FixedRng(ints: new[] { 1 }),
            randomSeed: 7,
            totalPositionsHint: 2,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            randomEventsCatalog: randomEventsCatalog,
            globalEventIntervalTurns: 5,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global",
            tileTypesByPositionIndex: tileTypes,
            combatRatingByPlayerId: combatRating);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr_start",
            causationId: "ut.start");

        bus.Published.Clear();
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr_59_re", causationId: "ut.roll");

        var applied = bus.Published.FirstOrDefault(e => e.Type == SanguoRandomEventApplied.EventType);
        applied.Should().NotBeNull();

        var started = bus.Published.FirstOrDefault(e => e.Type == SanguoCombatStarted.EventType);
        var ended = bus.Published.FirstOrDefault(e => e.Type == SanguoCombatEnded.EventType);
        started.Should().NotBeNull();
        ended.Should().NotBeNull();

        var appliedJson = ((JsonElementEventData)applied!.Data!).Value;
        appliedJson.GetProperty("EffectKind").GetString().Should().Be(SanguoEffectKinds.StartCombat);
        appliedJson.GetProperty("EncounterId").GetString().Should().Be("enc_event_combat_small");
        appliedJson.GetProperty("EncounterTarget").GetInt32().Should().Be(10);

        var startedJson = ((JsonElementEventData)started!.Data!).Value;
        startedJson.GetProperty("CausationId").GetString().Should().Be(applied.Id);

        player.Money.ToDecimal().Should().BeGreaterThan(300m);
    }

    [Fact]
    public async Task ShouldRejectTileRandomEventStartCombat_WhenEncounterFieldsMissing()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var player = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { player }, citiesById: new Dictionary<string, City>());
        var treasury = new SanguoTreasury();

        var tileTypes = new Dictionary<int, string>
        {
            [0] = SanguoTileDefinition.TileTypeEmpty,
            [1] = SanguoTileDefinition.TileTypeEvent,
        };

        var randomEventsCatalog = new SanguoRandomEventsCatalog(
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
                    EncounterId: null,
                    EncounterTarget: null),
            },
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(PoolId: "default", EventIds: new[] { "event_combat_small" }),
                new SanguoRandomEventPoolCatalogEntry(PoolId: "global", EventIds: new[] { "event_combat_small" }),
            });

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new FixedRng(ints: new[] { 1 }),
            randomSeed: 7,
            totalPositionsHint: 2,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            randomEventsCatalog: randomEventsCatalog,
            globalEventIntervalTurns: 5,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global",
            tileTypesByPositionIndex: tileTypes,
            combatRatingByPlayerId: new Dictionary<string, int>(StringComparer.Ordinal) { ["p1"] = 100 });

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr_start",
            causationId: "ut.start");

        bus.Published.Clear();
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr_59_reject", causationId: "ut.roll");

        bus.Published.Should().NotContain(e => e.Type == SanguoCombatStarted.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoCombatEnded.EventType);

        var rejected = bus.Published.FirstOrDefault(e => e.Type == SanguoRandomEventRejected.EventType);
        rejected.Should().NotBeNull();

        var rejectedJson = ((JsonElementEventData)rejected!.Data!).Value;
        rejectedJson.GetProperty("RejectReason").GetString().Should().Be("missing_encounter_fields");
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

    private sealed class FixedRng : IRandomNumberGenerator
    {
        private readonly Queue<int> _ints;

        public FixedRng(IEnumerable<int> ints)
        {
            _ints = new Queue<int>(ints ?? Array.Empty<int>());
        }

        public int NextInt(int minInclusive, int maxInclusive)
        {
            if (_ints.Count == 0)
            {
                return minInclusive;
            }

            var v = _ints.Dequeue();
            if (v < minInclusive) return minInclusive;
            if (v > maxInclusive) return maxInclusive;
            return v;
        }

        public double NextDouble()
        {
            if (_ints.Count == 0)
            {
                return 0.0;
            }
            var v = _ints.Dequeue();
            return (v % 1000) / 1000.0;
        }
    }
}

