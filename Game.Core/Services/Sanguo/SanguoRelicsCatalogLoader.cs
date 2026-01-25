using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Game.Core.Services.Sanguo;

public static class SanguoRelicsCatalogLoader
{
    public const string RelicsResPath = "res://Data/relics.json";

    public const int MinStepDelta = -6;
    public const int MaxStepDelta = 6;

    private static readonly JsonDocumentOptions DocOptions = new()
    {
        CommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 64,
    };

    public static bool TryLoadRelicsCatalog(IResourceLoader loader, out SanguoRelicsCatalog catalog, out string error)
    {
        ArgumentNullException.ThrowIfNull(loader);

        catalog = new SanguoRelicsCatalog(SchemaVersion: 0, Version: 0, Relics: Array.Empty<SanguoRelicDefinition>());
        error = string.Empty;

        var json = loader.LoadText(RelicsResPath);
        if (string.IsNullOrWhiteSpace(json))
        {
            error = "relics_catalog_missing";
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
                error = "invalid_relics_catalog:root_not_object";
                return false;
            }

            if (!TryGetInt32Required(doc.RootElement, "schemaVersion", out var schemaVersion)
                || !TryGetInt32Required(doc.RootElement, "version", out var version))
            {
                error = "invalid_relics_catalog:bad_versions";
                return false;
            }

            if (schemaVersion <= 0 || version <= 0)
            {
                error = "invalid_relics_catalog:bad_versions";
                return false;
            }

            if (!doc.RootElement.TryGetProperty("relics", out var relicsEl))
            {
                error = "invalid_relics_catalog:missing_relics";
                return false;
            }

            if (relicsEl.ValueKind != JsonValueKind.Array)
            {
                error = "invalid_relics_catalog:relics_not_array";
                return false;
            }

            var valid = new List<SanguoRelicDefinition>();
            var seen = new HashSet<string>(StringComparer.Ordinal);

            foreach (var relicEl in relicsEl.EnumerateArray())
            {
                if (relicEl.ValueKind != JsonValueKind.Object)
                {
                    error = "invalid_relics_catalog:relic_not_object";
                    return false;
                }

                if (!TryGetStringRequired(relicEl, "relicId", out var relicId))
                {
                    error = "invalid_relics_catalog:missing_relic_id";
                    return false;
                }

                if (!seen.Add(relicId))
                {
                    error = "invalid_relics_catalog:duplicate_relic_id";
                    return false;
                }

                if (!TryGetStringRequired(relicEl, "nameKey", out var nameKey))
                {
                    error = "invalid_relics_catalog:missing_name_key";
                    return false;
                }

                if (!TryGetStringRequired(relicEl, "descriptionKey", out var descriptionKey))
                {
                    error = "invalid_relics_catalog:missing_description_key";
                    return false;
                }

                if (!TryGetStringRequired(relicEl, "effectKind", out var effectKind))
                {
                    error = "invalid_relics_catalog:missing_effect_kind";
                    return false;
                }

                if (!string.Equals(effectKind, SanguoEffectKinds.MoneyDelta, StringComparison.Ordinal)
                    && !string.Equals(effectKind, SanguoEffectKinds.EconomyStepDelta, StringComparison.Ordinal))
                {
                    error = "invalid_relics_catalog:invalid_effect_kind";
                    return false;
                }

                int? moneyDelta = null;
                int? stepDelta = null;

                if (string.Equals(effectKind, SanguoEffectKinds.MoneyDelta, StringComparison.Ordinal))
                {
                    if (!TryGetInt32Required(relicEl, "moneyDelta", out var md))
                    {
                        error = "invalid_relics_catalog:missing_money_delta";
                        return false;
                    }

                    if (md <= 0)
                    {
                        error = "invalid_relics_catalog:invalid_money_delta";
                        return false;
                    }

                    moneyDelta = md;
                }
                else
                {
                    if (!TryGetInt32Required(relicEl, "stepDelta", out var sd))
                    {
                        error = "invalid_relics_catalog:missing_step_delta";
                        return false;
                    }

                    if (sd < MinStepDelta || sd > MaxStepDelta || sd == 0)
                    {
                        error = "invalid_relics_catalog:invalid_step_delta";
                        return false;
                    }

                    stepDelta = sd;
                }

                valid.Add(new SanguoRelicDefinition(
                    RelicId: relicId,
                    NameKey: nameKey,
                    DescriptionKey: descriptionKey,
                    EffectKind: effectKind,
                    MoneyDelta: moneyDelta,
                    EconomyStepDelta: stepDelta));
            }

            var readOnly = Array.AsReadOnly(valid.OrderBy(x => x.RelicId, StringComparer.Ordinal).ToArray());
            catalog = new SanguoRelicsCatalog(schemaVersion, version, readOnly);
            return true;
        }
    }

    private static bool TryGetInt32Required(JsonElement obj, string name, out int value)
    {
        value = 0;
        if (!obj.TryGetProperty(name, out var el))
            return false;
        if (el.ValueKind != JsonValueKind.Number)
            return false;
        return el.TryGetInt32(out value);
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

