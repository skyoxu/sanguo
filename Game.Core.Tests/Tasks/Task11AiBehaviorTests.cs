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
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task11AiBehaviorTests
{
    [Fact]
    public async Task ShouldPublishAiDecisionMade_WhenTurnStartsForAi()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var gameId = "game-1";
        var humanId = "p1";
        var aiId = "ai-1";
        var playerOrder = new[] { humanId, aiId };
        var correlationId = "corr-1";

        var rules = new SanguoEconomyRules(
            maxPriceMultiplier: SanguoEconomyRules.DefaultMaxPriceMultiplier,
            maxTollMultiplier: SanguoEconomyRules.DefaultMaxTollMultiplier);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal);
        var human = new SanguoPlayer(playerId: humanId, money: 200m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: aiId, money: 200m, positionIndex: 0, economyRules: rules);

        var boardState = new SanguoBoardState(players: new[] { human, ai }, citiesById: cities);
        var treasury = new SanguoTreasury();
        var mgr = new SanguoTurnManager(bus, economy, boardState, treasury);

        await mgr.StartNewGameAsync(
            gameId: gameId,
            playerOrder: playerOrder,
            year: 1,
            month: 1,
            day: 1,
            correlationId: correlationId,
            causationId: null);

        await mgr.AdvanceTurnAsync(correlationId, causationId: "cmd-advance");

        var decision = bus.Published.Find(e => e.Type == SanguoAiDecisionMade.EventType);
        decision.Should().NotBeNull("Task 11 should publish an AI decision event when it becomes the AI player's turn");

        decision!.Data.Should().BeOfType<JsonElementEventData>();
        var payload = ((JsonElementEventData)decision.Data!).Value;

        payload.GetProperty("GameId").GetString().Should().Be(gameId);
        payload.GetProperty("AiPlayerId").GetString().Should().Be(aiId);
        payload.GetProperty("DecisionType").GetString().Should().NotBeNullOrWhiteSpace();
        payload.TryGetProperty("CorrelationId", out var corr).Should().BeTrue();
        corr.GetString().Should().Be(correlationId);
        payload.TryGetProperty("CausationId", out var causation).Should().BeTrue();
        causation.GetString().Should().Be("cmd-advance");
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
