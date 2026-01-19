using System;
using System.Collections.Generic;
using System.IO;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Contract-level validation for <see cref="SanguoMapDefinitionV2"/>.
/// </summary>
/// <remarks>
/// This stays deterministic and unit-testable. Do not access Godot APIs here.
/// Related ADRs: ADR-0019 (security baseline).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t53-map-config.md.
/// </remarks>
public static class SanguoMapDefinitionV2Validator
{
    private static readonly HashSet<string> AllowedTileKinds = new(StringComparer.OrdinalIgnoreCase)
    {
        SanguoMapTileDefinitionV2.TileKindCity,
        SanguoMapTileDefinitionV2.TileKindFacility,
        SanguoMapTileDefinitionV2.TileKindEvent,
        SanguoMapTileDefinitionV2.TileKindEmpty,
    };

    private static readonly HashSet<string> AllowedIconExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".png",
        ".webp",
        ".svg",
    };

    /// <summary>
    /// Validate a <see cref="SanguoMapDefinitionV2"/> instance.
    /// </summary>
    public static bool TryValidate(SanguoMapDefinitionV2? map, out IReadOnlyList<string> errors)
    {
        var list = new List<string>();

        if (map is null)
        {
            list.Add("Map definition is null.");
            errors = list;
            return false;
        }

        if (map.SchemaVersion <= 0)
            list.Add("SchemaVersion must be greater than 0.");

        if (map.Version <= 0)
            list.Add("Version must be greater than 0.");

        if (string.IsNullOrWhiteSpace(map.MapId))
            list.Add("MapId must be non-empty.");

        if (map.Track is null)
        {
            list.Add("Track must be provided.");
        }
        else
        {
            if (map.Track.Length <= 0)
                list.Add("Track.Length must be greater than 0.");
            if (string.IsNullOrWhiteSpace(map.Track.StartTileId))
                list.Add("Track.StartTileId must be non-empty.");
        }

        if (map.Tiles is null)
        {
            list.Add("Tiles must be provided.");
            errors = list;
            return false;
        }

        if (map.Track is not null && map.Track.Length > 0 && map.Tiles.Count != map.Track.Length)
        {
            list.Add($"Tiles.Count must match Track.Length (trackLength={map.Track.Length}, tilesCount={map.Tiles.Count}).");
        }

        var seenTileIds = new HashSet<string>(StringComparer.Ordinal);
        var firstTileId = map.Tiles.Count > 0 ? map.Tiles[0]?.TileId : null;
        foreach (var tile in map.Tiles)
        {
            if (tile is null)
            {
                list.Add("Tiles must not contain null entries.");
                continue;
            }

            if (string.IsNullOrWhiteSpace(tile.TileId))
                list.Add("TileId must be non-empty.");
            else if (!seenTileIds.Add(tile.TileId))
                list.Add($"Duplicate TileId detected: {tile.TileId}.");

            if (string.IsNullOrWhiteSpace(tile.TileKind))
                list.Add($"TileKind must be non-empty (tileId={tile.TileId}).");
            else if (!AllowedTileKinds.Contains(tile.TileKind))
                list.Add($"Unsupported TileKind '{tile.TileKind}' (tileId={tile.TileId}).");

            if (string.IsNullOrWhiteSpace(tile.NameKey))
                list.Add($"NameKey must be non-empty (tileId={tile.TileId}).");

            if (tile.Layout is null)
            {
                list.Add($"Layout must be provided (tileId={tile.TileId}).");
            }
            else
            {
                if (tile.Layout.X < 0 || tile.Layout.X > 1)
                    list.Add($"Layout.X must be in [0,1] (tileId={tile.TileId}, x={tile.Layout.X}).");
                if (tile.Layout.Y < 0 || tile.Layout.Y > 1)
                    list.Add($"Layout.Y must be in [0,1] (tileId={tile.TileId}, y={tile.Layout.Y}).");
            }

            if (tile.Actions is null)
            {
                list.Add($"Actions must be provided (tileId={tile.TileId}).");
            }
            else
            {
                var seenActionIds = new HashSet<string>(StringComparer.Ordinal);
                foreach (var action in tile.Actions)
                {
                    if (action is null)
                    {
                        list.Add($"Actions must not contain null entries (tileId={tile.TileId}).");
                        continue;
                    }

                    if (string.IsNullOrWhiteSpace(action.ActionId))
                        list.Add($"ActionId must be non-empty (tileId={tile.TileId}).");
                    else if (!seenActionIds.Add(action.ActionId))
                        list.Add($"Duplicate ActionId detected (tileId={tile.TileId}, actionId={action.ActionId}).");

                    if (string.IsNullOrWhiteSpace(action.IconResPath))
                    {
                        list.Add($"IconResPath must be non-empty (tileId={tile.TileId}, actionId={action.ActionId}).");
                    }
                    else
                    {
                        if (!action.IconResPath.StartsWith("res://Assets/", StringComparison.Ordinal))
                            list.Add($"IconResPath must be under res://Assets/ (tileId={tile.TileId}, actionId={action.ActionId}).");
                        var ext = Path.GetExtension(action.IconResPath);
                        if (string.IsNullOrWhiteSpace(ext) || !AllowedIconExtensions.Contains(ext))
                            list.Add($"IconResPath has unsupported extension (tileId={tile.TileId}, actionId={action.ActionId}).");
                    }
                }

                var kind = (tile.TileKind ?? string.Empty).Trim().ToLowerInvariant();
                if (kind != SanguoMapTileDefinitionV2.TileKindEmpty && tile.Actions.Count == 0)
                {
                    list.Add($"Non-empty tiles must define at least one action (tileId={tile.TileId}, kind={tile.TileKind}).");
                }
            }

            var normalizedKind = (tile.TileKind ?? string.Empty).Trim().ToLowerInvariant();
            if (normalizedKind == SanguoMapTileDefinitionV2.TileKindCity)
            {
                if (string.IsNullOrWhiteSpace(tile.RegionId))
                    list.Add($"RegionId must be provided for city tiles (tileId={tile.TileId}).");
                if (tile.City is null)
                {
                    list.Add($"City payload must be provided for city tiles (tileId={tile.TileId}).");
                }
                else
                {
                    if (tile.City.BasePrice < 0)
                        list.Add($"City.BasePrice must be non-negative (tileId={tile.TileId}).");
                    if (tile.City.BaseToll < 0)
                        list.Add($"City.BaseToll must be non-negative (tileId={tile.TileId}).");
                    if (tile.City.AllowedBuildingIds is null)
                        list.Add($"City.AllowedBuildingIds must be provided (tileId={tile.TileId}).");
                }
            }
            else if (normalizedKind == SanguoMapTileDefinitionV2.TileKindFacility)
            {
                if (string.IsNullOrWhiteSpace(tile.FacilityId))
                    list.Add($"FacilityId must be provided for facility tiles (tileId={tile.TileId}).");
            }
            else if (normalizedKind == SanguoMapTileDefinitionV2.TileKindEvent)
            {
                if (string.IsNullOrWhiteSpace(tile.EventPoolId))
                    list.Add($"EventPoolId must be provided for event tiles (tileId={tile.TileId}).");
            }
        }

        if (map.Track is not null)
        {
            if (!string.IsNullOrWhiteSpace(map.Track.StartTileId) && !seenTileIds.Contains(map.Track.StartTileId))
            {
                list.Add($"Track.StartTileId must exist in Tiles (startTileId={map.Track.StartTileId}).");
            }

            // Current runtime uses legacy PositionIndex derived from Tiles[] order.
            // Freeze the contract to avoid implicit mismatches until the full V2 runtime is adopted.
            if (!string.IsNullOrWhiteSpace(firstTileId) && !string.IsNullOrWhiteSpace(map.Track.StartTileId)
                && !string.Equals(firstTileId, map.Track.StartTileId, StringComparison.Ordinal))
            {
                list.Add($"Track.StartTileId must match the first tile's TileId (firstTileId={firstTileId}, startTileId={map.Track.StartTileId}).");
            }
        }

        errors = list;
        return list.Count == 0;
    }
}
