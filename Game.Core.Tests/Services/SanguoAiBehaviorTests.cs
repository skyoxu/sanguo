using System;
using System.Collections.Generic;
using System.Linq;
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

namespace Game.Core.Tests.Services;

public sealed class SanguoAiBehaviorTests
{
    // ACC:T11.1
    [Fact]
    public void ShouldNotReferenceGodotAssemblies_WhenUsingAiBehaviorInGameCore()
    {
        var referenced = typeof(SanguoTurnManager).Assembly.GetReferencedAssemblies();
        referenced.Should().NotContain(a => a.Name != null && a.Name.StartsWith("Godot", StringComparison.OrdinalIgnoreCase));
    }

    // ACC:T11.3
    [Fact]
    public async Task ShouldPublishAiDecisionMadeWithRollDice_WhenTurnStartsForAi()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var gameId = "game-1";
        var humanId = "p1";
        var aiId = "ai-1";
        var correlationId = "corr-1";

        var rules = SanguoEconomyRules.Default;
        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromMajorUnits(100), baseToll: Money.FromMajorUnits(10), positionIndex: 3),
        };

        var human = new SanguoPlayer(playerId: humanId, money: 200m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: aiId, money: 200m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { human, ai }, citiesById: cities);
        var treasury = new SanguoTreasury();

        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            rng: new FixedRng(3),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: gameId,
            playerOrder: new[] { humanId, aiId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId,
            causationId: null);

        await mgr.AdvanceTurnAsync(correlationId, causationId: "cmd-advance");

        var decisionEvent = bus.Published.LastOrDefault(e => e.Type == SanguoAiDecisionMade.EventType);
        decisionEvent.Should().NotBeNull("AI decision event should be published when it becomes the AI player's turn");

        var payload = GetJsonPayload(decisionEvent!);
        payload.GetProperty("GameId").GetString().Should().Be(gameId);
        payload.GetProperty("AiPlayerId").GetString().Should().Be(aiId);
        payload.GetProperty("DecisionType").GetString().Should().Be("RollDice");
        payload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);
        payload.GetProperty("CausationId").GetString().Should().Be("cmd-advance");
    }

    [Fact]
    public async Task ShouldNotPublishAiDecisionMade_WhenTurnStartsForHuman()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var gameId = "game-1";
        var humanId = "p1";
        var aiId = "ai-1";
        var correlationId = "corr-human-1";

        var rules = SanguoEconomyRules.Default;
        var cities = new Dictionary<string, City>(StringComparer.Ordinal);
        var human = new SanguoPlayer(playerId: humanId, money: 200m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: aiId, money: 200m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { human, ai }, citiesById: cities);
        var treasury = new SanguoTreasury();

        var mgr = new SanguoTurnManager(bus, economy, boardState, treasury);
        await mgr.StartNewGameAsync(
            gameId: gameId,
            playerOrder: new[] { humanId, aiId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId,
            causationId: null);

        bus.Published.Should().NotContain(e => e.Type == SanguoAiDecisionMade.EventType);
    }

    // ACC:T11.5
    // ACC:T11.6
    [Fact]
    public async Task ShouldUseSnapshotView_WhenCallingDecisionPolicy()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var policy = new CapturingDecisionPolicy();

        var gameId = "game-1";
        var humanId = "p1";
        var aiId = "ai-1";
        var correlationId = "corr-2";

        var rules = SanguoEconomyRules.Default;
        var cities = new Dictionary<string, City>(StringComparer.Ordinal);
        var human = new SanguoPlayer(playerId: humanId, money: 200m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: aiId, money: 200m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { human, ai }, citiesById: cities);
        var treasury = new SanguoTreasury();

        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            aiDecisionPolicy: policy,
            rng: new FixedRng(1),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: gameId,
            playerOrder: new[] { humanId, aiId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId,
            causationId: null);

        await mgr.AdvanceTurnAsync(correlationId, causationId: "cmd-advance");

        policy.Captured.Should().NotBeNull();
        policy.Captured!.PlayerId.Should().Be(aiId);
        policy.Captured.GetType().Should().Be(typeof(SanguoPlayerView), "decision policy should receive an immutable snapshot view");
    }

    // ACC:T11.6
    [Fact]
    public async Task ShouldSupportDecisionPolicyInjection_WhenProvidingSkipPolicy()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var gameId = "game-1";
        var humanId = "p1";
        var aiId = "ai-1";
        var correlationId = "corr-3";

        var rules = SanguoEconomyRules.Default;
        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromMajorUnits(100), baseToll: Money.FromMajorUnits(10), positionIndex: 3),
        };
        var human = new SanguoPlayer(playerId: humanId, money: 200m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: aiId, money: 200m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { human, ai }, citiesById: cities);
        var treasury = new SanguoTreasury();

        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            aiDecisionPolicy: new AlwaysDecisionPolicy(SanguoAiDecisionType.Skip),
            rng: new FixedRng(3),
            totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: gameId,
            playerOrder: new[] { humanId, aiId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId,
            causationId: null);

        await mgr.AdvanceTurnAsync(correlationId, causationId: "cmd-advance");

        var decisionEvent = bus.Published.LastOrDefault(e => e.Type == SanguoAiDecisionMade.EventType);
        decisionEvent.Should().NotBeNull();

        var payload = GetJsonPayload(decisionEvent!);
        payload.GetProperty("GameId").GetString().Should().Be(gameId);
        payload.GetProperty("AiPlayerId").GetString().Should().Be(aiId);
        payload.GetProperty("DecisionType").GetString().Should().Be("Skip");
        payload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);
        payload.GetProperty("CausationId").GetString().Should().Be("cmd-advance");

        bus.Published.Should().NotContain(e => e.Type == SanguoDiceRolled.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoTokenMoved.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoCityBought.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoCityTollPaid.EventType);
    }

    private static JsonElement GetJsonPayload(DomainEvent evt)
    {
        evt.Data.Should().BeOfType<JsonElementEventData>();
        return ((JsonElementEventData)evt.Data!).Value;
    }

    private sealed class AlwaysDecisionPolicy : ISanguoAiDecisionPolicy
    {
        private readonly SanguoAiDecisionType _decisionType;
        public AlwaysDecisionPolicy(SanguoAiDecisionType decisionType) => _decisionType = decisionType;
        public SanguoAiDecision Decide(ISanguoPlayerView self) => new(_decisionType);
    }

    private sealed class CapturingDecisionPolicy : ISanguoAiDecisionPolicy
    {
        public ISanguoPlayerView? Captured { get; private set; }
        public SanguoAiDecision Decide(ISanguoPlayerView self)
        {
            Captured = self;
            return new SanguoAiDecision(SanguoAiDecisionType.Skip);
        }
    }

    private sealed class FixedRng : IRandomNumberGenerator
    {
        private readonly Queue<int> _nextInts;

        public FixedRng(params int[] nextInts)
        {
            _nextInts = new Queue<int>(nextInts ?? Array.Empty<int>());
        }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            if (_nextInts.Count == 0)
                return minInclusive;

            var value = _nextInts.Dequeue();
            if (value < minInclusive)
                return minInclusive;
            if (value >= maxExclusive)
                return maxExclusive - 1;
            return value;
        }

        public double NextDouble() => 0.0;
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
