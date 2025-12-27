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

public sealed class Task14MonthEndSettlementTests
{
    [Fact]
    public async Task ShouldUpdateMoneyAndPublishMonthSettled_WhenMonthBoundaryReached()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var gameId = "game-1";
        var playerOrder = new[] { "p1", "p2" };
        var correlationId = "corr-1";

        var rules = new SanguoEconomyRules(
            maxPriceMultiplier: SanguoEconomyRules.DefaultMaxPriceMultiplier,
            maxTollMultiplier: SanguoEconomyRules.DefaultMaxTollMultiplier);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10)),
        };

        var p1 = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0, economyRules: rules);
        var p2 = new SanguoPlayer(playerId: "p2", money: 0m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1, p2 }, citiesById: cities);
        var treasury = new SanguoTreasury();

        boardState.TryBuyCity(buyerId: "p1", cityId: "c1", priceMultiplier: 1.0m).Should().BeTrue();
        var p1MoneyBefore = p1.Money;

        var mgr = new SanguoTurnManager(bus, economy, boardState, treasury);
        await mgr.StartNewGameAsync(
            gameId: gameId,
            playerOrder: playerOrder,
            year: 1,
            month: 1,
            day: 31,
            correlationId: correlationId,
            causationId: null);

        await mgr.AdvanceTurnAsync(correlationId, causationId: "cmd-advance");

        p1.Money.Should().BeGreaterThan(p1MoneyBefore, "month settlement should increase money by monthly income");

        var settled = bus.Published.Find(e => e.Type == SanguoMonthSettled.EventType);
        settled.Should().NotBeNull("crossing a month boundary should trigger month settlement");

        settled!.Data.Should().BeOfType<JsonElementEventData>();
        var payload = ((JsonElementEventData)settled.Data!).Value;

        payload.GetProperty("GameId").GetString().Should().Be(gameId);
        payload.GetProperty("Year").GetInt32().Should().Be(1);
        payload.GetProperty("Month").GetInt32().Should().Be(1);
        payload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);
        payload.GetProperty("CausationId").GetString().Should().Be("cmd-advance");

        payload.GetProperty("PlayerSettlements").ValueKind.Should().Be(JsonValueKind.Array);
        payload.GetProperty("PlayerSettlements").GetArrayLength().Should().Be(playerOrder.Length);
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
