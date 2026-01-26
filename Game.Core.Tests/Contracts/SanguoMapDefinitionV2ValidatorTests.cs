using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using System.Collections.Generic;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class SanguoMapDefinitionV2ValidatorTests
{
    [Fact]
    public void ShouldFail_WhenMapIsNull()
    {
        SanguoMapDefinitionV2Validator.TryValidate(null, out var errors).Should().BeFalse();
        errors.Should().ContainSingle(e => e.Contains("Map definition is null"));
    }

    [Fact]
    public void ShouldFail_WhenTilesIsNull()
    {
        var map = new SanguoMapDefinitionV2(
            SchemaVersion: 1,
            Version: 1,
            MapId: "map001",
            Track: new SanguoMapTrackDefinitionV2(Length: 1, StartTileId: "t0"),
            Tiles: null!);

        SanguoMapDefinitionV2Validator.TryValidate(map, out var errors).Should().BeFalse();
        errors.Should().Contain(e => e.Contains("Tiles must be provided"));
    }

    [Fact]
    public void ShouldValidate_WhenMapIsValid_AndCoversAllTileKinds()
    {
        var map = new SanguoMapDefinitionV2(
            SchemaVersion: 1,
            Version: 1,
            MapId: "map001",
            Track: new SanguoMapTrackDefinitionV2(Length: 4, StartTileId: "t0"),
            Tiles: new List<SanguoMapTileDefinitionV2>
            {
                new(
                    TileId: "t0",
                    TileKind: SanguoMapTileDefinitionV2.TileKindCity,
                    NameKey: "tile.city.start",
                    Layout: new SanguoMapTileLayoutV2(X: 0.0, Y: 0.0),
                    Actions: new List<SanguoMapTileActionV2> { new("buy_land", "res://Assets/Icons/buy.png") },
                    RegionId: "region-1",
                    City: new SanguoMapCityTileV2(BasePrice: 100, BaseToll: 10, AllowedBuildingIds: new[] { "b_house" })
                ),
                new(
                    TileId: "t1",
                    TileKind: SanguoMapTileDefinitionV2.TileKindFacility,
                    NameKey: "tile.facility.shop",
                    Layout: new SanguoMapTileLayoutV2(X: 0.25, Y: 0.25),
                    Actions: new List<SanguoMapTileActionV2> { new("enter", "res://Assets/Icons/shop.webp") },
                    FacilityId: "shop-001"
                ),
                new(
                    TileId: "t2",
                    TileKind: SanguoMapTileDefinitionV2.TileKindEvent,
                    NameKey: "tile.event",
                    Layout: new SanguoMapTileLayoutV2(X: 0.50, Y: 0.50),
                    Actions: new List<SanguoMapTileActionV2> { new("trigger_event", "res://Assets/Icons/event.svg") },
                    EventPoolId: "events-default"
                ),
                new(
                    TileId: "t3",
                    TileKind: SanguoMapTileDefinitionV2.TileKindEmpty,
                    NameKey: "tile.empty",
                    Layout: new SanguoMapTileLayoutV2(X: 1.0, Y: 1.0),
                    Actions: new List<SanguoMapTileActionV2>()
                ),
            });

        var ok = SanguoMapDefinitionV2Validator.TryValidate(map, out var errors);
        ok.Should().BeTrue();
        errors.Should().BeEmpty();
    }

    [Fact]
    public void ShouldFail_WhenTrackIsMissingOrInvalid()
    {
        var tile = new SanguoMapTileDefinitionV2(
            TileId: "t0",
            TileKind: SanguoMapTileDefinitionV2.TileKindEmpty,
            NameKey: "tile.empty",
            Layout: new SanguoMapTileLayoutV2(X: 0.0, Y: 0.0),
            Actions: new List<SanguoMapTileActionV2>());

        var missingTrack = new SanguoMapDefinitionV2(
            SchemaVersion: 1,
            Version: 1,
            MapId: "map001",
            Track: null!,
            Tiles: new List<SanguoMapTileDefinitionV2> { tile });

        SanguoMapDefinitionV2Validator.TryValidate(missingTrack, out var missingTrackErrors).Should().BeFalse();
        missingTrackErrors.Should().Contain(e => e.Contains("Track must be provided"));

        var invalidTrack = new SanguoMapDefinitionV2(
            SchemaVersion: 1,
            Version: 1,
            MapId: "map001",
            Track: new SanguoMapTrackDefinitionV2(Length: 0, StartTileId: " "),
            Tiles: new List<SanguoMapTileDefinitionV2>());

        SanguoMapDefinitionV2Validator.TryValidate(invalidTrack, out var invalidTrackErrors).Should().BeFalse();
        invalidTrackErrors.Should().Contain(e => e.Contains("Track.Length must be greater than 0"));
        invalidTrackErrors.Should().Contain(e => e.Contains("Track.StartTileId must be non-empty"));
    }

    [Fact]
    public void ShouldFail_WhenCityPayloadHasInvalidValues()
    {
        var map = new SanguoMapDefinitionV2(
            SchemaVersion: 1,
            Version: 1,
            MapId: "map001",
            Track: new SanguoMapTrackDefinitionV2(Length: 1, StartTileId: "t0"),
            Tiles: new List<SanguoMapTileDefinitionV2>
            {
                new(
                    TileId: "t0",
                    TileKind: SanguoMapTileDefinitionV2.TileKindCity,
                    NameKey: "tile.city",
                    Layout: new SanguoMapTileLayoutV2(X: 0.0, Y: 0.0),
                    Actions: new List<SanguoMapTileActionV2> { new("buy_land", "res://Assets/Icons/buy.png") },
                    RegionId: "region-1",
                    City: new SanguoMapCityTileV2(BasePrice: -1, BaseToll: -2, AllowedBuildingIds: null!)
                ),
            });

        SanguoMapDefinitionV2Validator.TryValidate(map, out var errors).Should().BeFalse();
        errors.Should().Contain(e => e.Contains("City.BasePrice must be non-negative"));
        errors.Should().Contain(e => e.Contains("City.BaseToll must be non-negative"));
        errors.Should().Contain(e => e.Contains("City.AllowedBuildingIds must be provided"));
    }

    [Fact]
    public void ShouldFail_WhenMapHasMultipleValidationErrors()
    {
        var map = new SanguoMapDefinitionV2(
            SchemaVersion: 0,
            Version: 0,
            MapId: " ",
            Track: new SanguoMapTrackDefinitionV2(Length: 6, StartTileId: "missing-start"),
            Tiles: new List<SanguoMapTileDefinitionV2>
            {
                new(
                    TileId: "t0",
                    TileKind: SanguoMapTileDefinitionV2.TileKindCity,
                    NameKey: " ",
                    Layout: null!,
                    Actions: null!,
                    RegionId: null,
                    City: null
                ),
                new(
                    TileId: "t1",
                    TileKind: SanguoMapTileDefinitionV2.TileKindFacility,
                    NameKey: "tile.facility",
                    Layout: new SanguoMapTileLayoutV2(X: -0.1, Y: 1.1),
                    Actions: new List<SanguoMapTileActionV2>(),
                    FacilityId: " "
                ),
                new(
                    TileId: "t2",
                    TileKind: SanguoMapTileDefinitionV2.TileKindEvent,
                    NameKey: "tile.event",
                    Layout: new SanguoMapTileLayoutV2(X: 0.5, Y: 0.5),
                    Actions: new List<SanguoMapTileActionV2>
                    {
                        null!,
                        new("", ""),
                        new("a1", "res://Bad/icon.txt"),
                        new("a1", "res://Assets/icon.bmp"),
                    },
                    EventPoolId: " "
                ),
                new(
                    TileId: "t2",
                    TileKind: "castle",
                    NameKey: "",
                    Layout: new SanguoMapTileLayoutV2(X: 0.2, Y: 0.2),
                    Actions: new List<SanguoMapTileActionV2> { new("a2", "res://Assets/icon") }
                ),
                null!,
            });

        var ok = SanguoMapDefinitionV2Validator.TryValidate(map, out var errors);
        ok.Should().BeFalse();
        errors.Should().NotBeEmpty();
        errors.Should().Contain(e => e.Contains("SchemaVersion must be greater than 0"));
        errors.Should().Contain(e => e.Contains("Version must be greater than 0"));
        errors.Should().Contain(e => e.Contains("MapId must be non-empty"));
        errors.Should().Contain(e => e.Contains("Tiles.Count must match Track.Length"));
        errors.Should().Contain(e => e.Contains("Track.StartTileId must exist in Tiles"));
    }

    [Fact]
    public void ShouldFail_WhenKnownRegionIdsProvided_AndCityRegionIdUnknown()
    {
        var map = new SanguoMapDefinitionV2(
            SchemaVersion: 1,
            Version: 1,
            MapId: "map001",
            Track: new SanguoMapTrackDefinitionV2(Length: 1, StartTileId: "t0"),
            Tiles: new List<SanguoMapTileDefinitionV2>
            {
                new(
                    TileId: "t0",
                    TileKind: SanguoMapTileDefinitionV2.TileKindCity,
                    NameKey: "tile.city.start",
                    Layout: new SanguoMapTileLayoutV2(X: 0.0, Y: 0.0),
                    Actions: new List<SanguoMapTileActionV2>(),
                    RegionId: "region-unknown",
                    City: new SanguoMapCityTileV2(BasePrice: 100, BaseToll: 10, AllowedBuildingIds: new[] { "b_house" })
                ),
            });

        var knownRegionIds = new HashSet<string>(System.StringComparer.Ordinal) { "region-1" };

        var ok = SanguoMapDefinitionV2Validator.TryValidate(map, knownRegionIds, out var errors);

        ok.Should().BeFalse();
        errors.Should().Contain(e => e.Contains("RegionId must exist in regions catalog", System.StringComparison.Ordinal));
    }
}
