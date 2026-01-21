using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;

namespace Game.Core.Services.Sanguo;

public static class SanguoCharactersCatalogLoader
{
    public const string CharactersResPath = "res://Data/characters.json";
    public const int MaxPortraitBytes = 1024 * 1024;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 64,
    };

    private static readonly HashSet<string> AllowedPortraitExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".png",
        ".webp",
        ".svg",
    };

    public static bool TryLoadCharactersCatalog(IResourceLoader loader, out SanguoCharactersCatalog catalog, out string error)
    {
        ArgumentNullException.ThrowIfNull(loader);

        catalog = new SanguoCharactersCatalog(SchemaVersion: 0, Version: 0, Characters: Array.Empty<SanguoCharacterDefinition>());
        error = string.Empty;

        var json = loader.LoadText(CharactersResPath);
        if (string.IsNullOrWhiteSpace(json))
        {
            error = "characters_catalog_missing";
            return false;
        }

        try
        {
            catalog = JsonSerializer.Deserialize<SanguoCharactersCatalog>(json, JsonOptions)
                ?? new SanguoCharactersCatalog(SchemaVersion: 0, Version: 0, Characters: Array.Empty<SanguoCharacterDefinition>());
        }
        catch (Exception ex)
        {
            error = $"json_parse_failed:{ex.GetType().Name}";
            return false;
        }

        if (catalog.SchemaVersion <= 0 || catalog.Version <= 0)
        {
            error = "invalid_characters_catalog:bad_versions";
            return false;
        }

        if (catalog.Characters is null || catalog.Characters.Count < 8)
        {
            error = "invalid_characters_catalog:too_few_characters";
            return false;
        }

        var seenIds = new HashSet<string>(StringComparer.Ordinal);
        foreach (var c in catalog.Characters)
        {
            if (string.IsNullOrWhiteSpace(c.CharacterId))
            {
                error = "invalid_characters_catalog:character_id_empty";
                return false;
            }

            if (!seenIds.Add(c.CharacterId))
            {
                error = "invalid_characters_catalog:duplicate_character_id";
                return false;
            }

            if (string.IsNullOrWhiteSpace(c.NameKey) || string.IsNullOrWhiteSpace(c.DescriptionKey))
            {
                error = "invalid_characters_catalog:i18n_keys_empty";
                return false;
            }

            if (c.CombatRating is < 0 or > 100)
            {
                error = "invalid_characters_catalog:combat_rating_out_of_range";
                return false;
            }

            if (string.IsNullOrWhiteSpace(c.PortraitPath))
            {
                error = "invalid_characters_catalog:portrait_path_empty";
                return false;
            }

            if (!IsSafeAssetsResPath(c.PortraitPath))
            {
                error = "invalid_characters_catalog:portrait_path_not_allowed";
                return false;
            }

            var ext = Path.GetExtension(c.PortraitPath);
            if (string.IsNullOrWhiteSpace(ext) || !AllowedPortraitExtensions.Contains(ext))
            {
                error = "invalid_characters_catalog:portrait_extension_not_allowed";
                return false;
            }

            var bytes = loader.LoadBytes(c.PortraitPath);
            if (bytes is null)
            {
                error = "invalid_characters_catalog:portrait_missing";
                return false;
            }

            if (bytes.Length > MaxPortraitBytes)
            {
                error = "invalid_characters_catalog:portrait_too_large";
                return false;
            }

            if (c.EconomyStepDeltas is null)
            {
                error = "invalid_characters_catalog:economy_step_deltas_missing";
                return false;
            }
        }

        var readOnly = Array.AsReadOnly(catalog.Characters.ToArray());
        catalog = new SanguoCharactersCatalog(catalog.SchemaVersion, catalog.Version, readOnly);
        return true;
    }

    private static bool IsSafeAssetsResPath(string path)
    {
        if (!path.StartsWith("res://Assets/", StringComparison.Ordinal))
            return false;

        // Disallow OS-style paths and traversal segments in Godot virtual paths.
        if (path.Contains('\\', StringComparison.Ordinal))
            return false;

        var afterRes = path.Substring("res://".Length);
        if (afterRes.Contains(':', StringComparison.Ordinal))
            return false;

        var parts = afterRes.Split('/', StringSplitOptions.RemoveEmptyEntries);
        return parts.All(p => !string.Equals(p, ".", StringComparison.Ordinal) && !string.Equals(p, "..", StringComparison.Ordinal));
    }
}
