using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using Game.Core.Services.Sanguo;
using System;
using System.Collections.Generic;
using System.Text;
using Xunit;

namespace Game.Core.Tests.Tasks;

// ADR-0006-data-storage (Accepted): Regions catalog is data-driven configuration.
// ADR-0004-event-bus-and-contracts (Accepted): Region capture affects economic calculation via explicit contracts/multipliers.
public sealed class Task64RegionsTests
{
    private sealed class InMemoryResourceLoader : IResourceLoader
    {
        private readonly string? _text;

        public InMemoryResourceLoader(string? text) => _text = text;

        public string? LoadText(string path)
        {
            if (string.Equals(path, SanguoRegionsCatalogLoader.RegionsResPath, StringComparison.Ordinal))
                return _text;
            return null;
        }

        public byte[]? LoadBytes(string path) => null;
    }

    private sealed class FileResourceLoader : IResourceLoader
    {
        public FileResourceLoader() { }

        public string? LoadText(string path) => null;

        public byte[]? LoadBytes(string path) => null;
    }

    // ACC:T64.1
    [Fact]
    public void GivenRegionsJsonMissingOrInvalid_WhenLoadingCatalog_ThenShouldRefuseToStart()
    {
        var missingLoader = new InMemoryResourceLoader(text: null);
        var okMissing = SanguoRegionsCatalogLoader.TryLoadRegionsCatalog(missingLoader, out _, out var errMissing);
        okMissing.Should().BeFalse();
        errMissing.Should().Be("regions_catalog_missing");

        var invalidJsonLoader = new InMemoryResourceLoader(text: "{not-json}");
        var okInvalid = SanguoRegionsCatalogLoader.TryLoadRegionsCatalog(invalidJsonLoader, out _, out var errInvalid);
        okInvalid.Should().BeFalse();
        errInvalid.Should().StartWith("regions_catalog_json_parse_failed:");

        var missingFieldsJson =
            "{\"schemaVersion\":1,\"version\":1,\"regions\":[{\"regionId\":\"r1\",\"nameKey\":\"region.r1\",\"descriptionKey\":\"region.r1.desc\",\"effectKind\":\"economyStepDelta\"}]}";
        var missingFieldsLoader = new InMemoryResourceLoader(text: missingFieldsJson);
        var okMissingFields = SanguoRegionsCatalogLoader.TryLoadRegionsCatalog(missingFieldsLoader, out _, out var errMissingFields);
        okMissingFields.Should().BeFalse();
        errMissingFields.Should().Be("invalid_regions_catalog:missing_economy_step_deltas");

        var missingNameKeyJson =
            "{\"schemaVersion\":1,\"version\":1,\"regions\":[{\"regionId\":\"r1\",\"descriptionKey\":\"region.r1.desc\",\"effectKind\":\"economyStepDelta\",\"economyStepDeltas\":{\"buyPrice\":0,\"toll\":1,\"incomeSettlement\":0,\"buildCost\":0,\"upgradeCost\":0}}]}";
        var missingNameKeyLoader = new InMemoryResourceLoader(text: missingNameKeyJson);
        var okMissingNameKey = SanguoRegionsCatalogLoader.TryLoadRegionsCatalog(missingNameKeyLoader, out _, out var errMissingNameKey);
        okMissingNameKey.Should().BeFalse();
        errMissingNameKey.Should().Be("invalid_regions_catalog:missing_name_key");

        var missingDescriptionKeyJson =
            "{\"schemaVersion\":1,\"version\":1,\"regions\":[{\"regionId\":\"r1\",\"nameKey\":\"region.r1\",\"effectKind\":\"economyStepDelta\",\"economyStepDeltas\":{\"buyPrice\":0,\"toll\":1,\"incomeSettlement\":0,\"buildCost\":0,\"upgradeCost\":0}}]}";
        var missingDescriptionKeyLoader = new InMemoryResourceLoader(text: missingDescriptionKeyJson);
        var okMissingDescriptionKey = SanguoRegionsCatalogLoader.TryLoadRegionsCatalog(missingDescriptionKeyLoader, out _, out var errMissingDescriptionKey);
        okMissingDescriptionKey.Should().BeFalse();
        errMissingDescriptionKey.Should().Be("invalid_regions_catalog:missing_description_key");

        var missingEffectKindJson =
            "{\"schemaVersion\":1,\"version\":1,\"regions\":[{\"regionId\":\"r1\",\"nameKey\":\"region.r1\",\"descriptionKey\":\"region.r1.desc\",\"economyStepDeltas\":{\"buyPrice\":0,\"toll\":1,\"incomeSettlement\":0,\"buildCost\":0,\"upgradeCost\":0}}]}";
        var missingEffectKindLoader = new InMemoryResourceLoader(text: missingEffectKindJson);
        var okMissingEffectKind = SanguoRegionsCatalogLoader.TryLoadRegionsCatalog(missingEffectKindLoader, out _, out var errMissingEffectKind);
        okMissingEffectKind.Should().BeFalse();
        errMissingEffectKind.Should().Be("invalid_regions_catalog:missing_effect_kind");

        var missingRegionIdJson =
            "{\"schemaVersion\":1,\"version\":1,\"regions\":[{\"nameKey\":\"region.r1\",\"descriptionKey\":\"region.r1.desc\",\"effectKind\":\"economyStepDelta\",\"economyStepDeltas\":{\"buyPrice\":0,\"toll\":1,\"incomeSettlement\":0,\"buildCost\":0,\"upgradeCost\":0}}]}";
        var missingRegionIdLoader = new InMemoryResourceLoader(text: missingRegionIdJson);
        var okMissingRegionId = SanguoRegionsCatalogLoader.TryLoadRegionsCatalog(missingRegionIdLoader, out _, out var errMissingRegionId);
        okMissingRegionId.Should().BeFalse();
        errMissingRegionId.Should().Be("invalid_regions_catalog:missing_region_id");
    }

