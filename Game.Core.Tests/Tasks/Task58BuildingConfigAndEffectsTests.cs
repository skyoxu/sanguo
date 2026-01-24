using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Ports;
using Game.Core.Services;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task58BuildingConfigAndEffectsTests
{
    private sealed class FakeResourceLoader : IResourceLoader
    {
        private readonly string _path;
        private readonly string? _content;
        public readonly List<string> LoadTextCalls = new();

        public FakeResourceLoader(string path, string? content)
        {
            _path = path;
            _content = content;
        }

        public string? LoadText(string path)
        {
            LoadTextCalls.Add(path);
            return string.Equals(path, _path, StringComparison.Ordinal) ? _content : null;
        }

        public byte[]? LoadBytes(string path) => null;
    }

    // ACC:T58.1
    [Fact]
    public void ShouldRejectUnknownRootField_WhenLoadingBuildingsCatalog()
    {
        var json = "{\"schemaVersion\":1,\"version\":1,\"buildings\":[],\"extra\":123}";
        var loader = new FakeResourceLoader(SanguoBuildingsCatalogLoader.BuildingsResPath, json);

        var ok = SanguoBuildingsCatalogLoader.TryLoadBuildingsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Contain("invalid_buildings_catalog");
        loader.LoadTextCalls.Should().ContainSingle().Which.Should().Be(SanguoBuildingsCatalogLoader.BuildingsResPath);
    }

    // ACC:T58.2
    [Fact]
    public void ShouldRejectUnknownEconomyStepDeltaField_WhenLoadingBuildingsCatalog()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "buildings": [
            {
              "buildingId": "building_market",
              "nameKey": "building.name",
              "descriptionKey": "building.desc",
              "maxLevel": 3,
              "buildCostBase": 100,
              "upgradeCostBase": 50,
              "settlementIncomeBase": 10,
              "economyStepDeltas": { "toll": 1, "unknown": 1 }
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(SanguoBuildingsCatalogLoader.BuildingsResPath, json);
        var ok = SanguoBuildingsCatalogLoader.TryLoadBuildingsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Contain("invalid_buildings_catalog");
    }

    // ACC:T58.4
    [Fact]
    public void ShouldApplyBuildingIncomeSettlementSteps_WhenSettlingMonthWithProvider()
    {
        var city = new City(
            id: "c1",
            name: "City1",
            regionId: "r1",
            basePrice: Money.Zero,
            baseToll: Money.FromMajorUnits(10),
            positionIndex: 0);

        var player = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        player.TryBuyCity(city, priceMultiplier: 1m).Should().BeTrue();

        var boardState = new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city });

        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        var treasury = new SanguoTreasury();

        // BuildingStepDelta=+2 => EffectiveSteps=4 => 2.0x; base toll 10 => income 20.
        var settlements = economy.SettleMonth(
            boardState: boardState,
            playerOrder: new[] { player.PlayerId },
            treasury: treasury,
            buildingIncomeSettlementStepDeltaProvider: _ => 2);

        settlements.Should().ContainSingle();
        settlements[0].AmountDelta.Should().Be(20m);
        player.Money.ToDecimal().Should().Be(20m);
    }

    // ACC:T58.1
    [Fact]
    public void ShouldLoadBuildingsCatalog_WhenJsonIsValidAndFieldsWhitelisted()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 2,
          "buildings": [
            {
              "buildingId": "b2",
              "nameKey": "b2.name",
              "descriptionKey": "b2.desc",
              "maxLevel": 2,
              "buildCostBase": 100,
              "upgradeCostBase": 50,
              "settlementIncomeBase": 10,
              "economyStepDeltas": { "buyPrice": 0, "toll": 1, "incomeSettlement": 2, "buildCost": 0, "upgradeCost": 0 }
            },
            {
              "buildingId": "b1",
              "nameKey": "b1.name",
              "descriptionKey": "b1.desc",
              "maxLevel": 1,
              "buildCostBase": 0,
              "upgradeCostBase": 0,
              "settlementIncomeBase": 0,
              "economyStepDeltas": { "buyPrice": 0, "toll": 0, "incomeSettlement": 0, "buildCost": 0, "upgradeCost": 0 }
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(SanguoBuildingsCatalogLoader.BuildingsResPath, json);
        var ok = SanguoBuildingsCatalogLoader.TryLoadBuildingsCatalog(loader, out var catalog, out var error);

        ok.Should().BeTrue(error);
        catalog.SchemaVersion.Should().Be(1);
        catalog.Version.Should().Be(2);
        catalog.Buildings.Should().HaveCount(2);
        catalog.Buildings[0].BuildingId.Should().Be("b1");
        catalog.Buildings[1].BuildingId.Should().Be("b2");
        catalog.Buildings[1].EconomyStepDeltas.IncomeSettlement.Should().Be(2);
    }

    // ACC:T58.1
    [Fact]
    public void ShouldRejectDuplicateBuildingId_WhenLoadingBuildingsCatalog()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "buildings": [
            {
              "buildingId": "b1",
              "nameKey": "b1.name",
              "descriptionKey": "b1.desc",
              "maxLevel": 1,
              "buildCostBase": 0,
              "upgradeCostBase": 0,
              "settlementIncomeBase": 0,
              "economyStepDeltas": { "buyPrice": 0, "toll": 0, "incomeSettlement": 0, "buildCost": 0, "upgradeCost": 0 }
            },
            {
              "buildingId": "b1",
              "nameKey": "b1.name2",
              "descriptionKey": "b1.desc2",
              "maxLevel": 1,
              "buildCostBase": 0,
              "upgradeCostBase": 0,
              "settlementIncomeBase": 0,
              "economyStepDeltas": { "buyPrice": 0, "toll": 0, "incomeSettlement": 0, "buildCost": 0, "upgradeCost": 0 }
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(SanguoBuildingsCatalogLoader.BuildingsResPath, json);
        var ok = SanguoBuildingsCatalogLoader.TryLoadBuildingsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Contain("duplicate_building_id");
    }

    // ACC:T58.1
    [Fact]
    public void ShouldRejectEmptyBuildingsArray_WhenLoadingBuildingsCatalog()
    {
        var json = "{\"schemaVersion\":1,\"version\":1,\"buildings\":[]}";
        var loader = new FakeResourceLoader(SanguoBuildingsCatalogLoader.BuildingsResPath, json);

        var ok = SanguoBuildingsCatalogLoader.TryLoadBuildingsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Contain("no_buildings");
    }

    // ACC:T58.1
    [Fact]
    public void ShouldRejectOutOfRangeStepDelta_WhenLoadingBuildingsCatalog()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "buildings": [
            {
              "buildingId": "b1",
              "nameKey": "b1.name",
              "descriptionKey": "b1.desc",
              "maxLevel": 1,
              "buildCostBase": 0,
              "upgradeCostBase": 0,
              "settlementIncomeBase": 0,
              "economyStepDeltas": { "buyPrice": 0, "toll": 999, "incomeSettlement": 0, "buildCost": 0, "upgradeCost": 0 }
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(SanguoBuildingsCatalogLoader.BuildingsResPath, json);
        var ok = SanguoBuildingsCatalogLoader.TryLoadBuildingsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Contain("bad_step_deltas");
    }

    // ACC:T58.1
    [Fact]
    public void ShouldRejectNonObjectRoot_WhenLoadingBuildingsCatalog()
    {
        var loader = new FakeResourceLoader(SanguoBuildingsCatalogLoader.BuildingsResPath, "[]");
        var ok = SanguoBuildingsCatalogLoader.TryLoadBuildingsCatalog(loader, out _, out var error);
        ok.Should().BeFalse();
        error.Should().Contain("root_not_object");
    }

    // ACC:T58.1
    [Fact]
    public void ShouldRejectBadVersions_WhenLoadingBuildingsCatalog()
    {
        var json = "{\"schemaVersion\":0,\"version\":0,\"buildings\":[]}";
        var loader = new FakeResourceLoader(SanguoBuildingsCatalogLoader.BuildingsResPath, json);
        var ok = SanguoBuildingsCatalogLoader.TryLoadBuildingsCatalog(loader, out _, out var error);
        ok.Should().BeFalse();
        error.Should().Contain("bad_versions");
    }

    // ACC:T58.1
    [Fact]
    public void ShouldRejectMissingEconomyStepDeltas_WhenLoadingBuildingsCatalog()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "buildings": [
            {
              "buildingId": "b1",
              "nameKey": "b1.name",
              "descriptionKey": "b1.desc",
              "maxLevel": 1,
              "buildCostBase": 0,
              "upgradeCostBase": 0,
              "settlementIncomeBase": 0
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(SanguoBuildingsCatalogLoader.BuildingsResPath, json);
        var ok = SanguoBuildingsCatalogLoader.TryLoadBuildingsCatalog(loader, out _, out var error);
        ok.Should().BeFalse();
        error.Should().Contain("missing_economy_step_deltas");
    }

    // ACC:T58.1
    [Fact]
    public void ShouldRejectNegativeCosts_WhenLoadingBuildingsCatalog()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "buildings": [
            {
              "buildingId": "b1",
              "nameKey": "b1.name",
              "descriptionKey": "b1.desc",
              "maxLevel": 1,
              "buildCostBase": -1,
              "upgradeCostBase": 0,
              "settlementIncomeBase": 0,
              "economyStepDeltas": { "buyPrice": 0, "toll": 0, "incomeSettlement": 0, "buildCost": 0, "upgradeCost": 0 }
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(SanguoBuildingsCatalogLoader.BuildingsResPath, json);
        var ok = SanguoBuildingsCatalogLoader.TryLoadBuildingsCatalog(loader, out _, out var error);
        ok.Should().BeFalse();
        error.Should().Contain("negative_cost_or_income");
    }

    // ACC:T58.4
    [Fact]
    public void ShouldCombineEventAndBuildingSteps_WhenSettlingMonthWithSeasonAdjustment()
    {
        var city = new City(
            id: "c1",
            name: "City1",
            regionId: "r1",
            basePrice: Money.Zero,
            baseToll: Money.FromMajorUnits(10),
            positionIndex: 0);

        var player = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        player.TryBuyCity(city, priceMultiplier: 1m).Should().BeTrue();

        var boardState = new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city });

        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        economy.SetActiveSeasonYieldAdjustment(
            year: 1,
            season: 1,
            affectedRegionIds: new[] { "r1" },
            yieldMultiplier: 1.5m);

        var treasury = new SanguoTreasury();

        // yieldMultiplier=1.5 => eventStepDelta=+1; buildingStepDelta=+2 => EffectiveSteps=5 => 2.5x; base toll 10 => income 25.
        var settlements = economy.SettleMonth(
            boardState: boardState,
            playerOrder: new[] { player.PlayerId },
            treasury: treasury,
            buildingIncomeSettlementStepDeltaProvider: _ => 2);

        settlements.Should().ContainSingle();
        settlements[0].AmountDelta.Should().Be(25m);
    }
}
