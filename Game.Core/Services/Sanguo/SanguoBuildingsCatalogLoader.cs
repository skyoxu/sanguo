using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Game.Core.Services.Sanguo;

public static class SanguoBuildingsCatalogLoader
{
    public const string BuildingsResPath = "res://Data/buildings.json";

    public const int MinStepDelta = -6;
    public const int MaxStepDelta = 6;

    private static readonly HashSet<string> AllowedRootFields = new(StringComparer.Ordinal)
    {
        "schemaVersion",
        "version",
        "buildings",
    };

    private static readonly HashSet<string> AllowedBuildingFields = new(StringComparer.Ordinal)
    {
        "buildingId",
        "nameKey",
        "descriptionKey",
        "maxLevel",
        "buildCostBase",
        "upgradeCostBase",
        "settlementIncomeBase",
        "economyStepDeltas",
    };

    private static readonly HashSet<string> AllowedEconomyStepDeltaFields = new(StringComparer.Ordinal)
    {
        "buyPrice",
        "toll",
        "incomeSettlement",
        "buildCost",
        "upgradeCost",
    };

    private static readonly JsonDocumentOptions DocOptions = new()
    {
        CommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 64,
    };

    public static bool TryLoadBuildingsCatalog(IResourceLoader loader, out SanguoBuildingsCatalog catalog, out string error)
        => TryLoadBuildingsCatalog(loader, pack: null, out catalog, out error);

    public static bool TryLoadBuildingsCatalog(IResourceLoader loader, SanguoContentPackPaths? pack, out SanguoBuildingsCatalog catalog, out string error)
    {
        ArgumentNullException.ThrowIfNull(loader);

        catalog = new SanguoBuildingsCatalog(SchemaVersion: 0, Version: 0, Buildings: Array.Empty<SanguoBuildingDefinition>());
        error = string.Empty;

        var resPath = pack?.BuildingsPath ?? BuildingsResPath;
        var json = loader.LoadText(resPath);
        if (string.IsNullOrWhiteSpace(json))
        {
            error = "buildings_catalog_missing";
            return false;
        }

        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(json, DocOptions);
        }
        catch (Exception ex)
        {
            error = $"json_parse_failed:{ex.GetType().Name}";
            return false;
        }

