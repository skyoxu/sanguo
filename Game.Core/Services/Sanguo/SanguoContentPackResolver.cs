using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using Game.Core.Ports;

namespace Game.Core.Services.Sanguo;

public sealed record SanguoContentPackPaths(
    string PackId,
    int PackVersion,
    string MapsIndexPath,
    string CharactersPath,
    string RandomEventsPath,
    string ActionCardsPath,
    string BuildingsPath,
    string RelicsPath,
    string RegionsPath,
    string FacilitiesPath,
    string I18nZhPath,
    string I18nEnPath
);

public static class SanguoContentPackResolver
{
    public const string PacksIndexResPath = "res://Data/packs/_index.json";

    private static readonly JsonDocumentOptions DocOptions = new()
    {
        CommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 64,
    };

    public static bool TryResolveDefaultPack(IResourceLoader loader, out SanguoContentPackPaths pack, out string error)
    {
        ArgumentNullException.ThrowIfNull(loader);

        pack = new SanguoContentPackPaths(
            PackId: string.Empty,
            PackVersion: 0,
            MapsIndexPath: string.Empty,
            CharactersPath: string.Empty,
            RandomEventsPath: string.Empty,
            ActionCardsPath: string.Empty,
            BuildingsPath: string.Empty,
            RelicsPath: string.Empty,
            RegionsPath: string.Empty,
            FacilitiesPath: string.Empty,
            I18nZhPath: string.Empty,
            I18nEnPath: string.Empty);
        error = string.Empty;

        var json = loader.LoadText(PacksIndexResPath);
        if (string.IsNullOrWhiteSpace(json))
        {
            error = "content_pack_index_missing";
            return false;
        }

        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(json, DocOptions);
        }
        catch (Exception ex)
        {
            error = $"content_pack_index_json_invalid:{ex.GetType().Name}";
            return false;
        }

