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

public sealed class Task52TurnPhaseWindowTests
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
            new SanguoRandomEventPoolCatalogEntry(
                PoolId: "global",
                EventIds: new[] { "event_economy_boost_a", "event_economy_boost_b" }),
        });

    private static readonly SanguoActionCardsCatalog ActionCardsCatalog = new(
        SchemaVersion: 1,
        Version: 1,
        Cards: new[]
        {
            new SanguoActionCardCatalogEntry(
                CardId: "card_1",
                NameKey: "card.card_1.name",
                DescriptionKey: "card.card_1.desc",
                EffectKind: "economyStepDelta",
                StepDelta: 1,
                DurationRounds: 3),
            new SanguoActionCardCatalogEntry(
                CardId: "card_2",
                NameKey: "card.card_2.name",
                DescriptionKey: "card.card_2.desc",
                EffectKind: "economyStepDelta",
                StepDelta: 1,
                DurationRounds: 3),
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

    private static (SanguoTurnManager manager, CapturingEventBus bus) CreateTurnManager(
        IRandomNumberGenerator rng,
        int totalPositionsHint = 10)
    {
        var players = new[]
        {
            new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: Rules),
        };
        var boardState = new SanguoBoardState(
            players: players,
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));
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
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global",
            actionCardsCatalog: ActionCardsCatalog);

        return (manager, bus);
    }

    // acceptance: ACC:T52.1
    [Fact]
    public async Task ShouldAllowAtMostOneActionCardPerTurn_WhenPlayingBeforeRoll()
    {
        var (manager, bus) = CreateTurnManager(rng: new FixedRng());
        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 2026,
            month: 1,
            day: 1,
            correlationId: "c0",
            causationId: null);

        bus.Published.Clear();

        var first = await manager.TryPlayHumanActionCardAsync(
            cardId: "card_1",
            correlationId: "c-card-1",
            causationId: null);
        first.Should().BeTrue();

        var second = await manager.TryPlayHumanActionCardAsync(
            cardId: "card_2",
            correlationId: "c-card-2",
            causationId: null);
        second.Should().BeFalse("only one action card is allowed per turn in TurnPhase.BeforeRoll");

        bus.Published.Should().ContainSingle(e => e.Type == SanguoActionCardPlayed.EventType);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoCardLost.EventType);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoActionCardPlayRejected.EventType);
        bus.Published
            .Where(e => string.Equals(TryGetCorrelationId(e), "c-card-2", StringComparison.Ordinal))
            .Should()
            .ContainSingle(e => e.Type == SanguoActionCardPlayRejected.EventType);

        var played = bus.Published.Single(e => e.Type == SanguoActionCardPlayed.EventType);
        var playedData = (played.Data as JsonElementEventData)?.Value;
        playedData.HasValue.Should().BeTrue();
        if (playedData.HasValue)
        {
            playedData.Value.TryGetProperty("EffectKind", out var effectKind).Should().BeTrue();
            playedData.Value.TryGetProperty("StepDelta", out var stepDelta).Should().BeTrue();
            playedData.Value.TryGetProperty("DurationRounds", out var durationRounds).Should().BeTrue();
            effectKind.GetString().Should().Be("economyStepDelta");
            stepDelta.GetInt32().Should().Be(1);
            durationRounds.GetInt32().Should().Be(3);
        }

        var rejected = bus.Published.Last(e => e.Type == SanguoActionCardPlayRejected.EventType);
        var data = (rejected.Data as JsonElementEventData)?.Value;
        data.HasValue.Should().BeTrue();
        if (data.HasValue)
        {
            data.Value.TryGetProperty("TurnNumber", out var turnNumber).Should().BeTrue();
            data.Value.TryGetProperty("RoundNumber", out var roundNumber).Should().BeTrue();
            data.Value.TryGetProperty("PlayerId", out var playerId).Should().BeTrue();
            data.Value.TryGetProperty("Phase", out var phase).Should().BeTrue();
            data.Value.TryGetProperty("CardId", out var cardId).Should().BeTrue();
            data.Value.TryGetProperty("ReasonCode", out var reason).Should().BeTrue();
            turnNumber.GetInt32().Should().Be(1);
            roundNumber.GetInt32().Should().Be(1);
            playerId.GetString().Should().Be("p1");
            phase.GetString().Should().Be(SanguoTurnPhase.BeforeRoll.ToString());
            cardId.GetString().Should().Be("card_2");
            reason.GetString().Should().Be(SanguoActionCardPlayRejected.ReasonAlreadyPlayedThisTurn);
        }
    }

    private static string? TryGetCorrelationId(DomainEvent evt)
    {
        var data = (evt.Data as JsonElementEventData)?.Value;
        if (!data.HasValue)
        {
            return null;
        }

        if (!data.Value.TryGetProperty("CorrelationId", out var correlation))
        {
            return null;
        }

        return correlation.GetString();
    }

    // acceptance: ACC:T52.4
    // intent: economy-affecting random events must be observable and expressed via step_delta (not direct multiplier mutation).
    [Fact]
    public async Task ShouldExposeStepDeltaAndAvoidMoneyDelta_WhenEffectKindIsEconomyStepDelta()
    {
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

        var applied = bus.Published.FirstOrDefault(e => e.Type == SanguoRandomEventApplied.EventType);
        applied.Should().NotBeNull("landing on an event tile should apply a random event and publish core.sanguo.random_event.applied");

        // Stop-loss expectation for the first implementation: for economyStepDelta effects, StepDelta is used and MoneyDelta remains null.
        var data = (applied!.Data as JsonElementEventData)?.Value;
        data.HasValue.Should().BeTrue("SanguoRandomEventApplied must carry JSON data");
        if (data.HasValue)
        {
            var root = data.Value;
            root.TryGetProperty("EffectKind", out var effectKind).Should().BeTrue();
            if (effectKind.ValueKind == System.Text.Json.JsonValueKind.String
                && string.Equals(effectKind.GetString(), "economyStepDelta", StringComparison.Ordinal))
            {
                root.TryGetProperty("StepDelta", out var stepDelta).Should().BeTrue();
                root.TryGetProperty("MoneyDelta", out var moneyDelta).Should().BeTrue();
                moneyDelta.ValueKind.Should().Be(System.Text.Json.JsonValueKind.Null);
                stepDelta.ValueKind.Should().Be(System.Text.Json.JsonValueKind.Number);

                root.TryGetProperty("AppliedMultipliersAfter", out var after).Should().BeTrue();
                after.ValueKind.Should().NotBe(System.Text.Json.JsonValueKind.Null);
                after.TryGetProperty("EventStepDelta", out var eventDelta).Should().BeTrue();
                after.TryGetProperty("EffectiveSteps", out var effectiveSteps).Should().BeTrue();
                eventDelta.GetInt32().Should().Be(stepDelta.GetInt32(), "random_event.applied must include a post-commit AppliedMultipliers snapshot for economyStepDelta");
                effectiveSteps.GetInt32().Should().Be(3);
            }
        }
    }

    // acceptance: ACC:T52.5
    // intent: with fixed seed/inputs, random event selection and ordering must be deterministic.
    [Fact]
    public async Task ShouldBeDeterministic_WhenRngAndInputsAreFixed()
    {
        static async Task<string?> RunOnceAsync()
        {
            var (manager, bus) = CreateTurnManager(rng: new FixedRng(ints: new[] { 1, 0, 1 }));
            await manager.StartNewGameAsync(
                gameId: "g1",
                playerOrder: new[] { "p1" },
                year: 2026,
                month: 1,
                day: 1,
                correlationId: "c0",
                causationId: null);

            for (var i = 0; i < 4; i++)
                await manager.AdvanceTurnAsync(correlationId: $"c-adv-{i}", causationId: null);

            bus.Published.Clear();
            await manager.ExecuteHumanRollDiceAndResolveAsync(correlationId: "c-roll", causationId: null);
            await manager.AdvanceTurnAsync(correlationId: "c-adv-final", causationId: null);

            var applied = bus.Published
                .Where(e => e.Type == SanguoRandomEventApplied.EventType)
                .ToArray();
            if (applied.Length != 2)
                return null;

            static string? ToSig(DomainEvent evt)
            {
                var data = (evt.Data as JsonElementEventData)?.Value;
                if (!data.HasValue)
                    return null;

                if (!data.Value.TryGetProperty("RngContextId", out var rngContextId))
                    return null;
                if (!data.Value.TryGetProperty("CandidatesSortedIdsHash", out var hash))
                    return null;
                if (!data.Value.TryGetProperty("PickedIndex", out var pickedIndex))
                    return null;
                if (!data.Value.TryGetProperty("PickedId", out var pickedId))
                    return null;
                if (!data.Value.TryGetProperty("AppliedMultipliersAfter", out var after))
                    return null;
                if (after.ValueKind == System.Text.Json.JsonValueKind.Null)
                    return null;
                if (!after.TryGetProperty("EventStepDelta", out var eventDelta))
                    return null;
                if (!after.TryGetProperty("EffectiveSteps", out var effectiveSteps))
                    return null;

                return $"{rngContextId.GetString()}|{hash.GetString()}|{pickedIndex.GetInt32()}|{pickedId.GetString()}|{eventDelta.GetInt32()}|{effectiveSteps.GetInt32()}";
            }

            var first = ToSig(applied[0]);
            var second = ToSig(applied[1]);
            if (first is null || second is null)
                return null;

            return first + "\n" + second;
        }

        var first = await RunOnceAsync();
        var second = await RunOnceAsync();

        first.Should().NotBeNull("random events must be emitted for determinism to be verifiable");
        second.Should().NotBeNull("random events must be emitted for determinism to be verifiable");
        first.Should().Be(second);
    }
}
