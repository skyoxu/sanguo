using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task53MapConfigParsingTests
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 64,
    };

    // ACC:T53.1
    [Fact]
    public void ShouldDeserializeMapsCatalog_WhenIndexJsonIsValid()
    {
        var repoRoot = FindRepoRoot();
        var json = File.ReadAllText(Path.Combine(repoRoot, "Data", "maps", "_index.json"));
        var catalog = JsonSerializer.Deserialize<SanguoMapsCatalog>(json, JsonOptions);

        catalog.Should().NotBeNull();
        catalog!.SchemaVersion.Should().BeGreaterThan(0);
        catalog.Version.Should().BeGreaterThan(0);
        catalog.Maps.Should().NotBeEmpty();
    }

    // ACC:T53.2
    [Fact]
    public void ShouldContainRequiredMapCatalogFields_WhenDeserializingMapsCatalog()
    {
        var repoRoot = FindRepoRoot();
        var json = File.ReadAllText(Path.Combine(repoRoot, "Data", "maps", "_index.json"));
        var catalog = JsonSerializer.Deserialize<SanguoMapsCatalog>(json, JsonOptions);

        catalog.Should().NotBeNull();
        catalog!.Maps.Should().NotBeEmpty();

        foreach (var map in catalog.Maps)
        {
            map.MapId.Should().NotBeNullOrWhiteSpace();
            map.NameKey.Should().NotBeNullOrWhiteSpace();
            map.DescriptionKey.Should().NotBeNullOrWhiteSpace();
            map.Path.Should().NotBeNullOrWhiteSpace();
            map.PreviewResPath.Should().NotBeNullOrWhiteSpace();
            map.RecommendedPlayersMin.Should().BeGreaterThan(0);
            map.RecommendedPlayersMax.Should().BeGreaterThanOrEqualTo(map.RecommendedPlayersMin);
            map.ContentVersion.Should().BeGreaterThan(0);
        }
    }

    // ACC:T53.5
    // ACC:T53.6
    [Fact]
    public void ShouldParseAndValidateMapIndexAndDefinition_WhenUsingDataFiles()
    {
        var repoRoot = FindRepoRoot();
        var indexJson = File.ReadAllText(Path.Combine(repoRoot, "Data", "maps", "_index.json"));
        var catalog = JsonSerializer.Deserialize<SanguoMapsCatalog>(indexJson, JsonOptions);
        catalog.Should().NotBeNull();

        var mapEntry = catalog!.Maps.First(m => string.Equals(m.MapId, "map001", StringComparison.Ordinal));
        mapEntry.Path.Should().StartWith("res://Data/");

        var relative = mapEntry.Path.Replace("res://", string.Empty, StringComparison.Ordinal)
            .Replace("/", Path.DirectorySeparatorChar.ToString(), StringComparison.Ordinal);

        var mapJson = File.ReadAllText(Path.Combine(repoRoot, relative));
        var map = JsonSerializer.Deserialize<SanguoMapDefinitionV2>(mapJson, JsonOptions);
        map.Should().NotBeNull();

        SanguoMapDefinitionV2Validator.TryValidate(map, out var errors).Should().BeTrue();
        errors.Should().BeEmpty();
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