        using (doc)
        {
            if (doc.RootElement.ValueKind != JsonValueKind.Object)
            {
                error = "invalid_buildings_catalog:root_not_object";
                return false;
            }

            if (!TryRejectUnknownFields(doc.RootElement, AllowedRootFields, out var rootUnknown))
            {
                error = $"invalid_buildings_catalog:unknown_root_field:{rootUnknown}";
                return false;
            }

            if (!TryGetInt32Required(doc.RootElement, "schemaVersion", out var schemaVersion)
                || !TryGetInt32Required(doc.RootElement, "version", out var version))
            {
                error = "invalid_buildings_catalog:bad_versions";
                return false;
            }

            if (schemaVersion <= 0 || version <= 0)
            {
                error = "invalid_buildings_catalog:bad_versions";
                return false;
            }

            if (!doc.RootElement.TryGetProperty("buildings", out var buildingsProp) || buildingsProp.ValueKind != JsonValueKind.Array)
            {
                error = "invalid_buildings_catalog:missing_buildings";
                return false;
            }

            var buildings = new List<SanguoBuildingDefinition>();
            foreach (var entry in buildingsProp.EnumerateArray())
            {
                if (entry.ValueKind != JsonValueKind.Object)
                {
                    error = "invalid_buildings_catalog:building_not_object";
                    return false;
                }

                if (!TryRejectUnknownFields(entry, AllowedBuildingFields, out var unknownBuildingField))
                {
                    error = $"invalid_buildings_catalog:unknown_building_field:{unknownBuildingField}";
                    return false;
                }

                if (!TryGetStringRequired(entry, "buildingId", out var buildingId)
                    || !TryGetStringRequired(entry, "nameKey", out var nameKey)
                    || !TryGetStringRequired(entry, "descriptionKey", out var descriptionKey))
                {
                    error = "invalid_buildings_catalog:missing_required_fields";
                    return false;
                }

                if (!TryGetInt32Required(entry, "maxLevel", out var maxLevel)
                    || !TryGetInt32Required(entry, "buildCostBase", out var buildCostBase)
                    || !TryGetInt32Required(entry, "upgradeCostBase", out var upgradeCostBase)
                    || !TryGetInt32Required(entry, "settlementIncomeBase", out var settlementIncomeBase))
                {
                    error = "invalid_buildings_catalog:bad_numeric_fields";
                    return false;
                }

                if (maxLevel < 1)
                {
                    error = "invalid_buildings_catalog:max_level_out_of_range";
                    return false;
                }

                if (buildCostBase < 0 || upgradeCostBase < 0 || settlementIncomeBase < 0)
                {
                    error = "invalid_buildings_catalog:negative_cost_or_income";
                    return false;
                }

                if (!entry.TryGetProperty("economyStepDeltas", out var deltasProp) || deltasProp.ValueKind != JsonValueKind.Object)
                {
                    error = "invalid_buildings_catalog:missing_economy_step_deltas";
                    return false;
                }

                if (!TryRejectUnknownFields(deltasProp, AllowedEconomyStepDeltaFields, out var unknownDeltaField))
                {
                    error = $"invalid_buildings_catalog:unknown_step_delta_field:{unknownDeltaField}";
                    return false;
                }

                if (!TryGetStepDeltaRequired(deltasProp, "buyPrice", out var buyDelta)
                    || !TryGetStepDeltaRequired(deltasProp, "toll", out var tollDelta)
                    || !TryGetStepDeltaRequired(deltasProp, "incomeSettlement", out var incomeDelta)
                    || !TryGetStepDeltaRequired(deltasProp, "buildCost", out var buildCostDelta)
                    || !TryGetStepDeltaRequired(deltasProp, "upgradeCost", out var upgradeCostDelta))
                {
                    error = "invalid_buildings_catalog:bad_step_deltas";
                    return false;
                }

                buildings.Add(new SanguoBuildingDefinition(
                    BuildingId: buildingId,
                    NameKey: nameKey,
                    DescriptionKey: descriptionKey,
                    MaxLevel: maxLevel,
                    BuildCostBase: buildCostBase,
                    UpgradeCostBase: upgradeCostBase,
                    SettlementIncomeBase: settlementIncomeBase,
                    EconomyStepDeltas: new SanguoEconomyStepDeltas(
                        BuyPrice: buyDelta,
                        Toll: tollDelta,
                        IncomeSettlement: incomeDelta,
                        BuildCost: buildCostDelta,
                        UpgradeCost: upgradeCostDelta)));
            }

            if (buildings.Count == 0)
            {
                error = "invalid_buildings_catalog:no_buildings";
                return false;
            }

            var ids = new HashSet<string>(StringComparer.Ordinal);
            foreach (var b in buildings)
            {
                if (!ids.Add(b.BuildingId))
                {
                    error = $"invalid_buildings_catalog:duplicate_building_id:{b.BuildingId}";
                    return false;
                }
            }

            catalog = new SanguoBuildingsCatalog(
                SchemaVersion: schemaVersion,
                Version: version,
                Buildings: buildings.OrderBy(x => x.BuildingId, StringComparer.Ordinal).ToArray());
            return true;
        }
    }

    private static bool TryRejectUnknownFields(JsonElement element, HashSet<string> allowed, out string unknownName)
    {
        unknownName = string.Empty;
        foreach (var prop in element.EnumerateObject())
        {
            if (!allowed.Contains(prop.Name))
            {
                unknownName = prop.Name;
                return false;
            }
        }
        return true;
    }

    private static bool TryGetStringRequired(JsonElement element, string name, out string value)
    {
        value = string.Empty;
        if (!element.TryGetProperty(name, out var prop) || prop.ValueKind != JsonValueKind.String)
        {
            return false;
        }

        var s = prop.GetString() ?? string.Empty;
        s = s.Trim();
        if (string.IsNullOrWhiteSpace(s))
        {
            return false;
        }

        value = s;
        return true;
    }

    private static bool TryGetInt32Required(JsonElement element, string name, out int value)
    {
        value = 0;
        if (!element.TryGetProperty(name, out var prop))
        {
            return false;
        }

        if (!prop.TryGetInt32(out value))
        {
            return false;
        }

        return true;
    }

    private static bool TryGetStepDeltaRequired(JsonElement element, string name, out int value)
    {
        value = 0;
        if (!TryGetInt32Required(element, name, out value))
        {
            return false;
        }

        if (value < MinStepDelta || value > MaxStepDelta)
        {
            return false;
        }

        return true;
    }
}

