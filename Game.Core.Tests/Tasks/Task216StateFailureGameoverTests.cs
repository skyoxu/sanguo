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

namespace Game.Core.Tests.Tasks;

public sealed class Task216StateFailureGameoverTests
{
    // ACC:T216.1 ACC:T216.2 ACC:T216.3 ACC:T216.4 ACC:T216.5 ACC:T216.10 ACC:T216.11 ACC:T216.12 ACC:T216.13 ACC:T216.14 ACC:T216.15 ACC:T216.16 ACC:T216.17 ACC:T216.18 ACC:T216.19 ACC:T216.20 ACC:T216.21
    [Fact]
    public async Task ShouldEnterGameOverAndRejectFurtherAdvancement_WhenHumanBankruptcyOccursDuringTollSettlement()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var tollCity = new City(
            id: "c-toll",
            name: "TollCity",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(100),
            baseToll: Money.FromMajorUnits(20),
            positionIndex: 3);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            [tollCity.Id] = tollCity,
        };

        var rules = SanguoEconomyRules.Default;
        var human = new SanguoPlayer(playerId: "p1", money: 5m, positionIndex: 0, economyRules: rules);
        var payee = new SanguoPlayer(playerId: "ai-1", money: 200m, positionIndex: 3, economyRules: rules);
        payee.TryBuyCity(tollCity, priceMultiplier: 1.0m).Should().BeTrue();
        var payeeMoneyBeforeSettlement = payee.Money.ToDecimal();

        var treasury = new SanguoTreasury();
        var boardState = new SanguoBoardState(players: new[] { human, payee }, citiesById: cities);
        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new FixedRng(fixedNextInt: 3),
            totalPositionsHint: 10);

        await manager.StartNewGameAsync(
            gameId: "g-t216-human",
            playerOrder: new[] { "p1", "ai-1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var beforeSettlement = bus.Published.Count;
        await manager.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-human", causationId: "ui.hud.dice.roll");
        var settlementEvents = bus.Published.Skip(beforeSettlement).ToList();

        human.IsEliminated.Should().BeTrue();
        human.Money.Should().Be(Money.Zero);
        payee.Money.ToDecimal().Should().Be(payeeMoneyBeforeSettlement + 5m);
        settlementEvents.Should().Contain(evt => evt.Type == SanguoCityTollPaid.EventType);
        settlementEvents.Last().Type.Should().Be(SanguoGameEnded.EventType);

        var ended = settlementEvents.Single(evt => evt.Type == SanguoGameEnded.EventType);
        var endedPayload = ((JsonElementEventData)ended.Data!).Value;
        endedPayload.GetProperty("EndReason").GetString().Should().Be(SanguoGameEnded.ReasonPlayerBankrupt);

        var eventCountAfterGameOver = bus.Published.Count;
        Func<Task> act = () => manager.AdvanceTurnAsync(correlationId: "corr-after-gameover", causationId: "cmd.after.gameover");

        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("*GameOver*");
        bus.Published.Count.Should().Be(eventCountAfterGameOver);
    }

    // ACC:T216.6 ACC:T216.7 ACC:T216.8 ACC:T216.9
    [Fact]
    public async Task ShouldPruneNpcAndReleaseOwnedCities_WhenNpcBankruptcyOccursDuringTurnSettlement()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var tollCity = new City(
            id: "c-toll",
            name: "TollCity",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(100),
            baseToll: Money.FromMajorUnits(10),
            positionIndex: 2);
        var ownedCity = new City(
            id: "c-owned",
            name: "OwnedCity",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(1),
            baseToll: Money.FromMajorUnits(1),
            positionIndex: 0);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            [tollCity.Id] = tollCity,
            [ownedCity.Id] = ownedCity,
        };

        var rules = SanguoEconomyRules.Default;
        var human = new SanguoPlayer(playerId: "p1", money: 500m, positionIndex: 0, economyRules: rules);
        var npc = new SanguoPlayer(playerId: "ai-1", money: 5m, positionIndex: 0, economyRules: rules);
        var secondHuman = new SanguoPlayer(playerId: "p2", money: 500m, positionIndex: 0, economyRules: rules);
        human.TryBuyCity(tollCity, priceMultiplier: 1.0m).Should().BeTrue();
        npc.TryBuyCity(ownedCity, priceMultiplier: 1.0m).Should().BeTrue();
        var humanMoneyBeforeSettlement = human.Money.ToDecimal();
        var npcMoneyBeforeSettlement = npc.Money.ToDecimal();

        var treasury = new SanguoTreasury();
        var boardState = new SanguoBoardState(players: new[] { human, npc, secondHuman }, citiesById: cities);
        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new FixedRng(fixedNextInt: 2),
            totalPositionsHint: 10);

        await manager.StartNewGameAsync(
            gameId: "g-t216-npc",
            playerOrder: new[] { "p1", "ai-1", "p2" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        await manager.AdvanceTurnAsync(correlationId: "corr-to-npc", causationId: "cmd.to.npc");

        npc.IsEliminated.Should().BeTrue();
        npc.Money.Should().Be(Money.Zero);
        human.Money.ToDecimal().Should().Be(humanMoneyBeforeSettlement + npcMoneyBeforeSettlement);
        npc.OwnedCityIds.Should().BeEmpty();
        boardState.TryGetOwnerOfCity(ownedCity.Id, out var owner).Should().BeFalse();
        owner.Should().BeNull();

        var observedActivePlayerIds = new List<string>();
        for (var turn = 0; turn < 4; turn++)
        {
            var beforeAdvance = bus.Published.Count;
            await manager.AdvanceTurnAsync(correlationId: $"corr-after-npc-{turn}", causationId: $"cmd.after.npc.{turn}");
            observedActivePlayerIds.AddRange(bus.Published.Skip(beforeAdvance).SelectMany(ReadActivePlayerIds));
        }

        observedActivePlayerIds.Should().NotContain("ai-1");
        observedActivePlayerIds.Should().Contain(new[] { "p1", "p2" });
        bus.Published.Should().NotContain(evt => evt.Type == SanguoGameEnded.EventType);
    }

    private static IEnumerable<string> ReadActivePlayerIds(DomainEvent evt)
    {
        if (evt.Data is not JsonElementEventData data)
            yield break;

        if (!data.Value.TryGetProperty("ActivePlayerId", out var activePlayerId))
            yield break;

        if (activePlayerId.ValueKind != JsonValueKind.String)
            yield break;

        var value = activePlayerId.GetString();
        if (!string.IsNullOrWhiteSpace(value))
            yield return value;
    }

    private sealed class FixedRng : IRandomNumberGenerator
    {
        private readonly int _fixedNextInt;

        public FixedRng(int fixedNextInt)
        {
            _fixedNextInt = fixedNextInt;
        }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            if (_fixedNextInt < minInclusive)
                return minInclusive;
            if (_fixedNextInt >= maxExclusive)
                return maxExclusive - 1;
            return _fixedNextInt;
        }

        public double NextDouble() => 0.0;
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
            public void Dispose()
            {
            }
        }
    }
}
