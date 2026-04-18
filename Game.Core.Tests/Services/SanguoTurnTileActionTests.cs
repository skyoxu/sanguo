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
    public async Task ShouldPublishCityBoughtAndStateChanged_WhenExecuteHumanTileActionBuyLandOnUnownedCity()
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
    public async Task ShouldPublishCityBoughtAndStateChanged_WhenExecuteHumanTileActionHouseBuildOnUnownedCity()
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
    public async Task ShouldNotPublishPurchaseEvent_WhenExecuteHumanTileActionSkipOnUnownedCity()
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
    public async Task ShouldNoOp_WhenExecuteUnsupportedHumanTileActionOnUnownedCity()
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
    public async Task ShouldNoOp_WhenExecuteHumanTileActionHouseBuildAndPlayerNotOnCity()
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
    public async Task ShouldNotPublishPurchaseEvent_WhenExecuteHumanTileActionHouseBuildAndFundsInsufficient()
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
    public async Task ShouldNotPublishPurchaseEvent_WhenExecuteHumanTileActionHouseBuildAndCityAlreadyOwned()
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
    public async Task ShouldNoOp_WhenExecuteHumanTileActionHouseBuildAndActivePlayerIsAi()
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

    // ACC:T98.1
    [Fact]
    public async Task ShouldRejectSecondActionCardAttemptAndKeepTurnState_WhenSecondActionIsAttemptedInSameRound()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(
            players: new[] { p1 },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var cards = new SanguoActionCardsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Cards: Array.AsReadOnly(new[]
            {
                new SanguoActionCardCatalogEntry(
                    CardId: "ac_step_down",
                    NameKey: "card.ac_step_down.name",
                    DescriptionKey: "card.ac_step_down.desc",
                    EffectKind: "economyStepDelta",
                    StepDelta: -1,
                    DurationRounds: 3),
                new SanguoActionCardCatalogEntry(
                    CardId: "ac_step_up",
                    NameKey: "card.ac_step_up.name",
                    DescriptionKey: "card.ac_step_up.desc",
                    EffectKind: "economyStepDelta",
                    StepDelta: 2,
                    DurationRounds: 3),
            }));

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            totalPositionsHint: 10,
            actionCardsCatalog: cards);

        await mgr.StartNewGameAsync("g1", new[] { "p1" }, 1, 1, 1, "corr-start", null);

        var first = await mgr.TryPlayHumanActionCardAsync("ac_step_down", "corr-first", "ut.first");
        first.Should().BeTrue();
        var stateAfterFirst = mgr.GetTurnAppliedMultipliersSnapshot("p1");
        var beforeSecond = bus.Published.Count;

        var second = await mgr.TryPlayHumanActionCardAsync("ac_step_up", "corr-second", "ut.second");
        second.Should().BeFalse();

        var secondEvents = bus.Published.Skip(beforeSecond).ToList();
        secondEvents.Should().ContainSingle(e => e.Type == SanguoActionCardPlayRejected.EventType);
        secondEvents.Should().ContainSingle(e => e.Type == "core.sanguo.action.explain");
        secondEvents.Should().NotContain(e => e.Type == SanguoActionCardPlayed.EventType);

        var stateAfterSecond = mgr.GetTurnAppliedMultipliersSnapshot("p1");
        stateAfterSecond.ActionCardStepDelta.Should().Be(stateAfterFirst.ActionCardStepDelta);
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
