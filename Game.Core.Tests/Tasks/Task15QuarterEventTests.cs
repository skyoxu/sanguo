using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Game.Core.Utilities;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task15QuarterEventTests
{
    // ACC:T15.1
    [Fact]
    public void ShouldNotReferenceGodotAssemblies_WhenUsingQuarterEventInGameCore()
    {
        var referenced = typeof(SanguoEconomyManager).Assembly.GetReferencedAssemblies();
        referenced.Should().NotContain(a => a.Name != null && a.Name.StartsWith("Godot", StringComparison.OrdinalIgnoreCase));
    }

    // ACC:T15.2
    [Fact]
    public void ShouldExposeEventTypeConstant_WhenUsingSeasonEventAppliedContract()
    {
        SanguoSeasonEventApplied.EventType.Should().Be("core.sanguo.economy.season.event.applied");
    }

    // ACC:T15.2
    [Fact]
    public async Task ShouldPublishSeasonEventApplied_WhenCrossingQuarterBoundary()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var occurredAt = new DateTimeOffset(2026, 1, 2, 0, 0, 0, TimeSpan.Zero);

        await economy.PublishSeasonEventIfBoundaryAsync(
            gameId: "game-1",
            previousDate: new SanguoCalendarDate(year: 1, month: 3, day: 30),
            currentDate: new SanguoCalendarDate(year: 1, month: 4, day: 1),
            season: 2,
            affectedRegionIds: new[] { "r1", "r2" },
            yieldMultiplier: 0.9m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: occurredAt);

        bus.Published.Should().ContainSingle(e => e.Type == SanguoSeasonEventApplied.EventType);
        var evt = bus.Published.Find(e => e.Type == SanguoSeasonEventApplied.EventType);
        evt.Should().NotBeNull();

        evt!.Source.Should().Be(nameof(SanguoEconomyManager));
        evt.Data.Should().BeOfType<JsonElementEventData>();

        var payload = ((JsonElementEventData)evt.Data!).Value;
        payload.GetProperty("GameId").GetString().Should().Be("game-1");
        payload.GetProperty("Year").GetInt32().Should().Be(1);
        payload.GetProperty("Season").GetInt32().Should().Be(2);
        payload.GetProperty("YieldMultiplier").GetDecimal().Should().Be(0.9m);
        payload.GetProperty("OccurredAt").GetDateTimeOffset().Should().Be(occurredAt);
        payload.GetProperty("CorrelationId").GetString().Should().Be("corr-1");
        payload.GetProperty("CausationId").GetString().Should().Be("cmd-1");
        payload.GetProperty("AffectedRegionIds").ValueKind.Should().Be(JsonValueKind.Array);
        payload.GetProperty("AffectedRegionIds").GetArrayLength().Should().Be(2);
    }

    // ACC:T15.2
    [Fact]
    public async Task ShouldNotPublishSeasonEventApplied_WhenNotCrossingQuarterBoundary()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        await economy.PublishSeasonEventIfBoundaryAsync(
            gameId: "game-1",
            previousDate: new SanguoCalendarDate(year: 1, month: 4, day: 1),
            currentDate: new SanguoCalendarDate(year: 1, month: 4, day: 2),
            season: 2,
            affectedRegionIds: new[] { "r1" },
            yieldMultiplier: 1.0m,
            correlationId: "corr-1",
            causationId: null,
            occurredAt: DateTimeOffset.UtcNow);

        bus.Published.Should().BeEmpty();
    }

    // ACC:T15.3
    [Fact]
    public async Task ShouldNotCarryOverQuarterYieldAdjustment_WhenNewQuarterBegins()
    {
        var rng = new SequencedRng(
            nextDoubles: new[] { 0.0, 0.999999 },
            nextInts: new[] { 0 }
        );
        var bus = new CapturingEventBus();

        var player = new SanguoPlayer(playerId: "p1", money: 1_000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var boardState = new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal)
            {
                ["c1"] = new City("c1", "City1", "r1", Money.FromMajorUnits(1), Money.FromMajorUnits(10)),
                ["c2"] = new City("c2", "City2", "r2", Money.FromMajorUnits(1), Money.FromMajorUnits(20)),
            });
        boardState.TryBuyCity(buyerId: "p1", cityId: "c1", priceMultiplier: 1.0m).Should().BeTrue();
        boardState.TryBuyCity(buyerId: "p1", cityId: "c2", priceMultiplier: 1.0m).Should().BeTrue();

        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(bus, economy, boardState, new SanguoTreasury(), rng: rng, totalPositionsHint: 1);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 3,
            day: 30,
            correlationId: "corr",
            causationId: null);

        await mgr.AdvanceTurnAsync(correlationId: "corr", causationId: "cmd-q2-start");
        bus.Published.Should().Contain(e => e.Type == SanguoSeasonEventApplied.EventType);

        for (var i = 0; i < 120; i++)
            await mgr.AdvanceTurnAsync(correlationId: "corr", causationId: $"cmd-step-{i}");

        var julySettlement = TryGetMonthSettledPayload(bus.Published, month: 7);
        julySettlement.Should().NotBeNull("July month settlement must be published at the month boundary");

        var delta = GetSinglePlayerAmountDelta(julySettlement!.Value, playerId: "p1");
        delta.Should().Be(30m, "when the next quarter does not trigger a new event, the previous quarter yield adjustment must not carry over");
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

    private sealed class SequencedRng : IRandomNumberGenerator
    {
        private readonly Queue<double> _nextDoubles;
        private readonly Queue<int> _nextInts;

        public SequencedRng(IEnumerable<double> nextDoubles, IEnumerable<int> nextInts)
        {
            _nextDoubles = new Queue<double>(nextDoubles ?? Array.Empty<double>());
            _nextInts = new Queue<int>(nextInts ?? Array.Empty<int>());
        }

        public int TotalCalls { get; private set; }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            TotalCalls++;

            if (maxExclusive <= minInclusive)
                throw new ArgumentOutOfRangeException(nameof(maxExclusive), "maxExclusive must be > minInclusive.");

            if (_nextInts.Count == 0)
                return minInclusive;

            var v = _nextInts.Dequeue();
            var span = maxExclusive - minInclusive;
            return minInclusive + (Math.Abs(v) % span);
        }

        public double NextDouble()
        {
            TotalCalls++;
            return _nextDoubles.Count == 0 ? 0.999999 : _nextDoubles.Dequeue();
        }
    }

    private static JsonElement? TryGetMonthSettledPayload(IReadOnlyList<DomainEvent> published, int month)
    {
        foreach (var evt in published)
        {
            if (evt.Type != SanguoMonthSettled.EventType)
                continue;

            evt.Data.Should().BeOfType<JsonElementEventData>();
            var payload = ((JsonElementEventData)evt.Data!).Value;
            if (payload.GetProperty("Month").GetInt32() == month)
                return payload;
        }

        return null;
    }

    private static decimal GetSinglePlayerAmountDelta(JsonElement monthSettledPayload, string playerId)
    {
        foreach (var settlement in monthSettledPayload.GetProperty("PlayerSettlements").EnumerateArray())
        {
            if (string.Equals(settlement.GetProperty("PlayerId").GetString(), playerId, StringComparison.Ordinal))
                return settlement.GetProperty("AmountDelta").GetDecimal();
        }

        throw new InvalidOperationException($"Player settlement not found for playerId={playerId}.");
    }
}