    // ACC:T64.2
    [Fact]
    public void GivenCityMissingOrUnknownRegionId_WhenValidatingGameInitialization_ThenShouldRefuseToStart()
    {
        var regionsJson = """
                          {
                            "schemaVersion": 1,
                            "version": 1,
                            "regions": [
                              {
                                "regionId": "r1",
                                "nameKey": "region.r1",
                                "descriptionKey": "region.r1.desc",
                                "effectKind": "economyStepDelta",
                                "economyStepDeltas": { "buyPrice": 0, "toll": 1, "incomeSettlement": 0, "buildCost": 0, "upgradeCost": 0 }
                              }
                            ]
                          }
                          """;
        var catalog = SanguoRegionsCatalogLoader.ParseAndValidate(regionsJson);
        var knownRegionIds = new HashSet<string>(StringComparer.Ordinal) { catalog.Regions[0].RegionId };

        var mapA = new SanguoMapDefinitionV2(
            SchemaVersion: 1,
            Version: 1,
            MapId: "mapA",
            Track: new SanguoMapTrackDefinitionV2(Length: 1, StartTileId: "t0"),
            Tiles: new List<SanguoMapTileDefinitionV2>
            {
                new(
                    TileId: "t0",
                    TileKind: SanguoMapTileDefinitionV2.TileKindCity,
                    NameKey: "tile.city",
                    Layout: new SanguoMapTileLayoutV2(X: 0.0, Y: 0.0),
                    Actions: new List<SanguoMapTileActionV2> { new("buy_land", "res://Assets/Icons/buy.png") },
                    RegionId: "r1",
                    City: new SanguoMapCityTileV2(BasePrice: 100, BaseToll: 10, AllowedBuildingIds: new[] { "b_house" })
                ),
            });
        SanguoMapDefinitionV2Validator.TryValidate(mapA, knownRegionIds, out var mapAErrors).Should().BeTrue(string.Join(" | ", mapAErrors));

        var mapB = mapA with { MapId = "mapB" };
        SanguoMapDefinitionV2Validator.TryValidate(mapB, knownRegionIds, out var mapBErrors).Should().BeTrue(string.Join(" | ", mapBErrors));

        var missingRegion = mapA with
        {
            Tiles = new List<SanguoMapTileDefinitionV2>
            {
                mapA.Tiles[0] with { RegionId = null },
            },
        };
        SanguoMapDefinitionV2Validator.TryValidate(missingRegion, knownRegionIds, out var missingErrors).Should().BeFalse();
        missingErrors.Should().Contain(e => e.Contains("RegionId must be provided for city tiles", StringComparison.Ordinal));

        var unknownRegion = mapA with
        {
            Tiles = new List<SanguoMapTileDefinitionV2>
            {
                mapA.Tiles[0] with { RegionId = "region-does-not-exist" },
            },
        };
        SanguoMapDefinitionV2Validator.TryValidate(unknownRegion, knownRegionIds, out var unknownErrors).Should().BeFalse();
        unknownErrors.Should().Contain(e => e.Contains("RegionId must exist in regions catalog", StringComparison.Ordinal));
    }

