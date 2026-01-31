using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.Json;

namespace Game.Core.Services.Sanguo;

public static class SanguoRegionsCatalogLoader
{
    public const string RegionsResPath = "res://Data/regions.json";

    private static readonly JsonDocumentOptions DocOptions = new()
    {
        CommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 64,
    };

    public static SanguoRegionsCatalog ParseAndValidate(string json)
    {
        if (string.IsNullOrWhiteSpace(json))
            throw new InvalidOperationException("regions_catalog_missing");

        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(json, DocOptions);
        }
        catch (Exception ex)
        {
            throw new InvalidOperationException($"regions_catalog_json_parse_failed:{ex.GetType().Name}", ex);
        }

        using (doc)
        {
            if (doc.RootElement.ValueKind != JsonValueKind.Object)
                throw new InvalidOperationException("invalid_regions_catalog:root_not_object");

            if (!TryGetInt32RequiredFlexible(doc.RootElement, "schemaVersion", out var schemaVersion)
                || !TryGetInt32RequiredFlexible(doc.RootElement, "version", out var version))
            {
                throw new InvalidOperationException("invalid_regions_catalog:bad_versions");
            }

            if (schemaVersion <= 0 || version <= 0)
                throw new InvalidOperationException("invalid_regions_catalog:bad_versions");

            if (!doc.RootElement.TryGetProperty("regions", out var regionsEl) || regionsEl.ValueKind != JsonValueKind.Array)
                throw new InvalidOperationException("invalid_regions_catalog:missing_regions");

            var seen = new HashSet<string>(StringComparer.Ordinal);
            var regions = new List<SanguoRegionDefinition>();

            foreach (var regionEl in regionsEl.EnumerateArray())
            {
                if (regionEl.ValueKind != JsonValueKind.Object)
                    throw new InvalidOperationException("invalid_regions_catalog:region_not_object");

                if (!TryGetStringRequired(regionEl, "regionId", out var regionId))
                    throw new InvalidOperationException("invalid_regions_catalog:missing_region_id");

                if (!seen.Add(regionId))
                    throw new InvalidOperationException("invalid_regions_catalog:duplicate_region_id");

                if (!TryGetStringRequired(regionEl, "nameKey", out var nameKey))
                    throw new InvalidOperationException("invalid_regions_catalog:missing_name_key");

                if (!TryGetStringRequired(regionEl, "descriptionKey", out var descriptionKey))
                    throw new InvalidOperationException("invalid_regions_catalog:missing_description_key");

                if (!TryGetStringRequired(regionEl, "effectKind", out var effectKind))
                    throw new InvalidOperationException("invalid_regions_catalog:missing_effect_kind");

                var effectParams = new Dictionary<string, string>(StringComparer.Ordinal);
                if (regionEl.TryGetProperty("effectParams", out var effectParamsEl))
                {
                    if (effectParamsEl.ValueKind != JsonValueKind.Object)
                        throw new InvalidOperationException("invalid_regions_catalog:effect_params_not_object");

                    foreach (var prop in effectParamsEl.EnumerateObject())
                    {
                        if (prop.Value.ValueKind != JsonValueKind.String)
                            throw new InvalidOperationException("invalid_regions_catalog:effect_params_not_string");

                        effectParams[prop.Name] = prop.Value.GetString() ?? string.Empty;
                    }
                }

                if (!regionEl.TryGetProperty("economyStepDeltas", out var deltasEl) || deltasEl.ValueKind != JsonValueKind.Object)
                    throw new InvalidOperationException("invalid_regions_catalog:missing_economy_step_deltas");

                if (!TryGetInt32RequiredFlexible(deltasEl, "buyPrice", out var buyPrice)
                    || !TryGetInt32RequiredFlexible(deltasEl, "toll", out var toll)
                    || !TryGetInt32RequiredFlexible(deltasEl, "incomeSettlement", out var incomeSettlement)
                    || !TryGetInt32RequiredFlexible(deltasEl, "buildCost", out var buildCost)
                    || !TryGetInt32RequiredFlexible(deltasEl, "upgradeCost", out var upgradeCost))
                {
                    throw new InvalidOperationException("invalid_regions_catalog:bad_economy_step_deltas");
                }

                var deltas = new SanguoEconomyStepDeltas(
                    BuyPrice: buyPrice,
                    Toll: toll,
                    IncomeSettlement: incomeSettlement,
                    BuildCost: buildCost,
                    UpgradeCost: upgradeCost);

                regions.Add(new SanguoRegionDefinition(
                    RegionId: regionId,
                    NameKey: nameKey,
                    DescriptionKey: descriptionKey,
                    EffectKind: effectKind,
                    EffectParams: effectParams,
                    EconomyStepDeltas: deltas));
            }

            var sorted = Array.AsReadOnly(regions.OrderBy(r => r.RegionId, StringComparer.Ordinal).ToArray());
            return new SanguoRegionsCatalog(schemaVersion, version, sorted);
        }
    }

    public static bool TryLoadRegionsCatalog(IResourceLoader loader, out SanguoRegionsCatalog catalog, out string error)
        => TryLoadRegionsCatalog(loader, pack: null, out catalog, out error);

    public static bool TryLoadRegionsCatalog(IResourceLoader loader, SanguoContentPackPaths? pack, out SanguoRegionsCatalog catalog, out string error)
    {
        ArgumentNullException.ThrowIfNull(loader);

        catalog = new SanguoRegionsCatalog(SchemaVersion: 0, Version: 0, Regions: Array.Empty<SanguoRegionDefinition>());
        error = string.Empty;

        var resPath = pack?.RegionsPath ?? RegionsResPath;
        var json = loader.LoadText(resPath) ?? string.Empty;
        try
        {
            catalog = ParseAndValidate(json);
            return true;
        }
        catch (InvalidOperationException ex)
        {
            error = ex.Message;
            return false;
        }
    }

    private static bool TryGetInt32RequiredFlexible(JsonElement obj, string name, out int value)
    {
        value = 0;
        if (!obj.TryGetProperty(name, out var el))
            return false;

        if (el.ValueKind == JsonValueKind.Number)
            return el.TryGetInt32(out value);

        if (el.ValueKind == JsonValueKind.String)
        {
            var text = (el.GetString() ?? string.Empty).Trim();
            return int.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out value);
        }

        return false;
    }

    private static bool TryGetStringRequired(JsonElement obj, string name, out string value)
    {
        value = string.Empty;
        if (!obj.TryGetProperty(name, out var el))
            return false;
        if (el.ValueKind != JsonValueKind.String)
            return false;
        value = el.GetString() ?? string.Empty;
        return !string.IsNullOrWhiteSpace(value);
    }
}
