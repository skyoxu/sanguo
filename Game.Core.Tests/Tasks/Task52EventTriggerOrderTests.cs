using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Services;
using Game.Core.Utilities;
using System.Security.Cryptography;
using System.Text;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task52EventTriggerOrderTests
{
    private static readonly SanguoEconomyRules Rules = new(
        maxPriceSteps: SanguoEconomyRules.DefaultMaxPriceSteps,
        maxTollSteps: SanguoEconomyRules.DefaultMaxTollSteps);

    private static readonly SanguoRandomEventsCatalog RandomEventsCatalog = new(
        SchemaVersion: 1,
        Version: 1,
        Events: new[]
        {
            new SanguoRandomEventCatalogEntry(
                EventId: "event_economy_boost_a",
                NameKey: "event.event_economy_boost_a.name",
                DescriptionKey: "event.event_economy_boost_a.desc",
                EffectKind: "economyStepDelta",
                MoneyDelta: null,
                StepDelta: 1,
                CooldownRounds: 0,
                UniqueOnce: false),
            new SanguoRandomEventCatalogEntry(
                EventId: "event_economy_boost_b",
                NameKey: "event.event_economy_boost_b.name",
                DescriptionKey: "event.event_economy_boost_b.desc",
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
                EventIds: new[] { "event_economy_boost_a", "event_economy_boost_b" }),
        });

    private static string ComputeSha256Hex(string value)
    {
        var bytes = Encoding.UTF8.GetBytes(value);
        var hash = SHA256.HashData(bytes);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    private static readonly string DefaultPoolCandidatesSortedIdsHash = ComputeSha256Hex(
        string.Join("\n", new[] { "event_economy_boost_a", "event_economy_boost_b" }));

    private static bool HasRngContextToken(DomainEvent evt, string token)
    {
        var data = (evt.Data as JsonElementEventData)?.Value;
        if (!data.HasValue)
            return false;

        if (!data.Value.TryGetProperty("RngContextId", out var rngContextId))
            return false;

        return (rngContextId.GetString() ?? string.Empty).Contains(token, StringComparison.Ordinal);
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
        private readonly Queue<double> _doubles;

        public FixedRng(IEnumerable<int>? ints = null, IEnumerable<double>? doubles = null)
        {
            _ints = new Queue<int>(ints ?? Array.Empty<int>());
            _doubles = new Queue<double>(doubles ?? Array.Empty<double>());
        }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            if (_ints.Count == 0)
                return minInclusive;
            return _ints.Dequeue();
        }

        public double NextDouble()
        {
            if (_doubles.Count == 0)
                return 1.0;
            return _doubles.Dequeue();
        }
    }

    private static (SanguoTurnManager manager, CapturingEventBus bus) CreateTurnManager(
        IRandomNumberGenerator rng,
        int totalPositionsHint = 10,
        int globalEventIntervalTurns = 5)
    {
        var players = new[]
        {
            new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: Rules),
        };
        var boardState = new SanguoBoardState(players: players, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));
        var treasury = new SanguoTreasury();

        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: rng,
            totalPositionsHint: totalPositionsHint,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            randomEventsCatalog: RandomEventsCatalog,
            globalEventIntervalTurns: globalEventIntervalTurns,
            randomEventPoolId: "default");

        return (manager, bus);
    }

    // acceptance: ACC:T52.2
    [Fact]
    public async Task ShouldPublishRandomEventApplied_WhenLandingOnNonCityTile()
    {
        // Force dice=1 so player lands on a non-city tile (no cities exist in this test board state).
        var (manager, bus) = CreateTurnManager(rng: new FixedRng(ints: new[] { 1 }));
        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 2026,
            month: 1,
            day: 1,
            correlationId: "c0",
            causationId: null);

        bus.Published.Clear();
        await manager.ExecuteHumanRollDiceAndResolveAsync(correlationId: "c1", causationId: null);

        bus.Published.Should().Contain(
            e => e.Type == SanguoRandomEventApplied.EventType,
            "Task52 requires that landing on an event tile triggers a random event (OnTileEvent) and emits core.sanguo.random_event.applied");

        var applied = bus.Published.First(e => e.Type == SanguoRandomEventApplied.EventType);
        var data = (applied.Data as JsonElementEventData)?.Value;
        data.HasValue.Should().BeTrue();
        if (data.HasValue)
        {
            data.Value.TryGetProperty("RngContextId", out var rngContextId).Should().BeTrue();
            rngContextId.GetString().Should().Contain("tile");

            data.Value.TryGetProperty("CandidatesSortedIdsHash", out var hash).Should().BeTrue();
            hash.GetString().Should().Be(DefaultPoolCandidatesSortedIdsHash);
        }
    }

    // acceptance: ACC:T52.2
    [Theory]
    [InlineData(5)]
    [InlineData(10)]
    [InlineData(20)]
    public async Task ShouldPublishRandomEventApplied_WhenGlobalTurnEventBoundaryIsHit(int globalEventIntervalTurns)
    {
        var (manager, bus) = CreateTurnManager(rng: new FixedRng(), globalEventIntervalTurns: globalEventIntervalTurns);
        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 2026,
            month: 1,
            day: 1,
            correlationId: "c0",
            causationId: null);

        bus.Published.Clear();

        // Drive turn advances; a global event should be emitted exactly at the configured boundary.
        for (var i = 0; i < globalEventIntervalTurns - 1; i++)
            await manager.AdvanceTurnAsync(correlationId: $"c-adv-{globalEventIntervalTurns}-{i}", causationId: null);

        bus.Published.Any(e => e.Type == SanguoRandomEventApplied.EventType && HasRngContextToken(e, "global"))
            .Should()
            .BeFalse("a global random event should only be triggered at the interval boundary");

        await manager.AdvanceTurnAsync(correlationId: $"c-adv-{globalEventIntervalTurns}-boundary", causationId: null);

        bus.Published.Should().Contain(
            e => e.Type == SanguoRandomEventApplied.EventType,
            "Task52 requires that OnGlobalTurnEvent triggers every N turns (N in {5,10,20}) and emits core.sanguo.random_event.applied");

        var globalApplied = bus.Published.FirstOrDefault(
            e => e.Type == SanguoRandomEventApplied.EventType && HasRngContextToken(e, "global"));
        globalApplied.Should().NotBeNull();

        var globalData = (globalApplied!.Data as JsonElementEventData)?.Value;
        globalData.HasValue.Should().BeTrue();
        if (globalData.HasValue)
        {
            globalData.Value.TryGetProperty("CandidatesSortedIdsHash", out var hash).Should().BeTrue();
            hash.GetString().Should().Be(DefaultPoolCandidatesSortedIdsHash);
        }
    }
}
