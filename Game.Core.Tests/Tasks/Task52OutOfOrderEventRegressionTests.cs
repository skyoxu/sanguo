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
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task52OutOfOrderEventRegressionTests
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

    private static (SanguoTurnManager manager, CapturingEventBus bus) CreateTurnManager(IRandomNumberGenerator rng, int totalPositionsHint = 10)
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
            globalEventIntervalTurns: 5,
            randomEventPoolId: "default");

        return (manager, bus);
    }

    // acceptance: ACC:T52.3
    // intent: when both tile event and global turn event are triggered in the same turn, ordering must be stable and replayable from event log.
    [Fact]
    public async Task ShouldBeOrderedAndReplayable_WhenTileAndGlobalEventsTriggeredSameTurn()
    {
        // ints are consumed in order: dice roll, tile pick, global pick.
        var (manager, bus) = CreateTurnManager(rng: new FixedRng(ints: new[] { 1, 0, 1 }));
        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 2026,
            month: 1,
            day: 1,
            correlationId: "c0",
            causationId: null);

        // Move to a turn where a global event boundary is expected (interval in {5,10,20}; implementation must be fixed and testable).
        for (var i = 0; i < 4; i++)
            await manager.AdvanceTurnAsync(correlationId: $"c-adv-{i}", causationId: null);

        bus.Published.Clear();
        await manager.ExecuteHumanRollDiceAndResolveAsync(correlationId: "c-roll", causationId: null);
        await manager.AdvanceTurnAsync(correlationId: "c-adv-final", causationId: null);

        var applied = bus.Published.Where(e => e.Type == SanguoRandomEventApplied.EventType).ToArray();
        applied.Length.Should().Be(
            2,
            "when both OnTileEvent and OnGlobalTurnEvent fire within the same turn, two random_event.applied events must be emitted so the ordering is replayable");

        // Stop-loss replay convention: RngContextId should encode the source (tile/global) and be ordered accordingly.
        var firstCtx = ((applied[0].Data as JsonElementEventData)?.Value.TryGetProperty("RngContextId", out var c0) ?? false)
            ? c0.GetString()
            : null;
        var secondCtx = ((applied[1].Data as JsonElementEventData)?.Value.TryGetProperty("RngContextId", out var c1) ?? false)
            ? c1.GetString()
            : null;

        firstCtx.Should().NotBeNull();
        secondCtx.Should().NotBeNull();
        firstCtx!.Should().Contain("tile", "tile event must be applied before global event in the same turn");
        secondCtx!.Should().Contain("global", "global event must be applied after tile event in the same turn");

        var firstData = (applied[0].Data as JsonElementEventData)?.Value;
        var secondData = (applied[1].Data as JsonElementEventData)?.Value;
        firstData.HasValue.Should().BeTrue();
        secondData.HasValue.Should().BeTrue();
        if (firstData.HasValue && secondData.HasValue)
        {
            firstData.Value.TryGetProperty("CandidatesSortedIdsHash", out var h0).Should().BeTrue();
            secondData.Value.TryGetProperty("CandidatesSortedIdsHash", out var h1).Should().BeTrue();
            h0.GetString().Should().NotBeNull();
            h1.GetString().Should().NotBeNull();
            h0.GetString().Should().Be(h1.GetString(), "both triggers must use the same RandomEventPool candidate set");

            firstData.Value.TryGetProperty("PickedIndex", out var i0).Should().BeTrue();
            secondData.Value.TryGetProperty("PickedIndex", out var i1).Should().BeTrue();
            i0.GetInt32().Should().Be(0);
            i1.GetInt32().Should().Be(1, "global draw should consume the next RNG value after tile draw");
        }
    }
}
