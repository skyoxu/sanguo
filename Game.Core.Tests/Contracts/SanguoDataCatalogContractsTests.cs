using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class SanguoDataCatalogContractsTests
{
    [Fact]
    public void MapsCatalog_ShouldBeConstructible()
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
        catalog.Maps.Should().HaveCount(1);
    }

    [Fact]
    public void FacilitiesCatalog_ShouldBeConstructible()
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
        catalog.Facilities[0].Actions.Should().HaveCount(1);
    }

    [Fact]
    public void RegionsCatalog_ShouldBeConstructible()
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
        catalog.Regions[0].EffectKind.Should().Be(SanguoEffectKinds.EconomyStepDelta);
    }

    [Fact]
    public void RelicsCatalog_ShouldBeConstructible()
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
        catalog.Relics[0].EffectKind.Should().Be(SanguoEffectKinds.MoneyDelta);
    }
}

