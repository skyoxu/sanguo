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
using MoneyValue = Game.Core.Domain.ValueObjects.Money;

namespace Game.Core.Tests.Tasks;

public sealed class Task213StateResourceProgressionBuildUpgradeTests
{
    // ACC:T213.1 ACC:T213.5 ACC:T213.9 ACC:T213.10 ACC:T213.13 ACC:T213.14 ACC:T213.15 ACC:T213.16
    [Fact]
    public async Task ShouldProduceSameResourceAndProgressionOutcome_WhenBuildUpgradeInputsRepeat()
    {
        var first = await RunBuildUpgradeScenarioAsync(startingMoney: 1000m, actionCount: 2);
        var second = await RunBuildUpgradeScenarioAsync(startingMoney: 1000m, actionCount: 2);

        first.Snapshot.Players.Single(p => p.PlayerId == "p1").Money.Should().Be(700m);
        first.Snapshot.BuildingLevelsByCityId!["c1"]["building_market"].Should().Be(2);

        second.Snapshot.Players.Single(p => p.PlayerId == "p1").Money.Should().Be(700m);
        second.Snapshot.BuildingLevelsByCityId!["c1"]["building_market"].Should().Be(2);

        first.BuildingLevels.Should().BeEquivalentTo(second.BuildingLevels, options => options.WithStrictOrdering());
        first.RemainingMoneyByAction.Should().BeEquivalentTo(second.RemainingMoneyByAction, options => options.WithStrictOrdering());
    }

    // ACC:T213.2 ACC:T213.6 ACC:T213.17 ACC:T213.18 ACC:T213.19 ACC:T213.20
    [Fact]
    public async Task ShouldExposeBuildUpgradeResourceCostAndProgression_WhenActionIsValid()
    {
        var scenario = await RunBuildUpgradeScenarioAsync(startingMoney: 1000m, actionCount: 2);

        scenario.BuildingLevels.Should().BeEquivalentTo(new[] { 1, 2 }, options => options.WithStrictOrdering());
        scenario.RemainingMoneyByAction.Should().BeEquivalentTo(new[] { 900m, 700m }, options => options.WithStrictOrdering());

        var firstCost = 1000m - scenario.RemainingMoneyByAction[0];
        var secondCost = scenario.RemainingMoneyByAction[0] - scenario.RemainingMoneyByAction[1];
        firstCost.Should().Be(100m);
        secondCost.Should().Be(200m);

        scenario.Snapshot.BuildingLevelsByCityId!["c1"]["building_market"].Should().Be(2);
    }

    // ACC:T213.3 ACC:T213.4 ACC:T213.7 ACC:T213.8 ACC:T213.11 ACC:T213.12
    [Fact]
    public async Task ShouldLeaveResourcesAndProgressionUnchanged_WhenBuildUpgradeCannotBePaid()
    {
        var harness = CreateHarness(startingMoney: 150m);
        await harness.Manager.StartNewGameAsync("g1", new[] { "p1" }, 1, 1, 1, "corr-start", "ut.start");

        await harness.Manager.ExecuteHumanTileActionAsync("build", "corr-build", "ut.build");
        var afterBuild = harness.Manager.ExportSaveSnapshot();
        var publishedBeforeUpgrade = harness.Bus.Published.Count;

        await harness.Manager.ExecuteHumanTileActionAsync("build", "corr-upgrade", "ut.build");

        var afterRejectedUpgrade = harness.Manager.ExportSaveSnapshot();
        afterRejectedUpgrade.Should().BeEquivalentTo(afterBuild);
        harness.Bus.Published.Skip(publishedBeforeUpgrade).Should().NotContain(e => e.Type == SanguoBuildingBuilt.EventType);
        harness.Bus.Published.Skip(publishedBeforeUpgrade).Should().NotContain(e => e.Type == SanguoPlayerStateChanged.EventType);

        var rejected = harness.Bus.Published.Skip(publishedBeforeUpgrade)
            .Should()
            .ContainSingle(e => e.Type == SanguoBuildingBuildRejected.EventType)
            .Subject;
        var payload = ReadPayload(rejected);
        payload.GetProperty("ReasonCode").GetString().Should().Be(SanguoBuildingBuildRejected.ReasonInsufficientResources);
        payload.GetProperty("PlayerId").GetString().Should().Be("p1");
        payload.GetProperty("CityId").GetString().Should().Be("c1");
        payload.GetProperty("BuildingId").GetString().Should().Be("building_market");
        payload.GetProperty("RequiredMoney").GetDecimal().Should().Be(200m);
        payload.GetProperty("AvailableMoney").GetDecimal().Should().Be(50m);
        payload.GetProperty("CorrelationId").GetString().Should().Be("corr-upgrade");
    }

