using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task53MapConfigValidationTests
{
    // ACC:T53.2
    // ACC:T53.3
    [Fact]
    public void ShouldRejectFrozenStartTileIdMismatch_WhenValidatingMapDefinitionV2()
    {
        var tiles = new List<SanguoMapTileDefinitionV2>
        {
            new(
                TileId: "t0",
                TileKind: SanguoMapTileDefinitionV2.TileKindEvent,
                NameKey: "sanguo.tile.event.test",
                Layout: new SanguoMapTileLayoutV2(X: 0.1f, Y: 0.1f),
                RegionId: null,
                FacilityId: null,
                EventPoolId: "pool-default",
                Actions: new List<SanguoMapTileActionV2>
                {
                    new(ActionId: "trigger_event", IconResPath: "res://Assets/Icons/trigger_event.png"),
                },
                City: null)
            ,
            new(
                TileId: "t1",
                TileKind: SanguoMapTileDefinitionV2.TileKindEmpty,
                NameKey: "sanguo.tile.empty.test",
                Layout: new SanguoMapTileLayoutV2(X: 0.2f, Y: 0.2f),
                RegionId: null,
                FacilityId: null,
                EventPoolId: null,
                Actions: new List<SanguoMapTileActionV2>(),
                City: null)
        };

        var map = new SanguoMapDefinitionV2(
            SchemaVersion: 1,
            Version: 1,
            MapId: "map-test",
            Track: new SanguoMapTrackDefinitionV2(Length: 2, StartTileId: "t0"),
            Tiles: tiles);

        var mismatched = map with { Track = map.Track with { StartTileId = "t1" } };

        SanguoMapDefinitionV2Validator.TryValidate(mismatched, out var errors).Should().BeFalse();
        errors.Should().Contain(e => e.Contains("Track.StartTileId", StringComparison.Ordinal));
    }

    // ACC:T53.4
    [Fact]
    public void ShouldFailValidation_WhenTilesIsEmpty()
    {
        var map = new SanguoMapDefinitionV2(
            SchemaVersion: 1,
            Version: 1,
            MapId: "map-test",
            Track: new SanguoMapTrackDefinitionV2(Length: 1, StartTileId: "t0"),
            Tiles: Array.Empty<SanguoMapTileDefinitionV2>());

        SanguoMapDefinitionV2Validator.TryValidate(map, out var errors).Should().BeFalse();
        errors.Should().NotBeEmpty();
    }
}
