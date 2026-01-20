using System;
using System.Text.Json;
using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;

namespace Game.Core.Services.Sanguo;

public static class SanguoMapsCatalogLoader
{
    public const string MapsIndexResPath = "res://Data/maps/_index.json";

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 64,
    };

    public static bool TryLoadMapsCatalog(IResourceLoader loader, out SanguoMapsCatalog catalog, out string error)
    {
        ArgumentNullException.ThrowIfNull(loader);

        catalog = new SanguoMapsCatalog(SchemaVersion: 0, Version: 0, Maps: Array.Empty<SanguoMapCatalogEntry>());
        error = string.Empty;

        var json = loader.LoadText(MapsIndexResPath);
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
}

