using System;
using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: SanguoMapDefinitionV2
/// Description: Map definition loaded from JSON at runtime (tracks + layout + per-tile kind payload).
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates), ADR-0019 (security baseline).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t53-map-config.md.
/// Data source (SSoT): res://Data/maps/&lt;map_id&gt;.json.
/// </remarks>
public sealed record SanguoMapDefinitionV2(
    int SchemaVersion,
    int Version,
    string MapId,
    SanguoMapTrackDefinitionV2 Track,
    IReadOnlyList<SanguoMapTileDefinitionV2> Tiles
);

/// <summary>
/// DTO: SanguoMapTrackDefinitionV2
/// Description: Track settings. Track.Length is authoritative for gameplay loops.
/// </summary>
public sealed record SanguoMapTrackDefinitionV2(
    int Length,
    string StartTileId
);

/// <summary>
/// DTO: SanguoMapTileDefinitionV2
/// Description: Per-tile definition (kind + layout + actions and kind-specific fields).
/// </summary>
/// <remarks>
/// TileKind is currently restricted to: city | facility | event | empty.
/// </remarks>
public sealed record SanguoMapTileDefinitionV2(
    string TileId,
    string TileKind,
    string NameKey,
    SanguoMapTileLayoutV2 Layout,
    IReadOnlyList<SanguoMapTileActionV2> Actions,
    string? RegionId = null,
    string? FacilityId = null,
    string? EventPoolId = null,
    SanguoMapCityTileV2? City = null
)
{
    public const string TileKindCity = "city";
    public const string TileKindFacility = "facility";
    public const string TileKindEvent = "event";
    public const string TileKindEmpty = "empty";
}

/// <summary>
/// DTO: SanguoMapTileLayoutV2
/// Description: Normalized layout coordinates in [0,1] with origin at top-left.
/// </summary>
public sealed record SanguoMapTileLayoutV2(
    double X,
    double Y
);

/// <summary>
/// DTO: SanguoMapTileActionV2
/// Description: Action reference available at a tile.
/// </summary>
public sealed record SanguoMapTileActionV2(
    string ActionId,
    string IconResPath
);

/// <summary>
/// DTO: SanguoMapCityTileV2
/// Description: City-specific payload for a city tile.
/// </summary>
public sealed record SanguoMapCityTileV2(
    int BasePrice,
    int BaseToll,
    IReadOnlyList<string> AllowedBuildingIds
);

