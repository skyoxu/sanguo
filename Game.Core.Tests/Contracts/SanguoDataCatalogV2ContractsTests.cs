using System;
using System.IO;
using System.Linq;
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
    public void ShouldDeserializeMapDefinitionV2_WhenReadingDataMapJson()
    {
        var repoRoot = FindRepoRoot();
        var json = File.ReadAllText(Path.Combine(repoRoot, "Data", "maps", "map001.json"));
        var map = JsonSerializer.Deserialize<SanguoMapDefinitionV2>(json, JsonOptions);
        map.Should().NotBeNull();
        map!.MapId.Should().Be("map001");
        map.SchemaVersion.Should().Be(1);
        map.Version.Should().BeGreaterOrEqualTo(1);
        map.Track.Length.Should().Be(45);
        map.Track.StartTileId.Should().Be("tile_01");
        map.Tiles.Should().HaveCount(45);
        map.Tiles.Should().Contain(tile => tile.TileId == "tile_07" && tile.FacilityId == "facility_battlefield");
        map.Tiles.Should().Contain(tile => tile.TileId == "tile_04" && tile.EventPoolId == "default");
    }

    [Fact]
    public void ShouldDeserializeMapsCatalog_WhenReadingDataMapsIndexJson()
    {
        var repoRoot = FindRepoRoot();
        var json = File.ReadAllText(Path.Combine(repoRoot, "Data", "maps", "_index.json"));
        var catalog = JsonSerializer.Deserialize<SanguoMapsCatalog>(json, JsonOptions);
        catalog.Should().NotBeNull();
        catalog!.SchemaVersion.Should().Be(1);
        catalog.Version.Should().BeGreaterOrEqualTo(1);
        catalog.Maps.Should().NotBeEmpty();
        var first = catalog.Maps[0];
        first.MapId.Should().NotBeNullOrWhiteSpace();
        first.Path.Should().StartWith("res://Data/maps/");
        first.PreviewResPath.Should().StartWith("res://Assets/");
        first.RecommendedPlayersMin.Should().BeLessOrEqualTo(first.RecommendedPlayersMax);
    }

    [Fact]
    public void ShouldDeserializeRandomEventsCatalog_WhenReadingDataRandomEventsJson()
    {
        var repoRoot = FindRepoRoot();
        var json = File.ReadAllText(Path.Combine(repoRoot, "Data", "random_events.json"));
        var catalog = JsonSerializer.Deserialize<SanguoRandomEventsCatalog>(json, JsonOptions);
        catalog.Should().NotBeNull();
        catalog!.Events.Should().NotBeEmpty();
        catalog.EventPools.Should().NotBeEmpty();
        catalog.Events.Should().Contain(e =>
            e.EventId == "event_combat_small" &&
            e.EffectKind == "startCombat" &&
            e.EncounterId == "enc_event_combat_small" &&
            e.EncounterTarget == 10);
        catalog.EventPools.Should().Contain(p =>
            p.PoolId == "default" &&
            p.EventIds.Any(id => id == "event_combat_small"));
    }

    [Fact]
    public void ShouldDeserializeActionCardsCatalog_WhenReadingDataActionCardsJson()
    {
        var repoRoot = FindRepoRoot();
        var json = File.ReadAllText(Path.Combine(repoRoot, "Data", "action_cards.json"));
        var catalog = JsonSerializer.Deserialize<SanguoActionCardsCatalog>(json, JsonOptions);
        catalog.Should().NotBeNull();
        catalog!.Cards.Should().NotBeEmpty();
        catalog.Cards.Should().Contain(card =>
            card.CardId == "card_coupon" &&
            card.EffectKind == "economyStepDelta" &&
            card.StepDelta == -1 &&
            card.DurationRounds == 3);
    }

    [Fact]
    public void ShouldThrowJsonException_WhenMapDefinitionJsonIsMalformed()
    {
        var malformed = "{ \"schemaVersion\": 1, \"version\": 1, \"mapId\": \"broken\",";
        var act = () => JsonSerializer.Deserialize<SanguoMapDefinitionV2>(malformed, JsonOptions);
        act.Should().Throw<JsonException>();
    }

    [Fact]
    public void ShouldLeaveTilesAndTrackNull_WhenMapDefinitionMissingRequiredSections()
    {
        var missingRequired = """
            {
              "schemaVersion": 1,
              "version": 1,
              "mapId": "map_missing_required"
            }
            """;

        var map = JsonSerializer.Deserialize<SanguoMapDefinitionV2>(missingRequired, JsonOptions);
        map.Should().NotBeNull();
        map!.Track.Should().BeNull("record members default to null when required JSON sections are omitted");
        map.Tiles.Should().BeNull("missing tiles should not be silently treated as a valid list");
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
