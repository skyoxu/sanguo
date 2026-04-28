using System;
using System.Collections.Generic;
using System.Linq;
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

public sealed class Task108V3Tests
{
    // ACC:T108.2
    [Theory]
    [InlineData("g-t108-campaign", true)]
    [InlineData("g-t108-classic", false)]
    public async Task ShouldGuardAiDecisionEntrypointByRunMode_WhenAdvancingIntoAiTurn(string gameId, bool campaignModeExpected)
    {
        var scenario = CreateScenario();

        await scenario.Manager.StartNewGameAsync(
            gameId: gameId,
            playerOrder: new[] { "p1", "ai-1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var publishedBefore = scenario.Bus.Published.Count;
        var aiPositionBefore = scenario.AiPlayer.PositionIndex;

        await scenario.Manager.AdvanceTurnAsync(correlationId: "corr-advance", causationId: "cmd-advance");

        var published = scenario.Bus.Published.Skip(publishedBefore).ToList();
        var aiDecisionEvents = published.Where(e => e.Type == SanguoAiDecisionMade.EventType).ToList();
        var blockedDiagnostics = published.Where(e => e.Type == EventTypes.RunContinueBlocked).ToList();

        if (campaignModeExpected)
        {
            aiDecisionEvents.Should().BeEmpty("campaign mode must hard-disable AI decision entrypoint");
            published.Should().NotContain(e =>
                e.Type == SanguoDiceRolled.EventType ||
                e.Type == SanguoTokenMoved.EventType ||
                e.Type == SanguoCityBought.EventType ||
                e.Type == SanguoCityTollPaid.EventType,
                "campaign mode must not execute AI action path");
            blockedDiagnostics.Should().NotBeEmpty("campaign guard should emit an explicit blocked diagnostic event");
            scenario.AiPlayer.PositionIndex.Should().Be(aiPositionBefore, "campaign guard should keep AI player state unchanged");
            return;
        }

        aiDecisionEvents.Should().NotBeEmpty("non-campaign mode should keep AI decision path available");
        blockedDiagnostics.Should().BeEmpty("blocked diagnostic is expected only when campaign guard blocks AI");
        scenario.AiPlayer.PositionIndex.Should().NotBe(aiPositionBefore, "non-campaign mode should continue AI movement path");
    }

    // ACC:T108.3
    [Fact]
    public async Task ShouldEmitNoAiActionEvents_WhenCampaignRoundsAdvanceWithHardDisable()
    {
        var scenario = CreateScenario();

        await scenario.Manager.StartNewGameAsync(
            gameId: "g-t108-campaign-rounds",
            playerOrder: new[] { "p1", "ai-1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var publishedBefore = scenario.Bus.Published.Count;

        await scenario.Manager.AdvanceTurnAsync(correlationId: "corr-advance-1", causationId: "cmd-advance-1");
        await scenario.Manager.AdvanceTurnAsync(correlationId: "corr-advance-2", causationId: "cmd-advance-2");

        var published = scenario.Bus.Published.Skip(publishedBefore).ToList();
        var aiActionTypes = new[]
        {
            SanguoAiDecisionMade.EventType,
            SanguoDiceRolled.EventType,
            SanguoTokenMoved.EventType,
            SanguoCityBought.EventType,
            SanguoCityTollPaid.EventType,
        };

        published
            .Where(e => aiActionTypes.Contains(e.Type, StringComparer.Ordinal))
            .Should()
            .BeEmpty("campaign rounds must emit no AI action events when AI is hard-disabled");
    }

    private static Scenario CreateScenario()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var humanPlayer = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0, economyRules: rules);
        var aiPlayer = new SanguoPlayer(playerId: "ai-1", money: 200m, positionIndex: 0, economyRules: rules);

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City(
                id: "c1",
                name: "City1",
                regionId: "r1",
                basePrice: Money.FromMajorUnits(100),
                baseToll: Money.FromMajorUnits(10),
                positionIndex: 3),
        };

        var boardState = new SanguoBoardState(players: new[] { humanPlayer, aiPlayer }, citiesById: citiesById);

        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(3),
            totalPositionsHint: 10);

        return new Scenario(manager, bus, aiPlayer);
    }

    private sealed record Scenario(SanguoTurnManager Manager, RecordingEventBus Bus, SanguoPlayer AiPlayer);

    private sealed class RecordingEventBus : IEventBus
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
        private readonly Queue<int> nextInts;

        public FixedRng(params int[] nextInts)
        {
            this.nextInts = new Queue<int>(nextInts ?? Array.Empty<int>());
        }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            if (nextInts.Count == 0)
            {
                return minInclusive;
            }

            var value = nextInts.Dequeue();
            if (value < minInclusive)
            {
                return minInclusive;
            }

            if (value >= maxExclusive)
            {
                return maxExclusive - 1;
            }

            return value;
        }

        public double NextDouble() => 0.0;
    }
}
