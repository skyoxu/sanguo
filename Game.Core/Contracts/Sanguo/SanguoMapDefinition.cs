namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Runtime map definition for the Sanguo playable loop.
/// This contract is engine-agnostic and can be validated via pure unit tests.
/// </summary>
public sealed record SanguoMapDefinition(
    string MapId,
    int TileCount,
    IReadOnlyList<SanguoTileDefinition> Tiles
);

/// <summary>
/// Tile definition for a board position.
/// </summary>
public sealed record SanguoTileDefinition(
    int PositionIndex,
    string TileType,
    string TileId,
    string Name,
    string StateId,
    decimal PurchasePrice,
    decimal TollPrice,
    IReadOnlyList<string>? Actions
)
{
    public const string TileTypeCity = "city";
    public const string TileTypePass = "pass";
    public const string TileTypeWild = "wild";
}

