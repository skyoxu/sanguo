using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using Game.Core.Services.Sanguo;
using System;
using System.Collections.Generic;
using Xunit;

namespace Game.Core.Tests.Services;

public class SanguoRegionsCatalogLoaderTests
{
    [Fact]
    public void ParseAndValidate_ShouldParseValidCatalog_WhenUsingStringVersion()
    {
        var json = """
                   {
                     "schemaVersion": 1,
                     "version": "1",
                     "regions": [
                       {
                         "regionId": "r2",
                         "nameKey": "region.r2",
                         "descriptionKey": "region.r2.desc",
                         "effectKind": "economyStepDelta",
                         "effectParams": { "k": "v" },
                         "economyStepDeltas": { "buyPrice": 0, "toll": 1, "incomeSettlement": 0, "buildCost": 0, "upgradeCost": 0 }
                       },
                       {
                         "regionId": "r1",
                         "nameKey": "region.r1",
                         "descriptionKey": "region.r1.desc",
                         "effectKind": "economyStepDelta",
                         "economyStepDeltas": { "buyPrice": 0, "toll": 2, "incomeSettlement": 0, "buildCost": 0, "upgradeCost": 0 }
                       }
                     ]
                   }
                   """;

        var catalog = SanguoRegionsCatalogLoader.ParseAndValidate(json);
        catalog.SchemaVersion.Should().Be(1);
        catalog.Version.Should().Be(1);
        catalog.Regions.Should().HaveCount(2);
        catalog.Regions[0].RegionId.Should().Be("r1");
        catalog.Regions[1].RegionId.Should().Be("r2");
        catalog.Regions[1].EffectParams.Should().ContainKey("k").WhoseValue.Should().Be("v");
        catalog.Regions[0].EconomyStepDeltas.Toll.Should().Be(2);
    }

    [Theory]
    [InlineData("[]", "invalid_regions_catalog:root_not_object")]
    [InlineData("{}", "invalid_regions_catalog:bad_versions")]
    [InlineData("{\"schemaVersion\":1,\"version\":1}", "invalid_regions_catalog:missing_regions")]
    [InlineData("{\"schemaVersion\":1,\"version\":1,\"regions\":[1]}", "invalid_regions_catalog:region_not_object")]
    public void ParseAndValidate_ShouldThrowInvalidOperation_WhenCatalogInvalid(string json, string expectedMessage)
    {
        Action act = () => _ = SanguoRegionsCatalogLoader.ParseAndValidate(json);
        act.Should().Throw<InvalidOperationException>().WithMessage(expectedMessage);
    }

    [Fact]
    public void ParseAndValidate_ShouldThrow_WhenRegionMissingRegionId()
    {
        var json = """
                   { "schemaVersion": 1, "version": 1, "regions": [
                     { "nameKey": "region.r1", "descriptionKey": "region.r1.desc", "effectKind": "economyStepDelta",
                       "economyStepDeltas": { "buyPrice": 0, "toll": 1, "incomeSettlement": 0, "buildCost": 0, "upgradeCost": 0 } }
                   ] }
                   """;

        Action act = () => _ = SanguoRegionsCatalogLoader.ParseAndValidate(json);
        act.Should().Throw<InvalidOperationException>().WithMessage("invalid_regions_catalog:missing_region_id");
    }

    [Fact]
    public void ParseAndValidate_ShouldThrow_WhenDuplicateRegionId()
    {
        var json = """
                   { "schemaVersion": 1, "version": 1, "regions": [
                     { "regionId": "r1", "nameKey": "region.r1", "descriptionKey": "region.r1.desc", "effectKind": "economyStepDelta",
                       "economyStepDeltas": { "buyPrice": 0, "toll": 1, "incomeSettlement": 0, "buildCost": 0, "upgradeCost": 0 } },
                     { "regionId": "r1", "nameKey": "region.r1b", "descriptionKey": "region.r1b.desc", "effectKind": "economyStepDelta",
                       "economyStepDeltas": { "buyPrice": 0, "toll": 1, "incomeSettlement": 0, "buildCost": 0, "upgradeCost": 0 } }
                   ] }
                   """;

        Action act = () => _ = SanguoRegionsCatalogLoader.ParseAndValidate(json);
        act.Should().Throw<InvalidOperationException>().WithMessage("invalid_regions_catalog:duplicate_region_id");
    }

