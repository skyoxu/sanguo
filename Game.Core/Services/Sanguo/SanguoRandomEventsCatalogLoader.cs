using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Game.Core.Services.Sanguo;

public static class SanguoRandomEventsCatalogLoader
{
    public const string RandomEventsResPath = "res://Data/random_events.json";

    private static readonly HashSet<string> AllowedEffectKinds = new(StringComparer.Ordinal)
    {
        SanguoEffectKinds.MoneyDelta,
        SanguoEffectKinds.EconomyStepDelta,
        SanguoEffectKinds.StartCombat,
    };

    private static readonly JsonDocumentOptions DocOptions = new()
    {
        CommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 64,
    };

    public static bool TryLoadRandomEventsCatalog(IResourceLoader loader, out SanguoRandomEventsCatalog catalog, out string error)
        => TryLoadRandomEventsCatalog(loader, pack: null, out catalog, out error);

    public static bool TryLoadRandomEventsCatalog(IResourceLoader loader, SanguoContentPackPaths? pack, out SanguoRandomEventsCatalog catalog, out string error)
    {
        ArgumentNullException.ThrowIfNull(loader);

        catalog = new SanguoRandomEventsCatalog(
            SchemaVersion: 0,
            Version: 0,
            Events: Array.Empty<SanguoRandomEventCatalogEntry>(),
            EventPools: Array.Empty<SanguoRandomEventPoolCatalogEntry>());
        error = string.Empty;

        var resPath = pack?.RandomEventsPath ?? RandomEventsResPath;
        var json = loader.LoadText(resPath);
        if (string.IsNullOrWhiteSpace(json))
        {
            error = "random_events_catalog_missing";
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
                error = "invalid_random_events_catalog:root_not_object";
                return false;
            }

            if (!TryGetInt32Required(doc.RootElement, "schemaVersion", out var schemaVersion))
            {
                error = "invalid_random_events_catalog:bad_versions";
                return false;
            }

            if (!TryGetInt32Required(doc.RootElement, "version", out var version))
            {
                error = "invalid_random_events_catalog:bad_versions";
                return false;
            }

            if (schemaVersion <= 0 || version <= 0)
            {
                error = "invalid_random_events_catalog:bad_versions";
                return false;
            }

            var pools = new List<SanguoRandomEventPoolCatalogEntry>();
            if (!TryParsePools(doc.RootElement, pools, out error))
            {
                return false;
            }

            var poolIds = new HashSet<string>(pools.Select(p => p.PoolId), StringComparer.Ordinal);
            if (!poolIds.Contains("default") || !poolIds.Contains("global"))
            {
                error = "invalid_random_events_catalog:missing_required_pools";
                return false;
            }

            var events = new List<SanguoRandomEventCatalogEntry>();
            if (!TryParseEvents(doc.RootElement, events, out error))
            {
                return false;
            }

            catalog = new SanguoRandomEventsCatalog(
                SchemaVersion: schemaVersion,
                Version: version,
                Events: events,
                EventPools: pools);

            return true;
        }
    }

    private static bool TryParsePools(JsonElement root, List<SanguoRandomEventPoolCatalogEntry> pools, out string error)
    {
        error = string.Empty;

        if (!root.TryGetProperty("eventPools", out var poolsEl))
        {
            error = "invalid_random_events_catalog:eventPools_missing";
            return false;
        }

        if (poolsEl.ValueKind != JsonValueKind.Array)
        {
            error = "invalid_random_events_catalog:eventPools_not_array";
            return false;
        }

        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var poolEl in poolsEl.EnumerateArray())
        {
            if (poolEl.ValueKind != JsonValueKind.Object)
            {
                error = "invalid_random_events_catalog:pool_not_object";
                return false;
            }

            if (!TryGetStringRequired(poolEl, "poolId", out var poolId))
            {
                error = "invalid_random_events_catalog:pool_missing_poolId";
                return false;
            }

            if (!seen.Add(poolId))
            {
                continue;
            }

            if (!poolEl.TryGetProperty("eventIds", out var idsEl) || idsEl.ValueKind != JsonValueKind.Array)
            {
                error = "invalid_random_events_catalog:pool_missing_eventIds";
                return false;
            }

            var ids = new List<string>();
            foreach (var idEl in idsEl.EnumerateArray())
            {
                if (idEl.ValueKind != JsonValueKind.String)
                {
                    error = "invalid_random_events_catalog:pool_eventIds_not_strings";
                    return false;
                }

                var id = (idEl.GetString() ?? string.Empty).Trim();
                if (!string.IsNullOrWhiteSpace(id))
                {
                    ids.Add(id);
                }
            }

            pools.Add(new SanguoRandomEventPoolCatalogEntry(PoolId: poolId, EventIds: ids));
        }

        if (pools.Count == 0)
        {
            error = "invalid_random_events_catalog:eventPools_empty";
            return false;
        }

        return true;
    }

    private static bool TryParseEvents(JsonElement root, List<SanguoRandomEventCatalogEntry> events, out string error)
    {
        error = string.Empty;

        if (!root.TryGetProperty("events", out var eventsEl))
        {
            error = "invalid_random_events_catalog:events_missing";
            return false;
        }

        if (eventsEl.ValueKind != JsonValueKind.Array)
        {
            error = "invalid_random_events_catalog:events_not_array";
            return false;
        }

        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var evEl in eventsEl.EnumerateArray())
        {
            if (evEl.ValueKind != JsonValueKind.Object)
            {
                error = "invalid_random_events_catalog:event_not_object";
                return false;
            }

            if (!TryGetStringRequired(evEl, "eventId", out var eventId))
            {
                error = "invalid_random_events_catalog:event_missing_eventId";
                return false;
            }

            if (!seen.Add(eventId))
            {
                continue;
            }

            if (!TryGetStringRequired(evEl, "nameKey", out var nameKey))
            {
                error = "invalid_random_events_catalog:event_missing_nameKey";
                return false;
            }

            if (!TryGetStringRequired(evEl, "descriptionKey", out var descriptionKey))
            {
                error = "invalid_random_events_catalog:event_missing_descriptionKey";
                return false;
            }

            if (!TryGetStringRequired(evEl, "effectKind", out var effectKind))
            {
                error = "invalid_random_events_catalog:event_missing_effectKind";
                return false;
            }

            if (!AllowedEffectKinds.Contains(effectKind))
            {
                error = "invalid_random_events_catalog:event_invalid_effectKind";
                return false;
            }

            if (!TryGetBooleanRequired(evEl, "uniqueOnce", out var uniqueOnce))
            {
                error = "invalid_random_events_catalog:event_missing_uniqueOnce";
                return false;
            }

            if (!TryGetInt32Required(evEl, "cooldownRounds", out var cooldownRounds) || cooldownRounds < 0 || cooldownRounds > 1000)
            {
                error = "invalid_random_events_catalog:event_invalid_cooldownRounds";
                return false;
            }

            int? moneyDelta = null;
            int? stepDelta = null;
            string? encounterId = null;
            int? encounterTarget = null;

            if (string.Equals(effectKind, SanguoEffectKinds.MoneyDelta, StringComparison.Ordinal))
            {
                if (!TryGetInt32Required(evEl, "moneyDelta", out var md))
                {
                    error = "invalid_random_events_catalog:event_missing_moneyDelta";
                    return false;
                }
                moneyDelta = md;
            }

            if (string.Equals(effectKind, SanguoEffectKinds.EconomyStepDelta, StringComparison.Ordinal))
            {
                if (!TryGetInt32Required(evEl, "stepDelta", out var sd) || sd is < -6 or > 6)
                {
                    error = "invalid_random_events_catalog:event_invalid_stepDelta";
                    return false;
                }
                stepDelta = sd;
            }

            if (string.Equals(effectKind, SanguoEffectKinds.StartCombat, StringComparison.Ordinal))
            {
                if (!TryGetStringRequired(evEl, "encounterId", out var encId))
                {
                    error = "invalid_random_events_catalog:event_missing_encounterId";
                    return false;
                }

                if (!TryGetInt32Required(evEl, "encounterTarget", out var encTarget) || encTarget < 0 || encTarget > 1000)
                {
                    error = "invalid_random_events_catalog:event_invalid_encounterTarget";
                    return false;
                }

                encounterId = encId;
                encounterTarget = encTarget;
            }

            events.Add(new SanguoRandomEventCatalogEntry(
                EventId: eventId,
                NameKey: nameKey,
                DescriptionKey: descriptionKey,
                EffectKind: effectKind,
                MoneyDelta: moneyDelta,
                StepDelta: stepDelta,
                CooldownRounds: cooldownRounds,
                UniqueOnce: uniqueOnce,
                EncounterId: encounterId,
                EncounterTarget: encounterTarget));
        }

        if (events.Count == 0)
        {
            error = "invalid_random_events_catalog:events_empty";
            return false;
        }

        return true;
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

    private static bool TryGetInt32Required(JsonElement obj, string name, out int value)
    {
        value = 0;
        if (!obj.TryGetProperty(name, out var el) || el.ValueKind != JsonValueKind.Number || !el.TryGetInt32(out value))
        {
            return false;
        }
        return true;
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
}
