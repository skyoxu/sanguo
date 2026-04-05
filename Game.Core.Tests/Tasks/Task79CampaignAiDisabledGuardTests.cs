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
using Game.Core.Services.Sanguo;
using Game.Core.Utilities;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task79CampaignAiDisabledGuardTests
{
    // ACC:T79.1
    [Fact]
    public async Task ShouldRefuseAiDecisionPathAndKeepGameStateUnchanged_WhenInvokedInCampaignMode()
    {
        var runmodeIsolation = CampaignRunmodeIsolationPolicy.Evaluate(runmode: "campaign", requestIsolation: true);
        runmodeIsolation.CampaignIsolationApplied.Should().BeTrue();

        var scenario = CreateScenario();
        await scenario.Manager.StartNewGameAsync(
            gameId: "g-t79-campaign",
            playerOrder: new[] { "p1", "ai-1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var aiPositionBefore = scenario.AiPlayer.PositionIndex;
        var aiMoneyBefore = scenario.AiPlayer.Money.ToDecimal();
        var aiOwnedCityIdsBefore = scenario.AiPlayer.OwnedCityIds.ToArray();
        var publishedBefore = scenario.Bus.Published.Count;

        await scenario.Manager.AdvanceTurnAsync(correlationId: "corr-advance", causationId: "cmd-advance");

        var published = scenario.Bus.Published.Skip(publishedBefore).ToList();
        published.Should().NotContain(e => e.Type == SanguoAiDecisionMade.EventType, "campaign mode should refuse AI decision entry");
        published.Should().NotContain(e => e.Type == SanguoDiceRolled.EventType, "campaign mode should block AI dice execution path");
        published.Should().NotContain(e => e.Type == SanguoTokenMoved.EventType, "campaign mode should block AI movement path");
        published.Should().NotContain(e => e.Type == SanguoCityBought.EventType, "campaign mode should block AI city purchase path");
        published.Should().NotContain(e => e.Type == SanguoCityTollPaid.EventType, "campaign mode should block AI toll path");

        scenario.AiPlayer.PositionIndex.Should().Be(aiPositionBefore);
        scenario.AiPlayer.Money.ToDecimal().Should().Be(aiMoneyBefore);
        scenario.AiPlayer.OwnedCityIds.Should().BeEquivalentTo(aiOwnedCityIdsBefore);
    }

    // ACC:T79.1
    [Fact]
    public async Task ShouldKeepAiDecisionBehaviorAvailable_WhenInvokedInNonCampaignMode()
    {
        var runmodeIsolation = CampaignRunmodeIsolationPolicy.Evaluate(runmode: "classic", requestIsolation: true);
        runmodeIsolation.CampaignIsolationApplied.Should().BeFalse();

        var scenario = CreateScenario();
        await scenario.Manager.StartNewGameAsync(
            gameId: "g-t79-classic",
            playerOrder: new[] { "p1", "ai-1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var aiPositionBefore = scenario.AiPlayer.PositionIndex;
        var publishedBefore = scenario.Bus.Published.Count;

        await scenario.Manager.AdvanceTurnAsync(correlationId: "corr-advance", causationId: "cmd-advance");

        var published = scenario.Bus.Published.Skip(publishedBefore).ToList();
        published.Should().Contain(e => e.Type == SanguoAiDecisionMade.EventType);
        published.Should().Contain(e => e.Type == SanguoDiceRolled.EventType);
        published.Should().Contain(e => e.Type == SanguoTokenMoved.EventType);

        scenario.AiPlayer.PositionIndex.Should().NotBe(aiPositionBefore);
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