    [Fact]
    public void ParseAndValidate_ShouldThrow_WhenEffectParamsNotObject()
    {
        var json = """
                   { "schemaVersion": 1, "version": 1, "regions": [
                     { "regionId": "r1", "nameKey": "region.r1", "descriptionKey": "region.r1.desc", "effectKind": "economyStepDelta", "effectParams": 1,
                       "economyStepDeltas": { "buyPrice": 0, "toll": 1, "incomeSettlement": 0, "buildCost": 0, "upgradeCost": 0 } }
                   ] }
                   """;

        Action act = () => _ = SanguoRegionsCatalogLoader.ParseAndValidate(json);
        act.Should().Throw<InvalidOperationException>().WithMessage("invalid_regions_catalog:effect_params_not_object");
    }

    [Fact]
    public void ParseAndValidate_ShouldThrow_WhenEffectParamsValueNotString()
    {
        var json = """
                   { "schemaVersion": 1, "version": 1, "regions": [
                     { "regionId": "r1", "nameKey": "region.r1", "descriptionKey": "region.r1.desc", "effectKind": "economyStepDelta", "effectParams": { "k": 1 },
                       "economyStepDeltas": { "buyPrice": 0, "toll": 1, "incomeSettlement": 0, "buildCost": 0, "upgradeCost": 0 } }
                   ] }
                   """;

        Action act = () => _ = SanguoRegionsCatalogLoader.ParseAndValidate(json);
        act.Should().Throw<InvalidOperationException>().WithMessage("invalid_regions_catalog:effect_params_not_string");
    }

    [Fact]
    public void ParseAndValidate_ShouldThrow_WhenEconomyStepDeltasMissingOrInvalid()
    {
        var missingEconomyStepDeltas =
            "{\"schemaVersion\":1,\"version\":1,\"regions\":[{\"regionId\":\"r1\",\"nameKey\":\"region.r1\",\"descriptionKey\":\"region.r1.desc\",\"effectKind\":\"economyStepDelta\"}]}";

        Action act1 = () => _ = SanguoRegionsCatalogLoader.ParseAndValidate(missingEconomyStepDeltas);
        act1.Should().Throw<InvalidOperationException>().WithMessage("invalid_regions_catalog:missing_economy_step_deltas");

        var missingField =
            "{\"schemaVersion\":1,\"version\":1,\"regions\":[{\"regionId\":\"r1\",\"nameKey\":\"region.r1\",\"descriptionKey\":\"region.r1.desc\",\"effectKind\":\"economyStepDelta\",\"economyStepDeltas\":{\"buyPrice\":0,\"toll\":1,\"incomeSettlement\":0,\"buildCost\":0}}]}";

        Action act2 = () => _ = SanguoRegionsCatalogLoader.ParseAndValidate(missingField);
        act2.Should().Throw<InvalidOperationException>().WithMessage("invalid_regions_catalog:bad_economy_step_deltas");
    }

    [Fact]
    public void TryLoadRegionsCatalog_ShouldReturnFalse_WhenLoaderReturnsNull()
    {
        var loader = new FakeLoader(text: null);
        var ok = SanguoRegionsCatalogLoader.TryLoadRegionsCatalog(loader, out var catalog, out var error);
        ok.Should().BeFalse();
        error.Should().Be("regions_catalog_missing");
        catalog.SchemaVersion.Should().Be(0);
    }

    [Fact]
    public void TryLoadRegionsCatalog_ShouldReturnTrue_WhenLoaderReturnsValidJson()
    {
        var loader = new FakeLoader(text: "{\"schemaVersion\":1,\"version\":1,\"regions\":[]}");
        var ok = SanguoRegionsCatalogLoader.TryLoadRegionsCatalog(loader, out var catalog, out var error);
        ok.Should().BeTrue();
        error.Should().BeEmpty();
        catalog.SchemaVersion.Should().Be(1);
    }

    private sealed class FakeLoader : IResourceLoader
    {
        private readonly string? _text;

        public FakeLoader(string? text)
        {
            _text = text;
        }

        public string? LoadText(string path) => _text;

        public byte[]? LoadBytes(string path) => null;
    }
}
