using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

public static class SanguoMapDefinitionValidator
{
    public static bool TryValidate(SanguoMapDefinition? map, out IReadOnlyList<string> errors)
    {
        var list = new List<string>();

        if (map is null)
        {
            list.Add("Map definition is null.");
            errors = list;
            return false;
        }

        if (string.IsNullOrWhiteSpace(map.MapId))
            list.Add("MapId must be non-empty.");

        if (map.TileCount <= 0)
            list.Add("TileCount must be greater than 0.");

        if (map.Tiles is null)
        {
            list.Add("Tiles must be provided.");
            errors = list;
            return false;
        }

        if (map.TileCount > 0 && map.Tiles.Count != map.TileCount)
            list.Add($"Tiles.Count must match TileCount (TileCount={map.TileCount}, Tiles.Count={map.Tiles.Count}).");

        var seenPositions = new HashSet<int>();
        var seenTileIds = new HashSet<string>(System.StringComparer.Ordinal);

        foreach (var tile in map.Tiles)
        {
            if (tile is null)
            {
                list.Add("Tiles must not contain null entries.");
                continue;
            }

            if (tile.PositionIndex < 0)
                list.Add($"Tile.PositionIndex must be non-negative (tileId={tile.TileId}).");

            if (map.TileCount > 0 && tile.PositionIndex >= map.TileCount)
                list.Add($"Tile.PositionIndex must be < TileCount (tileId={tile.TileId}, pos={tile.PositionIndex}, tileCount={map.TileCount}).");

            if (!seenPositions.Add(tile.PositionIndex))
                list.Add($"Duplicate PositionIndex detected: {tile.PositionIndex}.");

            if (string.IsNullOrWhiteSpace(tile.TileType))
                list.Add($"TileType must be non-empty (pos={tile.PositionIndex}).");

            var normalizedType = (tile.TileType ?? "").Trim().ToLowerInvariant();
            if (normalizedType != SanguoTileDefinition.TileTypeCity
                && normalizedType != SanguoTileDefinition.TileTypePass
                && normalizedType != SanguoTileDefinition.TileTypeEvent
                && normalizedType != SanguoTileDefinition.TileTypeEmpty
                && normalizedType != SanguoTileDefinition.TileTypeWild)
            {
                list.Add($"Unsupported TileType '{tile.TileType}' (pos={tile.PositionIndex}).");
            }

            if (string.IsNullOrWhiteSpace(tile.TileId))
                list.Add($"TileId must be non-empty (pos={tile.PositionIndex}).");

            if (!string.IsNullOrWhiteSpace(tile.TileId) && !seenTileIds.Add(tile.TileId))
                list.Add($"Duplicate TileId detected: {tile.TileId}.");

            if (string.IsNullOrWhiteSpace(tile.Name))
                list.Add($"Name must be non-empty (tileId={tile.TileId}, pos={tile.PositionIndex}).");

            if (string.IsNullOrWhiteSpace(tile.StateId))
                list.Add($"StateId must be non-empty (tileId={tile.TileId}, pos={tile.PositionIndex}).");

            if (tile.PurchasePrice < 0)
                list.Add($"PurchasePrice must be non-negative (tileId={tile.TileId}, pos={tile.PositionIndex}).");

            if (tile.TollPrice < 0)
                list.Add($"TollPrice must be non-negative (tileId={tile.TileId}, pos={tile.PositionIndex}).");
        }

        if (map.TileCount > 0)
        {
            for (var i = 0; i < map.TileCount; i++)
            {
                if (!seenPositions.Contains(i))
                    list.Add($"Missing tile definition for PositionIndex={i}.");
            }
        }

        errors = list;
        return list.Count == 0;
    }
}

