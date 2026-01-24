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
using Game.Core.Ports;
using Game.Core.Services;
using Game.Core.Utilities;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task58BuildingBuildWindowTests
{
    private sealed class CapturingEventBus : IEventBus
    {
        private readonly List<Func<DomainEvent, Task>> _handlers = new();
        public List<DomainEvent> Published { get; } = new();

        public Task PublishAsync(DomainEvent evt)
        {
            Published.Add(evt);
            return Task.WhenAll(_handlers.Select(h => h(evt)));
        }

        public IDisposable Subscribe(Func<DomainEvent, Task> handler)
        {
            _handlers.Add(handler);
            return new Unsubscriber(_handlers, handler);
        }

        private sealed class Unsubscriber : IDisposable
        {
            private readonly List<Func<DomainEvent, Task>> _handlers;
            private readonly Func<DomainEvent, Task> _handler;
            private bool _disposed;

            public Unsubscriber(List<Func<DomainEvent, Task>> handlers, Func<DomainEvent, Task> handler)
            {
                _handlers = handlers;
                _handler = handler;
            }

            public void Dispose()
            {
                if (_disposed)
                {
                    return;
                }

                _disposed = true;
                _handlers.Remove(_handler);
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
            {
                return minInclusive;
            }

            return _ints.Dequeue();
        }

        public double NextDouble()
        {
            if (_doubles.Count == 0)
            {
                return 1.0;
            }

            return _doubles.Dequeue();
        }
    }

    private static SanguoBuildingsCatalog CreateTestBuildingsCatalog(int tollStepDelta)
    {
        return new SanguoBuildingsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Buildings: new[]
            {
                new SanguoBuildingDefinition(
                    BuildingId: "building_market",
                    NameKey: "building.building_market.name",
                    DescriptionKey: "building.building_market.desc",
                    MaxLevel: 3,
                    BuildCostBase: 0,
                    UpgradeCostBase: 0,
                    SettlementIncomeBase: 0,
                    EconomyStepDeltas: new SanguoEconomyStepDeltas(
                        BuyPrice: 0,
                        Toll: tollStepDelta,
                        IncomeSettlement: 0,
                        BuildCost: 0,
                        UpgradeCost: 0))
            });
    }

    private static SanguoBuildingsCatalog CreateCostAndUpgradeCatalog()
    {
        return new SanguoBuildingsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Buildings: new[]
            {
                new SanguoBuildingDefinition(
                    BuildingId: "building_market",
                    NameKey: "building.building_market.name",
                    DescriptionKey: "building.building_market.desc",
                    MaxLevel: 2,
                    BuildCostBase: 100,
                    UpgradeCostBase: 200,
                    SettlementIncomeBase: 0,
                    EconomyStepDeltas: new SanguoEconomyStepDeltas(
                        BuyPrice: 0,
                        Toll: 0,
                        IncomeSettlement: 0,
                        BuildCost: 1,
                        UpgradeCost: 2))
            });
    }

    private static City CreateCityAtIndex(int positionIndex, decimal baseTollMajorUnits)
    {
        return new City(
            id: "c1",
            name: "City1",
            regionId: "r1",
            basePrice: MoneyValue.Zero,
            baseToll: MoneyValue.FromDecimal(baseTollMajorUnits),
            positionIndex: positionIndex);
    }

    // ACC:T58.3
    [Fact]
    public async Task ShouldNotPublishBuildingBuilt_WhenBuildingOnUnownedCity()
    {
        var city = CreateCityAtIndex(positionIndex: 1, baseTollMajorUnits: 10m);
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 1, economyRules: SanguoEconomyRules.Default);
        var ai = new SanguoPlayer(playerId: "ai-1", money: 1000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);

        var boardState = new SanguoBoardState(
            players: new[] { p1, ai },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city });

        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var treasury = new SanguoTreasury();
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new FixedRng(ints: new[] { 1 }),
            totalPositionsHint: 10,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            globalEventIntervalTurns: 5,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global",
            buildingsCatalog: CreateTestBuildingsCatalog(tollStepDelta: 2));

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        await mgr.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-build", causationId: "ui.action");

        bus.Published.Should().NotContain(e => e.Type == SanguoBuildingBuilt.EventType);
    }

    // ACC:T58.2
    // ACC:T58.3
    [Fact]
    public async Task ShouldPublishBuildingBuiltAndIncreaseToll_WhenBuildingOnOwnedCityAndAiPaysToll()
    {
        var city = CreateCityAtIndex(positionIndex: 1, baseTollMajorUnits: 10m);
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 1, economyRules: SanguoEconomyRules.Default);
        var ai = new SanguoPlayer(playerId: "ai-1", money: 1000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        p1.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var boardState = new SanguoBoardState(
            players: new[] { p1, ai },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city });

        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var treasury = new SanguoTreasury();

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new FixedRng(ints: new[] { 1 }),
            totalPositionsHint: 10,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            globalEventIntervalTurns: 5,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global",
            buildingsCatalog: CreateTestBuildingsCatalog(tollStepDelta: 2));

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        await mgr.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-build", causationId: "ui.action");

        bus.Published.Should().Contain(e => e.Type == SanguoBuildingBuilt.EventType);
        var builtEvt = bus.Published.Last(e => e.Type == SanguoBuildingBuilt.EventType);
        builtEvt.Data.Should().BeOfType<JsonElementEventData>();
        var builtPayload = ((JsonElementEventData)builtEvt.Data!).Value;
        builtPayload.GetProperty("BuildingId").GetString().Should().Be("building_market");
        builtPayload.GetProperty("EconomyStepDeltas").GetProperty("Toll").GetInt32().Should().Be(2);

        await mgr.AdvanceTurnAsync(correlationId: "corr-advance", causationId: null);

        var tollEvt = bus.Published.LastOrDefault(e => e.Type == SanguoCityTollPaid.EventType);
        tollEvt.Should().NotBeNull("AI landing on an owned city must pay toll and publish core.sanguo.city.toll.paid");
        tollEvt!.Data.Should().BeOfType<JsonElementEventData>();
        var payload = ((JsonElementEventData)tollEvt.Data!).Value;

        payload.GetProperty("AppliedMultipliers").GetProperty("BuildingStepDelta").GetInt32().Should().Be(2);
        payload.GetProperty("AppliedMultipliers").GetProperty("EffectiveSteps").GetInt32().Should().Be(4);
        payload.GetProperty("Amount").GetDecimal().Should().Be(20m);
    }

    // ACC:T58.3
    [Fact]
    public async Task ShouldChargeBuildAndUpgradeCost_WhenBuildingIsUpgraded()
    {
        var city = CreateCityAtIndex(positionIndex: 0, baseTollMajorUnits: 0m);
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        p1.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var boardState = new SanguoBoardState(
            players: new[] { p1 },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city });

        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var treasury = new SanguoTreasury();

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new FixedRng(ints: new[] { 1 }),
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            globalEventIntervalTurns: 5,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global",
            buildingsCatalog: CreateCostAndUpgradeCatalog());

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        // Build cost: base=100, stepDelta=+1 => effectiveSteps=3 => 1.5x => 150.
        await mgr.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-build-1", causationId: "ui.action");
        p1.Money.ToDecimal().Should().Be(850m);

        // Upgrade cost: base=200, stepDelta=+2 => effectiveSteps=4 => 2.0x => 400.
        await mgr.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-build-2", causationId: "ui.action");
        p1.Money.ToDecimal().Should().Be(450m);

        var builtEvents = bus.Published.Where(e => e.Type == SanguoBuildingBuilt.EventType).ToArray();
        builtEvents.Should().HaveCount(2);

        var second = builtEvents[1];
        second.Data.Should().BeOfType<JsonElementEventData>();
        var payload2 = ((JsonElementEventData)second.Data!).Value;
        payload2.GetProperty("NewLevel").GetInt32().Should().Be(2);
    }

    // ACC:T58.3
    [Fact]
    public async Task ShouldNotBuild_WhenCityOwnedByAnotherPlayer()
    {
        var city = CreateCityAtIndex(positionIndex: 0, baseTollMajorUnits: 0m);
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var p2 = new SanguoPlayer(playerId: "p2", money: 1000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        p2.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var boardState = new SanguoBoardState(
            players: new[] { p1, p2 },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city });

        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(ints: new[] { 1 }),
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            globalEventIntervalTurns: 5,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global",
            buildingsCatalog: CreateTestBuildingsCatalog(tollStepDelta: 2));

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "p2" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        await mgr.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-build", causationId: "ui.action");

        bus.Published.Should().NotContain(e => e.Type == SanguoBuildingBuilt.EventType);
    }

    // ACC:T58.3
    [Fact]
    public async Task ShouldNotBuild_WhenInsufficientMoney()
    {
        var city = CreateCityAtIndex(positionIndex: 0, baseTollMajorUnits: 0m);
        var p1 = new SanguoPlayer(playerId: "p1", money: 10m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        p1.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var boardState = new SanguoBoardState(
            players: new[] { p1 },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city });

        var expensiveCatalog = new SanguoBuildingsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Buildings: new[]
            {
                new SanguoBuildingDefinition(
                    BuildingId: "building_market",
                    NameKey: "building.building_market.name",
                    DescriptionKey: "building.building_market.desc",
                    MaxLevel: 1,
                    BuildCostBase: 9999,
                    UpgradeCostBase: 0,
                    SettlementIncomeBase: 0,
                    EconomyStepDeltas: new SanguoEconomyStepDeltas(
                        BuyPrice: 0,
                        Toll: 0,
                        IncomeSettlement: 0,
                        BuildCost: 0,
                        UpgradeCost: 0))
            });

        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(ints: new[] { 1 }),
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            globalEventIntervalTurns: 5,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global",
            buildingsCatalog: expensiveCatalog);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        await mgr.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-build", causationId: "ui.action");

        bus.Published.Should().NotContain(e => e.Type == SanguoBuildingBuilt.EventType);
    }

    // ACC:T58.3
    [Fact]
    public async Task ShouldStopBuilding_WhenAllBuildingsAtMaxLevel()
    {
        var city = CreateCityAtIndex(positionIndex: 0, baseTollMajorUnits: 0m);
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        p1.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var boardState = new SanguoBoardState(
            players: new[] { p1 },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city });

        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(ints: new[] { 1 }),
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            globalEventIntervalTurns: 5,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global",
            buildingsCatalog: CreateCostAndUpgradeCatalog());

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        await mgr.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-build-1", causationId: "ui.action");
        await mgr.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-build-2", causationId: "ui.action");

        var before = bus.Published.Count(e => e.Type == SanguoBuildingBuilt.EventType);
        await mgr.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-build-3", causationId: "ui.action");
        var after = bus.Published.Count(e => e.Type == SanguoBuildingBuilt.EventType);

        after.Should().Be(before);
    }

    // ACC:T58.3
    [Fact]
    public async Task ShouldNotBuild_WhenBuildingsCatalogMissing()
    {
        var city = CreateCityAtIndex(positionIndex: 0, baseTollMajorUnits: 0m);
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        p1.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var boardState = new SanguoBoardState(
            players: new[] { p1 },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city });

        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(ints: new[] { 1 }),
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            globalEventIntervalTurns: 5,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global",
            buildingsCatalog: null);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        await mgr.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-build", causationId: "ui.action");

        bus.Published.Should().NotContain(e => e.Type == SanguoBuildingBuilt.EventType);
    }
}

