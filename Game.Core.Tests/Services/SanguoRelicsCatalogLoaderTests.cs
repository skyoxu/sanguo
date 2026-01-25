using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using Game.Core.Services.Sanguo;
using System;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class SanguoRelicsCatalogLoaderTests
{
    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenJsonMissing()
    {
        var loader = new FakeResourceLoader(path => null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out var catalog, out var error);

        ok.Should().BeFalse();
        error.Should().Be("relics_catalog_missing");
        catalog.Relics.Should().BeEmpty();
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldLoadAndSortByRelicId_WhenJsonValid()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "relics": [
            {
              "relicId": "relic_b",
              "nameKey": "relic.relic_b.name",
              "descriptionKey": "relic.relic_b.desc",
              "effectKind": "moneyDelta",
              "moneyDelta": 10
            },
            {
              "relicId": "relic_a",
              "nameKey": "relic.relic_a.name",
              "descriptionKey": "relic.relic_a.desc",
              "effectKind": "economyStepDelta",
              "stepDelta": 1
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? json : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out var catalog, out var error);

        ok.Should().BeTrue(error);
        error.Should().BeEmpty();
        catalog.SchemaVersion.Should().Be(1);
        catalog.Version.Should().Be(1);
        catalog.Relics.Should().HaveCount(2);
        catalog.Relics[0].RelicId.Should().Be("relic_a");
        catalog.Relics[1].RelicId.Should().Be("relic_b");
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenDuplicateRelicId()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "relics": [
            {
              "relicId": "relic_dup",
              "nameKey": "relic.relic_dup.name",
              "descriptionKey": "relic.relic_dup.desc",
              "effectKind": "moneyDelta",
              "moneyDelta": 10
            },
            {
              "relicId": "relic_dup",
              "nameKey": "relic.relic_dup2.name",
              "descriptionKey": "relic.relic_dup2.desc",
              "effectKind": "economyStepDelta",
              "stepDelta": 1
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? json : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_relics_catalog:duplicate_relic_id");
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenEffectKindNotAllowlisted()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "relics": [
            {
              "relicId": "relic_bad",
              "nameKey": "relic.relic_bad.name",
              "descriptionKey": "relic.relic_bad.desc",
              "effectKind": "teleport",
              "moneyDelta": 10
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? json : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_relics_catalog:invalid_effect_kind");
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenStepDeltaIsZero()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "relics": [
            {
              "relicId": "relic_step",
              "nameKey": "relic.relic_step.name",
              "descriptionKey": "relic.relic_step.desc",
              "effectKind": "economyStepDelta",
              "stepDelta": 0
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? json : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_relics_catalog:invalid_step_delta");
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenMoneyDeltaIsNonPositive()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "relics": [
            {
              "relicId": "relic_gold",
              "nameKey": "relic.relic_gold.name",
              "descriptionKey": "relic.relic_gold.desc",
              "effectKind": "moneyDelta",
              "moneyDelta": 0
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? json : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_relics_catalog:invalid_money_delta");
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenRelicsArrayMissing()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1
        }
        """;

        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? json : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_relics_catalog:missing_relics");
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenJsonIsMalformed()
    {
        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? "{ bad json" : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().StartWith("json_parse_failed:");
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenRootIsNotObject()
    {
        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? "[]" : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_relics_catalog:root_not_object");
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenRelicsIsNotArray()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "relics": { }
        }
        """;

        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? json : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_relics_catalog:relics_not_array");
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenRelicItemIsNotObject()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "relics": [ 1 ]
        }
        """;

        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? json : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_relics_catalog:relic_not_object");
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenMoneyDeltaMissingForMoneyDeltaRelic()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "relics": [
            {
              "relicId": "relic_gold",
              "nameKey": "relic.relic_gold.name",
              "descriptionKey": "relic.relic_gold.desc",
              "effectKind": "moneyDelta"
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? json : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_relics_catalog:missing_money_delta");
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenStepDeltaMissingForEconomyStepDeltaRelic()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "relics": [
            {
              "relicId": "relic_step",
              "nameKey": "relic.relic_step.name",
              "descriptionKey": "relic.relic_step.desc",
              "effectKind": "economyStepDelta"
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? json : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_relics_catalog:missing_step_delta");
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenSchemaVersionIsNonPositive()
    {
        var json = """
        {
          "schemaVersion": 0,
          "version": 1,
          "relics": []
        }
        """;

        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? json : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_relics_catalog:bad_versions");
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenRelicIdMissing()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "relics": [
            {
              "nameKey": "relic.missing_id.name",
              "descriptionKey": "relic.missing_id.desc",
              "effectKind": "moneyDelta",
              "moneyDelta": 10
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? json : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_relics_catalog:missing_relic_id");
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldFail_WhenNameKeyMissing()
    {
        var json = """
        {
          "schemaVersion": 1,
          "version": 1,
          "relics": [
            {
              "relicId": "relic_missing_name",
              "descriptionKey": "relic.relic_missing_name.desc",
              "effectKind": "moneyDelta",
              "moneyDelta": 10
            }
          ]
        }
        """;

        var loader = new FakeResourceLoader(path => path == SanguoRelicsCatalogLoader.RelicsResPath ? json : null);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_relics_catalog:missing_name_key");
    }

    private sealed class FakeResourceLoader : IResourceLoader
    {
        private readonly Func<string, string?> _loadText;

        public FakeResourceLoader(Func<string, string?> loadText)
        {
            _loadText = loadText;
        }

        public string? LoadText(string path) => _loadText(path);

        public byte[]? LoadBytes(string path) => null;
    }
}