        using (doc)
        {
            if (doc.RootElement.ValueKind != JsonValueKind.Object)
            {
                error = "content_pack_index_root_not_object";
                return false;
            }

            if (!doc.RootElement.TryGetProperty("packs", out var packsEl) || packsEl.ValueKind != JsonValueKind.Array)
            {
                error = "content_pack_index_missing_packs";
                return false;
            }

            var candidates = new List<(string PackId, string Path, int Order)>();
            foreach (var entry in packsEl.EnumerateArray())
            {
                if (entry.ValueKind != JsonValueKind.Object)
                {
                    error = "content_pack_index_entry_not_object";
                    return false;
                }

                if (!TryGetStringRequired(entry, "packId", out var packId)
                    || !TryGetStringRequired(entry, "path", out var packPath)
                    || !TryGetBooleanRequired(entry, "enabled", out var enabled)
                    || !TryGetInt32Required(entry, "order", out var order))
                {
                    error = "content_pack_index_entry_invalid";
                    return false;
                }

                if (enabled)
                {
                    candidates.Add((packId, packPath, order));
                }
            }

            if (candidates.Count == 0)
            {
                error = "content_pack_index_no_enabled";
                return false;
            }

            var selected = candidates.OrderBy(x => x.Order).ThenBy(x => x.PackId, StringComparer.Ordinal).First();
            if (!TryLoadPack(loader, selected.PackId, selected.Path, out pack, out error))
            {
                return false;
            }

            return true;
        }
    }

    private static bool TryLoadPack(
        IResourceLoader loader,
        string packId,
        string packPath,
        out SanguoContentPackPaths pack,
        out string error)
    {
        pack = new SanguoContentPackPaths(
            PackId: string.Empty,
            PackVersion: 0,
            MapsIndexPath: string.Empty,
            CharactersPath: string.Empty,
            RandomEventsPath: string.Empty,
            ActionCardsPath: string.Empty,
            BuildingsPath: string.Empty,
            RelicsPath: string.Empty,
            RegionsPath: string.Empty,
            FacilitiesPath: string.Empty,
            I18nZhPath: string.Empty,
            I18nEnPath: string.Empty);
        error = string.Empty;

        var json = loader.LoadText(packPath);
        if (string.IsNullOrWhiteSpace(json))
        {
            error = "content_pack_missing";
            return false;
        }

        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(json, DocOptions);
        }
        catch (Exception ex)
        {
            error = $"content_pack_json_invalid:{ex.GetType().Name}";
            return false;
        }

        using (doc)
        {
            if (doc.RootElement.ValueKind != JsonValueKind.Object)
            {
                error = "content_pack_root_not_object";
                return false;
            }

            if (!TryGetStringRequired(doc.RootElement, "packId", out var packIdFromDoc) || !string.Equals(packIdFromDoc, packId, StringComparison.Ordinal))
            {
                error = "content_pack_id_mismatch";
                return false;
            }

            if (!TryGetInt32Required(doc.RootElement, "schemaVersion", out var schemaVersion) || schemaVersion <= 0)
            {
                error = "content_pack_bad_schema";
                return false;
            }

            if (!TryGetInt32Required(doc.RootElement, "version", out var version) || version <= 0)
            {
                error = "content_pack_bad_version";
                return false;
            }

            if (!doc.RootElement.TryGetProperty("content", out var contentEl) || contentEl.ValueKind != JsonValueKind.Object)
            {
                error = "content_pack_missing_content";
                return false;
            }

            if (!TryGetContentPath(contentEl, "maps", out var mapsIndexPath)
                || !TryGetContentPath(contentEl, "characters", out var charactersPath)
                || !TryGetContentPath(contentEl, "events", out var randomEventsPath)
                || !TryGetContentPath(contentEl, "cards", out var actionCardsPath)
                || !TryGetContentPath(contentEl, "buildings", out var buildingsPath)
                || !TryGetContentPath(contentEl, "relics", out var relicsPath)
                || !TryGetContentPath(contentEl, "regions", out var regionsPath)
                || !TryGetContentPath(contentEl, "facilities", out var facilitiesPath))
            {
                error = "content_pack_missing_content_paths";
                return false;
            }

            if (!contentEl.TryGetProperty("i18n", out var i18nEl) || i18nEl.ValueKind != JsonValueKind.Object)
            {
                error = "content_pack_missing_i18n";
                return false;
            }

            if (!TryGetStringRequired(i18nEl, "zh-CN", out var i18nZhPath)
                || !TryGetStringRequired(i18nEl, "en-US", out var i18nEnPath))
            {
                error = "content_pack_missing_i18n_paths";
                return false;
            }

            pack = new SanguoContentPackPaths(
                PackId: packId,
                PackVersion: version,
                MapsIndexPath: mapsIndexPath,
                CharactersPath: charactersPath,
                RandomEventsPath: randomEventsPath,
                ActionCardsPath: actionCardsPath,
                BuildingsPath: buildingsPath,
                RelicsPath: relicsPath,
                RegionsPath: regionsPath,
                FacilitiesPath: facilitiesPath,
                I18nZhPath: i18nZhPath,
                I18nEnPath: i18nEnPath);
            return true;
        }
    }

    private static bool TryGetContentPath(JsonElement content, string name, out string path)
    {
        path = string.Empty;
        if (!content.TryGetProperty(name, out var el) || el.ValueKind != JsonValueKind.Array)
        {
            return false;
        }

        if (el.GetArrayLength() == 0)
        {
            return false;
        }

        var first = el.EnumerateArray().First();
        if (first.ValueKind != JsonValueKind.String)
        {
            return false;
        }

        path = (first.GetString() ?? string.Empty).Trim();
        return !string.IsNullOrWhiteSpace(path);
    }

    private static bool TryGetStringRequired(JsonElement obj, string name, out string value)
    {
        value = string.Empty;
        if (!obj.TryGetProperty(name, out var el) || el.ValueKind != JsonValueKind.String)
        {
            return false;
        }
        value = (el.GetString() ?? string.Empty).Trim();
        return !string.IsNullOrWhiteSpace(value);
    }

    private static bool TryGetBooleanRequired(JsonElement obj, string name, out bool value)
    {
        value = false;
        if (!obj.TryGetProperty(name, out var el) || (el.ValueKind != JsonValueKind.True && el.ValueKind != JsonValueKind.False))
        {
            return false;
        }
        value = el.GetBoolean();
        return true;
    }

    private static bool TryGetInt32Required(JsonElement obj, string name, out int value)
    {
        value = 0;
        if (!obj.TryGetProperty(name, out var el) || el.ValueKind != JsonValueKind.Number)
        {
            return false;
        }
        return el.TryGetInt32(out value);
    }
}
