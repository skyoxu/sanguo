using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Game.Core.Services.Sanguo;

public static class SanguoActionCardsCatalogLoader
{
    public const string ActionCardsResPath = "res://Data/action_cards.json";

    public const int MinStepDelta = -6;
    public const int MaxStepDelta = 6;

    public const int MaxDurationRounds = 1000;

    private static readonly JsonDocumentOptions DocOptions = new()
    {
        CommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 64,
    };

    public static bool TryLoadActionCardsCatalog(IResourceLoader loader, out SanguoActionCardsCatalog catalog, out string error)
        => TryLoadActionCardsCatalog(loader, pack: null, out catalog, out error);

    public static bool TryLoadActionCardsCatalog(IResourceLoader loader, SanguoContentPackPaths? pack, out SanguoActionCardsCatalog catalog, out string error)
    {
        ArgumentNullException.ThrowIfNull(loader);

        catalog = new SanguoActionCardsCatalog(SchemaVersion: 0, Version: 0, Cards: Array.Empty<SanguoActionCardCatalogEntry>());
        error = string.Empty;

        var resPath = pack?.ActionCardsPath ?? ActionCardsResPath;
        var json = loader.LoadText(resPath);
        if (string.IsNullOrWhiteSpace(json))
        {
            error = "action_cards_catalog_missing";
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
                error = "invalid_action_cards_catalog:root_not_object";
                return false;
            }

            if (!TryGetInt32Required(doc.RootElement, "schemaVersion", out var schemaVersion))
            {
                error = "invalid_action_cards_catalog:bad_versions";
                return false;
            }

            if (!TryGetInt32Required(doc.RootElement, "version", out var version))
            {
                error = "invalid_action_cards_catalog:bad_versions";
                return false;
            }

            if (schemaVersion <= 0 || version <= 0)
            {
                error = "invalid_action_cards_catalog:bad_versions";
                return false;
            }

            var valid = new List<SanguoActionCardCatalogEntry>();
            var seen = new HashSet<string>(StringComparer.Ordinal);

            if (doc.RootElement.TryGetProperty("cards", out var cardsEl))
            {
                if (cardsEl.ValueKind != JsonValueKind.Array)
                {
                    error = "invalid_action_cards_catalog:cards_not_array";
                    return false;
                }

                foreach (var cardEl in cardsEl.EnumerateArray())
                {
                    if (cardEl.ValueKind != JsonValueKind.Object)
                    {
                        error = "invalid_action_cards_catalog:card_not_object";
                        return false;
                    }

                    if (!TryGetStringOptionalOrFatal(cardEl, "cardId", out var cardId, out var fatalError) || string.IsNullOrWhiteSpace(cardId))
                    {
                        if (!string.IsNullOrWhiteSpace(fatalError))
                        {
                            error = fatalError;
                            return false;
                        }

                        continue;
                    }

                    if (!seen.Add(cardId))
                        continue;

                    if (!TryGetStringOptionalOrFatal(cardEl, "nameKey", out var nameKey, out fatalError) || string.IsNullOrWhiteSpace(nameKey))
                    {
                        if (!string.IsNullOrWhiteSpace(fatalError))
                        {
                            error = fatalError;
                            return false;
                        }

                        continue;
                    }

                    if (!TryGetStringOptionalOrFatal(cardEl, "descriptionKey", out var descriptionKey, out fatalError) || string.IsNullOrWhiteSpace(descriptionKey))
                    {
                        if (!string.IsNullOrWhiteSpace(fatalError))
                        {
                            error = fatalError;
                            return false;
                        }

                        continue;
                    }

                    if (!TryGetStringOptionalOrFatal(cardEl, "effectKind", out var effectKind, out fatalError) || string.IsNullOrWhiteSpace(effectKind))
                    {
                        if (!string.IsNullOrWhiteSpace(fatalError))
                        {
                            error = fatalError;
                            return false;
                        }

                        continue;
                    }

                    var isEconomyStepDelta = string.Equals(effectKind, SanguoEffectKinds.EconomyStepDelta, StringComparison.Ordinal);
                    var isTransferOwnership = string.Equals(effectKind, SanguoEffectKinds.TransferOwnership, StringComparison.Ordinal);
                    if (!isEconomyStepDelta && !isTransferOwnership)
                        continue;

                    if (!TryGetInt32OptionalOrFatal(cardEl, "stepDelta", out var stepDelta, out fatalError))
                    {
                        if (!string.IsNullOrWhiteSpace(fatalError))
                        {
                            error = fatalError;
                            return false;
                        }

                        continue;
                    }

                    if (stepDelta < MinStepDelta || stepDelta > MaxStepDelta)
                        continue;

                    if (!TryGetInt32OptionalOrFatal(cardEl, "durationRounds", out var durationRounds, out fatalError))
                    {
                        if (!string.IsNullOrWhiteSpace(fatalError))
                        {
                            error = fatalError;
                            return false;
                        }

                        continue;
                    }

                    if (durationRounds <= 0)
                        continue;

                    if (durationRounds > MaxDurationRounds)
                        continue;

                    valid.Add(new SanguoActionCardCatalogEntry(
                        CardId: cardId,
                        NameKey: nameKey,
                        DescriptionKey: descriptionKey,
                        EffectKind: effectKind,
                        StepDelta: stepDelta,
                        DurationRounds: durationRounds));
                }
            }

            var readOnly = Array.AsReadOnly(valid.OrderBy(x => x.CardId, StringComparer.Ordinal).ToArray());
            catalog = new SanguoActionCardsCatalog(schemaVersion, version, readOnly);
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

    private static bool TryGetStringOptionalOrFatal(JsonElement obj, string name, out string value, out string fatalError)
    {
        value = string.Empty;
        fatalError = string.Empty;

        if (!obj.TryGetProperty(name, out var el))
            return false;

        if (el.ValueKind != JsonValueKind.String)
        {
            fatalError = $"invalid_action_cards_catalog:card_field_type:{name}";
            return false;
        }

        value = el.GetString() ?? string.Empty;
        return true;
    }

    private static bool TryGetInt32OptionalOrFatal(JsonElement obj, string name, out int value, out string fatalError)
    {
        value = 0;
        fatalError = string.Empty;

        if (!obj.TryGetProperty(name, out var el))
            return false;

        if (el.ValueKind != JsonValueKind.Number)
        {
            fatalError = $"invalid_action_cards_catalog:card_field_type:{name}";
            return false;
        }

        if (!el.TryGetInt32(out value))
        {
            fatalError = $"invalid_action_cards_catalog:card_field_type:{name}";
            return false;
        }

        return true;
    }
}