    // ACC:T64.3
    [Fact]
    public void GivenLastCityCaptured_WhenRecomputingRegionBonus_ThenBonusActivatesImmediatelyAndRemovesOnOwnershipChange()
    {
        var cityRegionIds = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["c1"] = "r1",
            ["c2"] = "r1",
        };

        var cityOwnerIds = new Dictionary<string, string?>(StringComparer.Ordinal)
        {
            ["c1"] = "p1",
            ["c2"] = null,
        };

        var regionDeltas = new Dictionary<string, SanguoEconomyStepDeltas>(StringComparer.Ordinal)
        {
            ["r1"] = new(0, 2, 0, 0, 0),
        };

        var deltaBeforeCapture = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "c1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);
        deltaBeforeCapture.Should().Be(0);

        cityOwnerIds["c2"] = "p1";

        var deltaAfterCapture = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "c1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);
        deltaAfterCapture.Should().Be(2);

        cityOwnerIds["c2"] = null;

        var deltaAfterUnowned = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "c1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);
        deltaAfterUnowned.Should().Be(0);

        cityOwnerIds["c2"] = "p1";

        var deltaAfterRecapture = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "c1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);
        deltaAfterRecapture.Should().Be(2);

        cityOwnerIds["c2"] = "p2";

        var deltaAfterTakeover = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "c1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);
        deltaAfterTakeover.Should().Be(0);

        cityOwnerIds["c1"] = null;
        cityOwnerIds["c2"] = null;

        var deltaAfterEliminationRelease = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "c1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);
        deltaAfterEliminationRelease.Should().Be(0);
    }

    // ACC:T64.4
    [Fact]
    public void GivenBonusActiveForOneRegion_WhenComputingDeltas_ThenOtherRegionsRemainUnchangedAndRemovalStopsApplying()
    {
        var cityRegionIds = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["a1"] = "r1",
            ["a2"] = "r1",
            ["b1"] = "r2",
            ["b2"] = "r2",
        };

        var cityOwnerIds = new Dictionary<string, string?>(StringComparer.Ordinal)
        {
            ["a1"] = "p1",
            ["a2"] = "p1",
            ["b1"] = "p2",
            ["b2"] = "p2",
        };

        var regionDeltas = new Dictionary<string, SanguoEconomyStepDeltas>(StringComparer.Ordinal)
        {
            ["r1"] = new(0, 3, 0, 0, 0),
            ["r2"] = new(0, 7, 0, 0, 0),
        };

        var r1DeltaA1 = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "a1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);

        var r1DeltaA2 = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "a2",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);

        var r2DeltaB1 = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "b1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);

        r1DeltaA1.Should().Be(3);
        r1DeltaA2.Should().Be(3);
        r2DeltaB1.Should().Be(7);

        cityOwnerIds["a2"] = null;

        var r1DeltaAfterRemoval = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "a1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);

        r1DeltaAfterRemoval.Should().Be(0);

        var r2DeltaAfterRemoval = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "b1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);

        r2DeltaAfterRemoval.Should().Be(7);
    }
}
