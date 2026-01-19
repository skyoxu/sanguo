using System;
using System.IO;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class SanguoDataCatalogV2ContractsTests
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 64,
    };

    [Fact]
    public void MapDefinitionV2_ShouldDeserialize_FromDataMapJson()
    {
        var repoRoot = FindRepoRoot();
        var json = File.ReadAllText(Path.Combine(repoRoot, "Data", "maps", "map001.json"));
        var map = JsonSerializer.Deserialize<SanguoMapDefinitionV2>(json, JsonOptions);
        map.Should().NotBeNull();
        map!.Tiles.Should().HaveCount(45);
        map.MapId.Should().Be("map001");
    }

    [Fact]
    public void RandomEventsCatalog_ShouldDeserialize_FromDataRandomEventsJson()
    {
        var repoRoot = FindRepoRoot();
        var json = File.ReadAllText(Path.Combine(repoRoot, "Data", "random_events.json"));
        var catalog = JsonSerializer.Deserialize<SanguoRandomEventsCatalog>(json, JsonOptions);
        catalog.Should().NotBeNull();
        catalog!.Events.Should().NotBeEmpty();
        catalog.EventPools.Should().NotBeEmpty();
    }

    [Fact]
    public void ActionCardsCatalog_ShouldDeserialize_FromDataActionCardsJson()
    {
        var repoRoot = FindRepoRoot();
        var json = File.ReadAllText(Path.Combine(repoRoot, "Data", "action_cards.json"));
        var catalog = JsonSerializer.Deserialize<SanguoActionCardsCatalog>(json, JsonOptions);
        catalog.Should().NotBeNull();
        catalog!.Cards.Should().NotBeEmpty();
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