    private static async Task<BuildUpgradeResult> RunBuildUpgradeScenarioAsync(decimal startingMoney, int actionCount)
    {
        var harness = CreateHarness(startingMoney);
        await harness.Manager.StartNewGameAsync("g1", new[] { "p1" }, 1, 1, 1, "corr-start", "ut.start");
        var publishedBeforeActions = harness.Bus.Published.Count;

        for (var i = 0; i < actionCount; i++)
        {
            await harness.Manager.ExecuteHumanTileActionAsync("build", $"corr-build-{i}", "ut.build");
        }

        var actionEvents = harness.Bus.Published.Skip(publishedBeforeActions).ToArray();
        var builtPayloads = actionEvents
            .Where(evt => evt.Type == SanguoBuildingBuilt.EventType)
            .Select(ReadPayload)
            .ToArray();
        var statePayloads = actionEvents
            .Where(evt => evt.Type == SanguoPlayerStateChanged.EventType)
            .Select(ReadPayload)
            .ToArray();

        return new BuildUpgradeResult(
            Snapshot: harness.Manager.ExportSaveSnapshot(),
            BuildingLevels: builtPayloads.Select(payload => payload.GetProperty("NewLevel").GetInt32()).ToArray(),
            RemainingMoneyByAction: statePayloads.Select(payload => payload.GetProperty("Money").GetDecimal()).ToArray());
    }

    private static Harness CreateHarness(decimal startingMoney)
    {
        var city = new City(
            id: "c1",
            name: "City1",
            regionId: "r1",
            basePrice: MoneyValue.Zero,
            baseToll: MoneyValue.FromDecimal(10m),
            positionIndex: 0);

        var player = new SanguoPlayer("p1", startingMoney, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        player.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var bus = new RecordingEventBus();
        var boardState = new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city });

        var manager = new SanguoTurnManager(
            bus: bus,
            economy: new SanguoEconomyManager(bus),
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(),
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            buildingsCatalog: CreateBuildingsCatalog());

        return new Harness(manager, bus);
    }

    private static SanguoBuildingsCatalog CreateBuildingsCatalog()
    {
        return new SanguoBuildingsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Buildings:
            [
                new SanguoBuildingDefinition(
                    BuildingId: "building_market",
                    NameKey: "building.market.name",
                    DescriptionKey: "building.market.desc",
                    MaxLevel: 2,
                    BuildCostBase: 100,
                    UpgradeCostBase: 200,
                    SettlementIncomeBase: 0,
                    EconomyStepDeltas: new SanguoEconomyStepDeltas(
                        BuyPrice: 0,
                        Toll: 0,
                        IncomeSettlement: 0,
                        BuildCost: 0,
                        UpgradeCost: 0)),
            ]);
    }

    private static JsonElement ReadPayload(DomainEvent evt)
    {
        evt.Data.Should().BeOfType<JsonElementEventData>();
        return ((JsonElementEventData)evt.Data!).Value;
    }

    private sealed record Harness(SanguoTurnManager Manager, RecordingEventBus Bus);

    private sealed record BuildUpgradeResult(
        SanguoSaveSnapshot Snapshot,
        int[] BuildingLevels,
        decimal[] RemainingMoneyByAction);

    private sealed class RecordingEventBus : IEventBus
    {
        public List<DomainEvent> Published { get; } = new();

        public Task PublishAsync(DomainEvent evt)
        {
            Published.Add(evt);
            return Task.CompletedTask;
        }

        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => new NoopDisposable();
    }

    private sealed class NoopDisposable : IDisposable
    {
        public void Dispose()
        {
        }
    }

    private sealed class FixedRng : IRandomNumberGenerator
    {
        public int NextInt(int minInclusive, int maxExclusive) => minInclusive;

        public double NextDouble() => 0.0;
    }
}
