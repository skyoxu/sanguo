using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class SanguoDataCatalogContractsTests
{
    [Fact]
    public void ShouldConstructMapsCatalog_WhenInputIsValid()
    {
        var catalog = new SanguoMapsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Maps: new[]
            {
                new SanguoMapCatalogEntry(
                    MapId: "map001",
                    NameKey: "maps.map001.name",
                    DescriptionKey: "maps.map001.description",
                    Path: "res://Data/maps/map001.json",
                    RecommendedPlayersMin: 4,
                    RecommendedPlayersMax: 8,
                    ContentVersion: 1,
                    PreviewResPath: "res://Assets/Maps/map001_preview.png"),
            });

        catalog.SchemaVersion.Should().Be(1);
        catalog.Version.Should().Be(1);
        catalog.Maps.Should().HaveCount(1);
        var map = catalog.Maps[0];
        map.MapId.Should().Be("map001");
        map.Path.Should().StartWith("res://Data/maps/", "catalog path should stay in governed data root");
        map.RecommendedPlayersMin.Should().BeLessOrEqualTo(map.RecommendedPlayersMax);
        map.ContentVersion.Should().BePositive();
        map.PreviewResPath.Should().StartWith("res://Assets/", "preview should be asset-scoped");
    }

    [Fact]
    public void ShouldConstructFacilitiesCatalog_WhenInputIsValid()
    {
        var catalog = new SanguoFacilitiesCatalog(
            SchemaVersion: 1,
            Version: 1,
            Facilities: new[]
            {
                new SanguoFacilityDefinition(
                    FacilityId: "facility_shop",
                    FacilityKind: "shop",
                    NameKey: "facilities.shop.name",
                    DescriptionKey: "facilities.shop.description",
                    Actions: new[]
                    {
                        new SanguoFacilityActionDefinition(
                            ActionId: "buy",
                            NameKey: "actions.buy.name",
                            IconResPath: "res://Assets/Icons/buy.png",
                            Params: new Dictionary<string, string> { { "kind", "shop" } }),
                    }),
            });

        catalog.Facilities.Should().HaveCount(1);
        var facility = catalog.Facilities[0];
        facility.FacilityKind.Should().Be("shop");
        facility.Actions.Should().HaveCount(1);
        var action = facility.Actions[0];
        action.ActionId.Should().Be("buy");
        action.IconResPath.Should().StartWith("res://Assets/");
        action.Params.Should().NotBeNull();
        action.Params!.Should().ContainKey("kind").WhoseValue.Should().Be("shop");
    }

    [Fact]
    public void ShouldConstructRegionsCatalog_WhenInputIsValid()
    {
        var catalog = new SanguoRegionsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Regions: new[]
            {
                new SanguoRegionDefinition(
                    RegionId: "region_001",
                    NameKey: "regions.region_001.name",
                    DescriptionKey: "regions.region_001.description",
                    EffectKind: SanguoEffectKinds.EconomyStepDelta,
                    EffectParams: new Dictionary<string, string>(),
                    EconomyStepDeltas: new SanguoEconomyStepDeltas(0, 0, 0, 0, 0)),
            });

        catalog.Regions.Should().HaveCount(1);
        var region = catalog.Regions[0];
        region.EffectKind.Should().Be(SanguoEffectKinds.EconomyStepDelta);
        region.EconomyStepDeltas.BuyPrice.Should().Be(0);
        region.EconomyStepDeltas.Toll.Should().Be(0);
        region.EconomyStepDeltas.IncomeSettlement.Should().Be(0);
    }

    [Fact]
    public void ShouldConstructRelicsCatalog_WhenInputIsValid()
    {
        var catalog = new SanguoRelicsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Relics: new[]
            {
                new SanguoRelicDefinition(
                    RelicId: "relic_001",
                    NameKey: "relics.relic_001.name",
                    DescriptionKey: "relics.relic_001.description",
                    EffectKind: SanguoEffectKinds.MoneyDelta,
                    MoneyDelta: 10,
                    EconomyStepDelta: null),
            });

        catalog.Relics.Should().HaveCount(1);
        var relic = catalog.Relics[0];
        relic.EffectKind.Should().Be(SanguoEffectKinds.MoneyDelta);
        relic.MoneyDelta.Should().Be(10);
        relic.EconomyStepDelta.Should().BeNull();
    }

    [Fact]
    public void ShouldAllowFacilityActionParamsToBeNull_WhenActionHasNoDynamicPayload()
    {
        var facility = new SanguoFacilityDefinition(
            FacilityId: "facility_hospital",
            FacilityKind: "hospital",
            NameKey: "facilities.hospital.name",
            DescriptionKey: "facilities.hospital.description",
            Actions: new[]
            {
                new SanguoFacilityActionDefinition(
                    ActionId: "heal",
                    NameKey: "actions.heal.name",
                    IconResPath: "res://Assets/Icons/heal.png",
                    Params: null),
            });

        facility.Actions.Should().HaveCount(1);
        facility.Actions[0].Params.Should().BeNull("contract permits null params for payload-free actions");
    }
}
