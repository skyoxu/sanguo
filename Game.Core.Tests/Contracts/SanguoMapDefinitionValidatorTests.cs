using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using System.Collections.Generic;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class SanguoMapDefinitionValidatorTests
{
    [Fact]
    public void ShouldFail_WhenMapIsNull()
    {
        SanguoMapDefinitionValidator.TryValidate(null, out var errors).Should().BeFalse();
        errors.Should().ContainSingle(e => e.Contains("Map definition is null"));
    }

    [Fact]
    public void ShouldValidate_WhenTilesCoverAllPositionsAndIdsUnique()
    {
        var map = new SanguoMapDefinition(
            MapId: "map001",
            TileCount: 3,
            Tiles: new[]
            {
                new SanguoTileDefinition(0, SanguoTileDefinition.TileTypeWild, "start", "Start", "s0", 0m, 0m, new[] { "random_event" }),
                new SanguoTileDefinition(1, SanguoTileDefinition.TileTypeCity, "c1", "City 1", "s1", 50m, 20m, new[] { "house_build" }),
                new SanguoTileDefinition(2, SanguoTileDefinition.TileTypePass, "pass1", "Pass 1", "s2", 0m, 0m, new[] { "enter_battle" }),
            });

        var ok = SanguoMapDefinitionValidator.TryValidate(map, out var errors);
        ok.Should().BeTrue();
        errors.Should().BeEmpty();
    }

    [Fact]
    public void ShouldValidate_WhenTileTypeUsesAnyCasing()
    {
        var map = new SanguoMapDefinition(
            MapId: "map001",
            TileCount: 1,
            Tiles: new[]
            {
                new SanguoTileDefinition(0, "CiTy", "c1", "City 1", "s1", 50m, 20m, null),
            });

        SanguoMapDefinitionValidator.TryValidate(map, out var errors).Should().BeTrue();
        errors.Should().BeEmpty();
    }

    [Fact]
    public void ShouldFail_WhenTileCountDoesNotMatchTilesLength()
    {
        var map = new SanguoMapDefinition(
            MapId: "map001",
            TileCount: 2,
            Tiles: new[]
            {
                new SanguoTileDefinition(0, SanguoTileDefinition.TileTypeWild, "start", "Start", "s0", 0m, 0m, null),
            });

        SanguoMapDefinitionValidator.TryValidate(map, out var errors).Should().BeFalse();
        errors.Should().Contain(e => e.Contains("Tiles.Count must match TileCount"));
        errors.Should().Contain(e => e.Contains("Missing tile definition for PositionIndex=1"));
    }

    [Fact]
    public void ShouldFail_WhenTileFieldsAreMissingOrInvalid()
    {
        var map = new SanguoMapDefinition(
            MapId: " ",
            TileCount: 1,
            Tiles: new[]
            {
                new SanguoTileDefinition(0, "", "", "", "", -1m, -2m, null),
            });

        SanguoMapDefinitionValidator.TryValidate(map, out var errors).Should().BeFalse();
        errors.Should().Contain(e => e.Contains("MapId must be non-empty"));
        errors.Should().Contain(e => e.Contains("TileType must be non-empty"));
        errors.Should().Contain(e => e.Contains("TileId must be non-empty"));
        errors.Should().Contain(e => e.Contains("Name must be non-empty"));
        errors.Should().Contain(e => e.Contains("StateId must be non-empty"));
        errors.Should().Contain(e => e.Contains("PurchasePrice must be non-negative"));
        errors.Should().Contain(e => e.Contains("TollPrice must be non-negative"));
    }

    [Fact]
    public void ShouldFail_WhenDuplicatePositionIndexExists()
    {
        var map = new SanguoMapDefinition(
            MapId: "map001",
            TileCount: 2,
            Tiles: new[]
            {
                new SanguoTileDefinition(0, SanguoTileDefinition.TileTypeWild, "start", "Start", "s0", 0m, 0m, null),
                new SanguoTileDefinition(0, SanguoTileDefinition.TileTypeCity, "c1", "City 1", "s1", 50m, 20m, null),
            });

        SanguoMapDefinitionValidator.TryValidate(map, out var errors).Should().BeFalse();
        errors.Should().Contain(e => e.Contains("Duplicate PositionIndex"));
    }

    [Fact]
    public void ShouldFail_WhenTilePositionIsOutOfRange()
    {
        var map = new SanguoMapDefinition(
            MapId: "map001",
            TileCount: 1,
            Tiles: new[]
            {
                new SanguoTileDefinition(2, SanguoTileDefinition.TileTypeWild, "start", "Start", "s0", 0m, 0m, null),
            });

        SanguoMapDefinitionValidator.TryValidate(map, out var errors).Should().BeFalse();
        errors.Should().Contain(e => e.Contains("Tile.PositionIndex must be < TileCount"));
        errors.Should().Contain(e => e.Contains("Missing tile definition for PositionIndex=0"));
    }

    [Fact]
    public void ShouldFail_WhenUnsupportedTileTypeProvided()
    {
        var map = new SanguoMapDefinition(
            MapId: "map001",
            TileCount: 1,
            Tiles: new[]
            {
                new SanguoTileDefinition(0, "castle", "x1", "X", "s0", 0m, 0m, null),
            });

        SanguoMapDefinitionValidator.TryValidate(map, out var errors).Should().BeFalse();
        errors.Should().Contain(e => e.Contains("Unsupported TileType"));
    }

    [Fact]
    public void ShouldFail_WhenTilesListContainsNull()
    {
        var tiles = new List<SanguoTileDefinition> { null! };
        var map = new SanguoMapDefinition(MapId: "map001", TileCount: 1, Tiles: tiles);

        SanguoMapDefinitionValidator.TryValidate(map, out var errors).Should().BeFalse();
        errors.Should().Contain(e => e.Contains("Tiles must not contain null entries"));
    }
}
