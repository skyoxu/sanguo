using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task218StateFailureTilesGameoverTests
{
    // ACC:T218.1
    [Fact]
    public void ShouldRejectMapDefinition_WhenTilesAreEmpty()
    {
        var map = new SanguoMapDefinitionV2(
            SchemaVersion: 1,
            Version: 1,
            MapId: "map-task-218-empty",
            Track: new SanguoMapTrackDefinitionV2(Length: 1, StartTileId: "t0"),
            Tiles: Array.Empty<SanguoMapTileDefinitionV2>());

        var ok = SanguoMapDefinitionV2Validator.TryValidate(map, out var errors);

        ok.Should().BeFalse();
        errors.Should().Contain("Tiles must contain at least one tile.");
    }

    // ACC:T218.2
    [Fact]
    public void ShouldAllowFirstTileAccess_WhenTilesContainStartTile()
    {
        var map = new SanguoMapDefinitionV2(
            SchemaVersion: 1,
            Version: 1,
            MapId: "map-task-218-valid",
            Track: new SanguoMapTrackDefinitionV2(Length: 1, StartTileId: "t0"),
            Tiles: new List<SanguoMapTileDefinitionV2>
            {
                new(
                    TileId: "t0",
                    TileKind: SanguoMapTileDefinitionV2.TileKindEmpty,
                    NameKey: "sanguo.tile.empty.task218",
                    Layout: new SanguoMapTileLayoutV2(X: 0.0, Y: 0.0),
                    Actions: new List<SanguoMapTileActionV2>())
            });

        var ok = SanguoMapDefinitionV2Validator.TryValidate(map, out var errors);

        ok.Should().BeTrue(string.Join(" | ", errors));
        map.Tiles[0].TileId.Should().Be(map.Track.StartTileId);
    }
}
