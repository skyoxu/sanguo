using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using Game.Godot.Scripts.Security;
using System;
using System.Linq;
using System.Text.Json;

namespace Game.Godot.Scripts.Sanguo;

internal static class SanguoMapConfigLoader
{
    internal const string MapsIndexPath = "res://Data/maps/_index.json";
    internal const string MapsDirPrefix = "res://Data/maps/";
    internal const string MapsFileSuffix = ".json";

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 64,
    };

    internal static bool TryLoadMap(
        IResourceLoader loader,
        string correlationId,
        out SanguoMapDefinition map,
        out string sourcePath,
        out string error
    )
    {
        ArgumentNullException.ThrowIfNull(loader);

        map = new SanguoMapDefinition(MapId: "invalid", TileCount: 0, Tiles: Array.Empty<SanguoTileDefinition>());
        sourcePath = MapsIndexPath;
        error = string.Empty;

        if (!TryLoadMapsCatalog(loader, out var catalog, out var catalogError))
        {
            SecurityAuditWriter.TryAppendSecurityAudit(
                action: "SANGUO_MAP_CATALOG_LOAD_FAILED",
                reason: "maps_index_invalid",
                target: $"path={MapsIndexPath} error={catalogError}",
                caller: "SanguoMapConfigLoader.TryLoadMap",
                eventType: "runtime.map.config.load.failed",
                eventSource: nameof(SanguoMapConfigLoader),
                eventId: correlationId);
            error = catalogError;
            return false;
        }

        SecurityAuditWriter.TryAppendSecurityAudit(
            action: "SANGUO_MAP_CATALOG_LOADED",
            reason: "maps_index",
            target: $"path={MapsIndexPath}",
            caller: "SanguoMapConfigLoader.TryLoadMap",
            eventType: "runtime.map.catalog.loaded",
            eventSource: nameof(SanguoMapConfigLoader),
            eventId: correlationId);

        if (catalog.Maps is null || catalog.Maps.Count == 0)
        {
            SecurityAuditWriter.TryAppendSecurityAudit(
                action: "SANGUO_MAP_CATALOG_LOAD_FAILED",
                reason: "maps_index_empty",
                target: $"path={MapsIndexPath}",
                caller: "SanguoMapConfigLoader.TryLoadMap",
                eventType: "runtime.map.catalog.load.failed",
                eventSource: nameof(SanguoMapConfigLoader),
                eventId: correlationId);
            error = "maps_index_empty";
            return false;
        }

        var defaultEntry = catalog.Maps[0];
        if (defaultEntry is null || string.IsNullOrWhiteSpace(defaultEntry.MapId))
        {
            SecurityAuditWriter.TryAppendSecurityAudit(
                action: "SANGUO_MAP_CATALOG_LOAD_FAILED",
                reason: "maps_index_entry_invalid",
                target: $"path={MapsIndexPath}",
                caller: "SanguoMapConfigLoader.TryLoadMap",
                eventType: "runtime.map.catalog.load.failed",
                eventSource: nameof(SanguoMapConfigLoader),
                eventId: correlationId);
            error = "maps_index_entry_invalid";
            return false;
        }

        var mapId = defaultEntry.MapId;
        if (!TryLoadMapV2FromMapId(loader, mapId, out var mapV2, out var mapV2Path, out var mapV2Error))
        {
            sourcePath = mapV2Path;
            SecurityAuditWriter.TryAppendSecurityAudit(
                action: "SANGUO_MAP_CONFIG_LOAD_FAILED",
                reason: "map_v2_load_failed",
                target: $"mapId={mapId} path={mapV2Path} error={mapV2Error}",
                caller: "SanguoMapConfigLoader.TryLoadMap",
                eventType: "runtime.map.config.load.failed",
                eventSource: nameof(SanguoMapConfigLoader),
                eventId: correlationId);
            error = mapV2Error;
            return false;
        }

        var legacy = ConvertV2ToLegacy(mapV2);
        if (!SanguoMapDefinitionValidator.TryValidate(legacy, out var legacyErrors))
        {
            sourcePath = mapV2Path;
            error = "invalid_legacy_map:" + string.Join(" | ", legacyErrors);
            if (error.Length > 512)
            {
                error = error.Substring(0, 512);
            }

            SecurityAuditWriter.TryAppendSecurityAudit(
                action: "SANGUO_MAP_CONFIG_LOAD_FAILED",
                reason: "legacy_contract_validation_failed",
                target: $"mapId={mapId} path={mapV2Path} error={error}",
                caller: "SanguoMapConfigLoader.TryLoadMap",
                eventType: "runtime.map.config.load.failed",
                eventSource: nameof(SanguoMapConfigLoader),
                eventId: correlationId);
            return false;
        }

        map = legacy;
        sourcePath = mapV2Path;
        SecurityAuditWriter.TryAppendSecurityAudit(
            action: "SANGUO_MAP_CONFIG_LOADED",
            reason: "maps_index_default",
            target: $"mapId={mapId} path={mapV2Path}",
            caller: "SanguoMapConfigLoader.TryLoadMap",
            eventType: "runtime.map.config.loaded",
            eventSource: nameof(SanguoMapConfigLoader),
            eventId: correlationId);
        return true;
    }

    private static bool TryLoadMapsCatalog(
        IResourceLoader loader,
        out SanguoMapsCatalog catalog,
        out string error)
    {
        catalog = new SanguoMapsCatalog(SchemaVersion: 0, Version: 0, Maps: Array.Empty<SanguoMapCatalogEntry>());
        error = string.Empty;

        var json = loader.LoadText(MapsIndexPath);
        if (string.IsNullOrWhiteSpace(json))
        {
            error = "maps_index_missing";
            return false;
        }

        try
        {
            catalog = JsonSerializer.Deserialize<SanguoMapsCatalog>(json, JsonOptions)
                ?? new SanguoMapsCatalog(SchemaVersion: 0, Version: 0, Maps: Array.Empty<SanguoMapCatalogEntry>());
        }
        catch (Exception ex)
        {
            error = $"json_parse_failed:{ex.GetType().Name}";
            return false;
        }

        if (catalog.SchemaVersion <= 0 || catalog.Version <= 0)
        {
            error = "invalid_maps_index:bad_versions";
            return false;
        }

        return true;
    }

    private static bool TryLoadMapV2FromMapId(
        IResourceLoader loader,
        string mapId,
        out SanguoMapDefinitionV2 map,
        out string sourcePath,
        out string error)
    {
        map = new SanguoMapDefinitionV2(
            SchemaVersion: 0,
            Version: 0,
            MapId: "invalid",
            Track: new SanguoMapTrackDefinitionV2(Length: 0, StartTileId: "invalid"),
            Tiles: Array.Empty<SanguoMapTileDefinitionV2>());
        error = string.Empty;

        sourcePath = $"{MapsDirPrefix}{mapId}{MapsFileSuffix}";
        var json = loader.LoadText(sourcePath);
        if (string.IsNullOrWhiteSpace(json))
        {
            error = "map_missing";
            return false;
        }

        SanguoMapDefinitionV2? parsed;
        try
        {
            parsed = JsonSerializer.Deserialize<SanguoMapDefinitionV2>(json, JsonOptions);
        }
        catch (Exception ex)
        {
            error = $"json_parse_failed:{ex.GetType().Name}";
            return false;
        }

        if (!SanguoMapDefinitionV2Validator.TryValidate(parsed, out var errors))
        {
            error = "invalid_map_v2:" + string.Join(" | ", errors);
            if (error.Length > 512)
            {
                error = error.Substring(0, 512);
            }
            return false;
        }

        map = parsed!;
        return true;
    }

    private static SanguoMapDefinition ConvertV2ToLegacy(SanguoMapDefinitionV2 map)
    {
        var tiles = map.Tiles
            .Select((t, i) => new SanguoTileDefinition(
                PositionIndex: i,
                TileType: MapTileKindToLegacyType(t.TileKind),
                TileId: t.TileId,
                Name: t.NameKey,
                StateId: MapTileStateId(t),
                PurchasePrice: (decimal)(t.City?.BasePrice ?? 0),
                TollPrice: (decimal)(t.City?.BaseToll ?? 0),
                Actions: t.Actions?.Select(a => a.ActionId).ToArray()))
            .ToArray();

        return new SanguoMapDefinition(
            MapId: map.MapId,
            TileCount: map.Track.Length,
            Tiles: tiles);
    }

    private static string MapTileKindToLegacyType(string tileKind)
    {
        var normalized = (tileKind ?? string.Empty).Trim().ToLowerInvariant();
        return normalized switch
        {
            SanguoMapTileDefinitionV2.TileKindCity => SanguoTileDefinition.TileTypeCity,
            SanguoMapTileDefinitionV2.TileKindEvent => SanguoTileDefinition.TileTypeEvent,
            SanguoMapTileDefinitionV2.TileKindEmpty => SanguoTileDefinition.TileTypeEmpty,
            SanguoMapTileDefinitionV2.TileKindFacility => SanguoTileDefinition.TileTypePass,
            _ => SanguoTileDefinition.TileTypeEmpty,
        };
    }

    private static string MapTileStateId(SanguoMapTileDefinitionV2 tile)
    {
        var kind = (tile.TileKind ?? string.Empty).Trim().ToLowerInvariant();
        if (kind == SanguoMapTileDefinitionV2.TileKindCity)
        {
            return tile.RegionId ?? "region:unknown";
        }

        if (kind == SanguoMapTileDefinitionV2.TileKindFacility)
        {
            return tile.FacilityId ?? "facility:unknown";
        }

        if (kind == SanguoMapTileDefinitionV2.TileKindEvent)
        {
            return tile.EventPoolId ?? "event_pool:unknown";
        }

        return string.IsNullOrWhiteSpace(kind) ? "unknown" : kind;
    }
}
