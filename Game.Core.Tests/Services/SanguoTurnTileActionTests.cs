using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class SanguoTurnTileActionTests
{
    [Fact]
    public async Task GivenUnownedCity_WhenExecuteHumanTileActionBuyLand_ThenPublishesCityBoughtAndStateChanged()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;

        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromDecimal(50m), baseToll: Money.FromDecimal(20m), positionIndex: 0);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { ["c1"] = city };

        var p1 = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: cities);
        var mgr = new SanguoTurnManager(bus, economy, boardState, new SanguoTreasury(), totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var beforeCount = bus.Published.Count;

        await mgr.ExecuteHumanTileActionAsync(action: "buy_land", correlationId: "corr-action", causationId: "ui.sanguo.tile.action.selected");

        var published = bus.Published.Skip(beforeCount).ToList();
        published.Should().Contain(e => e.Type == SanguoCityBought.EventType);
        published.Should().Contain(e => e.Type == SanguoPlayerStateChanged.EventType);
    }

    [Fact]
    public async Task GivenUnownedCity_WhenExecuteHumanTileActionHouseBuild_ThenPublishesCityBoughtAndStateChanged()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;

        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromDecimal(50m), baseToll: Money.FromDecimal(20m), positionIndex: 0);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { ["c1"] = city };

        var p1 = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: cities);
        var mgr = new SanguoTurnManager(bus, economy, boardState, new SanguoTreasury(), totalPositionsHint: 10);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var beforeMoney = p1.Money.ToDecimal();
        var beforeCount = bus.Published.Count;

        await mgr.ExecuteHumanTileActionAsync(action: "house_build", correlationId: "corr-action", causationId: "ui.sanguo.tile.action.selected");

        var published = bus.Published.Skip(beforeCount).ToList();
        published.Should().Contain(e => e.Type == SanguoCityBought.EventType);
        published.Should().Contain(e => e.Type == SanguoPlayerStateChanged.EventType);

        var cityBought = published.Last(e => e.Type == SanguoCityBought.EventType);
        var payload = ((JsonElementEventData)cityBought.Data!).Value;
        payload.GetProperty("BuyerId").GetString().Should().Be("p1");
        payload.GetProperty("CityId").GetString().Should().Be("c1");
        payload.GetProperty("CorrelationId").GetString().Should().Be("corr-action");
        payload.GetProperty("CausationId").GetString().Should().Be("ui.sanguo.tile.action.selected");

        p1.Money.ToDecimal().Should().BeLessThan(beforeMoney);
        p1.OwnsCityId("c1").Should().BeTrue();
    }

    [Fact]
    public async Task GivenUnownedCity_WhenExecuteHumanTileActionSkip_ThenNoPurchaseEventPublished()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromDecimal(50m), baseToll: Money.FromDecimal(20m), positionIndex: 0);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { ["c1"] = city };
        var p1 = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var mgr = new SanguoTurnManager(bus, economy, new SanguoBoardState(new[] { p1 }, cities), new SanguoTreasury(), totalPositionsHint: 10);

        await mgr.StartNewGameAsync("g1", new[] { "p1" }, 1, 1, 1, "corr-start", null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanTileActionAsync(action: "skip", correlationId: "corr-action", causationId: "ui.sanguo.tile.action.selected");
        bus.Published.Skip(before).Should().NotContain(e => e.Type == SanguoCityBought.EventType);
        p1.OwnsCityId("c1").Should().BeFalse();
    }

    [Fact]
    public async Task GivenUnownedCity_WhenExecuteHumanTileActionIsUnsupported_ThenNoOp()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromDecimal(50m), baseToll: Money.FromDecimal(20m), positionIndex: 0);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { ["c1"] = city };
        var p1 = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var mgr = new SanguoTurnManager(bus, economy, new SanguoBoardState(new[] { p1 }, cities), new SanguoTreasury(), totalPositionsHint: 10);

        await mgr.StartNewGameAsync("g1", new[] { "p1" }, 1, 1, 1, "corr-start", null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanTileActionAsync(action: "enter_battle", correlationId: "corr-action", causationId: "ui.sanguo.tile.action.selected");
        bus.Published.Skip(before).Should().BeEmpty();
        p1.OwnsCityId("c1").Should().BeFalse();
    }

    [Fact]
    public async Task GivenPlayerNotOnCity_WhenExecuteHumanTileActionHouseBuild_ThenNoOp()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromDecimal(50m), baseToll: Money.FromDecimal(20m), positionIndex: 0);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { ["c1"] = city };

        var p1 = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 1, economyRules: rules);
        var mgr = new SanguoTurnManager(bus, economy, new SanguoBoardState(new[] { p1 }, cities), new SanguoTreasury(), totalPositionsHint: 10);

        await mgr.StartNewGameAsync("g1", new[] { "p1" }, 1, 1, 1, "corr-start", null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanTileActionAsync(action: "house_build", correlationId: "corr-action", causationId: "ui.sanguo.tile.action.selected");
        bus.Published.Skip(before).Should().BeEmpty();
        p1.OwnsCityId("c1").Should().BeFalse();
    }

    [Fact]
    public async Task GivenInsufficientFunds_WhenExecuteHumanTileActionHouseBuild_ThenNoPurchaseEventPublished()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromDecimal(500m), baseToll: Money.FromDecimal(20m), positionIndex: 0);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { ["c1"] = city };

        var p1 = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: rules);
        var mgr = new SanguoTurnManager(bus, economy, new SanguoBoardState(new[] { p1 }, cities), new SanguoTreasury(), totalPositionsHint: 10);

        await mgr.StartNewGameAsync("g1", new[] { "p1" }, 1, 1, 1, "corr-start", null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanTileActionAsync(action: "house_build", correlationId: "corr-action", causationId: "ui.sanguo.tile.action.selected");
        bus.Published.Skip(before).Should().NotContain(e => e.Type == SanguoCityBought.EventType);
        p1.OwnsCityId("c1").Should().BeFalse();
    }

    [Fact]
    public async Task GivenCityAlreadyOwned_WhenExecuteHumanTileActionHouseBuild_ThenNoPurchaseEventPublished()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromDecimal(50m), baseToll: Money.FromDecimal(20m), positionIndex: 0);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { ["c1"] = city };

        var p1 = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        p1.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var mgr = new SanguoTurnManager(bus, economy, new SanguoBoardState(new[] { p1 }, cities), new SanguoTreasury(), totalPositionsHint: 10);
        await mgr.StartNewGameAsync("g1", new[] { "p1" }, 1, 1, 1, "corr-start", null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanTileActionAsync(action: "house_build", correlationId: "corr-action", causationId: "ui.sanguo.tile.action.selected");
        bus.Published.Skip(before).Should().NotContain(e => e.Type == SanguoCityBought.EventType);
    }

    [Fact]
    public async Task GivenActivePlayerIsAi_WhenExecuteHumanTileActionHouseBuild_ThenNoOp()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromDecimal(50m), baseToll: Money.FromDecimal(20m), positionIndex: 0);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { ["c1"] = city };
        var ai = new SanguoPlayer(playerId: "ai-1", money: 300m, positionIndex: 0, economyRules: rules);
        var mgr = new SanguoTurnManager(bus, economy, new SanguoBoardState(new[] { ai }, cities), new SanguoTreasury(), totalPositionsHint: 10);

        await mgr.StartNewGameAsync("g1", new[] { "ai-1" }, 1, 1, 1, "corr-start", null);

        var before = bus.Published.Count;
        await mgr.ExecuteHumanTileActionAsync(action: "house_build", correlationId: "corr-action", causationId: "ui.sanguo.tile.action.selected");
        bus.Published.Skip(before).Should().BeEmpty();
    }

    [Fact]
    public async Task ShouldThrow_WhenExecuteHumanTileActionWithoutStartingGame()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var mgr = new SanguoTurnManager(bus, economy, new SanguoBoardState(new[] { p1 }, new Dictionary<string, City>(StringComparer.Ordinal)), new SanguoTreasury());

        Func<Task> act = async () => await mgr.ExecuteHumanTileActionAsync(action: "house_build", correlationId: "corr", causationId: null);
        await act.Should().ThrowAsync<InvalidOperationException>();
    }

    [Fact]
    public async Task ShouldThrow_WhenCorrelationIdIsBlank()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromDecimal(50m), baseToll: Money.FromDecimal(20m), positionIndex: 0);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { ["c1"] = city };
        var mgr = new SanguoTurnManager(bus, economy, new SanguoBoardState(new[] { p1 }, cities), new SanguoTreasury(), totalPositionsHint: 10);

        await mgr.StartNewGameAsync("g1", new[] { "p1" }, 1, 1, 1, "corr-start", null);

        Func<Task> act = async () => await mgr.ExecuteHumanTileActionAsync(action: "house_build", correlationId: "  ", causationId: null);
        await act.Should().ThrowAsync<ArgumentException>();
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
            public void Dispose() { }
        }
    }
}
