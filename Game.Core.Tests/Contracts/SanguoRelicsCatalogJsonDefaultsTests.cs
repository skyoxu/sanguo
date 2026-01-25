using System;
using System.IO;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class SanguoRelicsCatalogJsonDefaultsTests
{
    [Fact]
    public void RelicsCatalog_ShouldDeserialize_WithDefaultJsonOptions_FromDataRelicsJson()
    {
        var repoRoot = FindRepoRoot();
        var json = File.ReadAllText(Path.Combine(repoRoot, "Data", "relics.json"));

        // Stop-loss: this MUST work without PropertyNameCaseInsensitive=true.
        var catalog = JsonSerializer.Deserialize<SanguoRelicsCatalog>(json);

        catalog.Should().NotBeNull();
        catalog!.SchemaVersion.Should().BeGreaterThan(0);
        catalog.Version.Should().BeGreaterThan(0);
        catalog.Relics.Should().NotBeEmpty();
    }

    [Fact]
    public void RelicsCatalog_ShouldExposeStepDelta_WhenEffectKindIsEconomyStepDelta_WithDefaultJsonOptions()
    {
        var repoRoot = FindRepoRoot();
        var json = File.ReadAllText(Path.Combine(repoRoot, "Data", "relics.json"));
        var catalog = JsonSerializer.Deserialize<SanguoRelicsCatalog>(json);

        catalog.Should().NotBeNull();
        foreach (var relic in catalog!.Relics)
        {
            if (string.Equals(relic.EffectKind, SanguoEffectKinds.EconomyStepDelta, StringComparison.Ordinal))
            {
                relic.EconomyStepDelta.Should().NotBeNull();
            }
        }
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var marker = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(marker))
                return dir.FullName;
            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }
}

