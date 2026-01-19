namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Runtime map definition for the Sanguo playable loop.
/// This contract is engine-agnostic and can be validated via pure unit tests.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0019 (security baseline), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t53-map-config.md.
/// </remarks>
public sealed record SanguoMapDefinition(
    string MapId,
    int TileCount,
    IReadOnlyList<SanguoTileDefinition> Tiles
);

/// <summary>
/// Tile definition for a board position.
/// </summary>
/// <remarks>
/// This is a low-level map contract used by both Core and Godot adapters. Keep it stable and Godot-free.
/// If a new tile model is introduced (e.g., facility_kind / region_id), prefer a new DTO and a validated migration.
/// </remarks>
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
    public const string TileTypeEvent = "event";
    public const string TileTypeEmpty = "empty";
    public const string TileTypeWild = "wild";
}

