using Game.Core.Contracts.Sanguo;
using Godot;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

/// <summary>
/// Builds a stable, UI-facing explanation string for events.
/// Facts-only: the UI must not infer or compute gameplay rules.
/// </summary>
public static class EventExplainService
{
    public static EventExplanation Explain(
        string type,
        string source,
        string eventId,
        string timestampIso,
        JsonElement root,
        Func<int, string?>? tileLabelByIndex = null)
    {
        var correlationId = TryGetStringLoose(root, "CorrelationId");
        var causationId = TryGetStringLoose(root, "CausationId");

        var summary = BuildSummary(type, root);
        var details = BuildDetails(type, root, tileLabelByIndex, source, eventId, timestampIso, correlationId, causationId);

        return new EventExplanation(
            EventType: type,
            SummaryText: summary,
            DetailText: details,
            Source: source,
            EventId: eventId,
            TimestampIso: timestampIso,
            CorrelationId: correlationId,
            CausationId: causationId
        );
    }

    private static string BuildSummary(string type, JsonElement root)
    {
        var prefix = BuildSummaryPrefix(type);
        var multiplierSuffix = BuildAppliedMultipliersSuffix(root);

        if (string.Equals(type, SanguoCityTollPaid.EventType, StringComparison.Ordinal))
        {
            var payerId = TryGetStringLoose(root, "PayerId") ?? string.Empty;
            var ownerId = TryGetStringLoose(root, "OwnerId") ?? string.Empty;
            var cityId = TryGetStringLoose(root, "CityId") ?? string.Empty;
            var amount = TryGetDecimalLoose(root, "Amount");
            var ownerAmount = TryGetDecimalLoose(root, "OwnerAmount");
            var overflow = TryGetDecimalLoose(root, "TreasuryOverflow");

            var parts = new List<string>(8) { prefix };
            if (!string.IsNullOrWhiteSpace(payerId)) parts.Add($"payer={payerId}");
            if (!string.IsNullOrWhiteSpace(ownerId)) parts.Add($"owner={ownerId}");
            if (!string.IsNullOrWhiteSpace(cityId)) parts.Add($"city={cityId}");
            if (amount.HasValue) parts.Add($"amount={FormatDecimal(amount.Value)}");
            if (ownerAmount.HasValue) parts.Add($"owner_amount={FormatDecimal(ownerAmount.Value)}");
            if (overflow.HasValue && overflow.Value != 0m) parts.Add($"overflow={FormatDecimal(overflow.Value)}");

            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoMonthSettled.EventType, StringComparison.Ordinal))
        {
            var year = TryGetIntLoose(root, "Year");
            var month = TryGetIntLoose(root, "Month");
            var turn = TryGetIntLoose(root, "TurnNumber");
            var parts = new List<string>(6) { prefix };
            if (turn.HasValue) parts.Add($"turn={turn.Value}");
            if (year.HasValue) parts.Add($"year={year.Value}");
            if (month.HasValue) parts.Add($"month={month.Value}");
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoTokenMoved.EventType, StringComparison.Ordinal))
        {
            var playerId = TryGetStringLoose(root, "PlayerId");
            var from = TryGetIntLoose(root, "FromIndex");
            var to = TryGetIntLoose(root, "ToIndex");
            var steps = TryGetIntLoose(root, "Steps");
            var passedStart = TryGetBoolLoose(root, "PassedStart");

            var parts = new List<string>(8) { prefix };
            if (!string.IsNullOrWhiteSpace(playerId)) parts.Add($"player={playerId}");
            if (from.HasValue) parts.Add($"from={from.Value}");
            if (to.HasValue) parts.Add($"to={to.Value}");
            if (steps.HasValue) parts.Add($"steps={steps.Value}");
            if (passedStart.HasValue) parts.Add($"passed_start={passedStart.Value.ToString().ToLowerInvariant()}");
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoGameEnded.EventType, StringComparison.Ordinal))
        {
            var reason = TryGetStringLoose(root, "EndReason");
            var winner = TryGetStringLoose(root, "WinnerPlayerId");
            var parts = new List<string>(6) { prefix };
            if (!string.IsNullOrWhiteSpace(reason)) parts.Add($"reason={reason}");
            if (!string.IsNullOrWhiteSpace(winner)) parts.Add($"winner={winner}");
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoRandomEventApplied.EventType, StringComparison.Ordinal))
        {
            var playerId = TryGetStringLoose(root, "PlayerId");
            var pickedId = TryGetStringLoose(root, "PickedId");
            if (string.IsNullOrWhiteSpace(pickedId))
            {
                pickedId = TryGetStringLoose(root, "EventId");
            }
            var effectKind = TryGetStringLoose(root, "EffectKind");

            var parts = new List<string>(8) { prefix };
            if (!string.IsNullOrWhiteSpace(playerId)) parts.Add($"player={playerId}");
            if (!string.IsNullOrWhiteSpace(pickedId)) parts.Add($"picked={pickedId}");
            if (!string.IsNullOrWhiteSpace(effectKind)) parts.Add($"kind={effectKind}");
            return string.Join(' ', parts) + multiplierSuffix;
        }

        // Generic fallbacks used by existing tests:
        var player = TryGetStringLoose(root, "PlayerId") ?? TryGetStringLoose(root, "ActivePlayerId");
        if (TryGetPropertyLoose(root, "Value", out var value) && value.ValueKind == JsonValueKind.Number)
        {
            return string.IsNullOrWhiteSpace(player)
                ? $"{type} value={value}{multiplierSuffix}"
                : $"{type} player={player} value={value}{multiplierSuffix}";
        }

        if (TryGetPropertyLoose(root, "CityId", out var cityIdProp))
        {
            var city = cityIdProp.ValueKind == JsonValueKind.String ? (cityIdProp.GetString() ?? string.Empty) : cityIdProp.ToString();
            var summary = string.IsNullOrWhiteSpace(player) ? $"{type} city={city}" : $"{type} player={player} city={city}";
            if (TryGetPropertyLoose(root, "Price", out var price) && price.ValueKind == JsonValueKind.Number)
            {
                summary += $" price={price}";
            }
            return summary + multiplierSuffix;
        }

        return string.IsNullOrWhiteSpace(player) ? prefix + multiplierSuffix : $"{prefix} player={player}{multiplierSuffix}";
    }

    private static string BuildDetails(
        string type,
        JsonElement root,
        Func<int, string?>? tileLabelByIndex,
        string source,
        string eventId,
        string timestampIso,
        string? correlationId,
        string? causationId)
    {
        var sb = new StringBuilder(512);
        sb.AppendLine($"type: {type}");
        sb.AppendLine($"source: {source}");
        sb.AppendLine($"id: {eventId}");
        sb.AppendLine($"ts: {timestampIso}");

        if (!string.IsNullOrWhiteSpace(correlationId)) sb.AppendLine($"correlation_id: {correlationId}");
        if (!string.IsNullOrWhiteSpace(causationId)) sb.AppendLine($"causation_id: {causationId}");

        var deltas = new List<string>(8);
        var facts = new List<string>(32);

        if (string.Equals(type, SanguoCityTollPaid.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "TurnNumber", "turn");
            AddFact(facts, type, root, "CityId", "city_id");
            AddFact(facts, type, root, "PayerId", "payer_id");
            AddFact(facts, type, root, "OwnerId", "owner_id");

            var amount = TryGetDecimalLoose(root, "Amount");
            var ownerAmount = TryGetDecimalLoose(root, "OwnerAmount");
            var overflow = TryGetDecimalLoose(root, "TreasuryOverflow");

            if (amount.HasValue)
            {
                var payerId = TryGetStringLoose(root, "PayerId") ?? "payer";
                var label = TranslateField(type, "delta", "money_delta", "money_delta");
                deltas.Add($"{label}[{payerId}]: -{FormatDecimal(amount.Value)}");
            }
            if (ownerAmount.HasValue)
            {
                var ownerId = TryGetStringLoose(root, "OwnerId") ?? "owner";
                var label = TranslateField(type, "delta", "money_delta", "money_delta");
                deltas.Add($"{label}[{ownerId}]: +{FormatDecimal(ownerAmount.Value)}");
            }
            if (overflow.HasValue && overflow.Value != 0m)
            {
                var label = TranslateField(type, "delta", "treasury_delta", "treasury_delta");
                deltas.Add($"{label}: +{FormatDecimal(overflow.Value)}");
            }

            AddAppliedMultipliersFacts(facts, type, root);
        }
        else if (string.Equals(type, SanguoMonthSettled.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "TurnNumber", "turn");
            AddFact(facts, type, root, "Year", "year");
            AddFact(facts, type, root, "Month", "month");

            if (TryGetPropertyLoose(root, "PlayerSettlements", out var settlements) && settlements.ValueKind == JsonValueKind.Array)
            {
                var count = 0;
                foreach (var item in settlements.EnumerateArray())
                {
                    var pid = TryGetStringLoose(item, "PlayerId") ?? "player";
                    var delta = TryGetDecimalLoose(item, "AmountDelta");
                    if (delta.HasValue)
                    {
                        var label = TranslateField(type, "delta", "money_delta", "money_delta");
                        deltas.Add($"{label}[{pid}]: {FormatSignedDecimal(delta.Value)}");
                        count++;
                        if (count >= 12)
                        {
                            var label = TranslateField(type, "delta", "money_delta", "money_delta");
                            deltas.Add($"{label}[...]: (truncated)");
                            break;
                        }
                    }
                }
                var label = TranslateField(type, "detail", "player_settlements_count", "player_settlements_count");
                facts.Add($"{label}: {settlements.GetArrayLength()}");
            }

            AddAppliedMultipliersFacts(facts, type, root);
        }
        else if (string.Equals(type, SanguoTokenMoved.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "PlayerId", "player_id");
            AddFact(facts, type, root, "Steps", "steps");
            AddFact(facts, type, root, "PassedStart", "passed_start");

            var from = TryGetIntLoose(root, "FromIndex");
            var to = TryGetIntLoose(root, "ToIndex");
            if (from.HasValue)
            {
                var label = TranslateField(type, "detail", "from_index", "from_index");
                facts.Add($"{label}: {from.Value}");
            }
            if (to.HasValue)
            {
                var label = TranslateField(type, "detail", "to_index", "to_index");
                facts.Add($"{label}: {to.Value}");
            }

            if (tileLabelByIndex != null)
            {
                if (from.HasValue)
                {
                    var label = tileLabelByIndex(from.Value);
                    if (!string.IsNullOrWhiteSpace(label))
                    {
                        var k = TranslateField(type, "detail", "from_tile", "from_tile");
                        facts.Add($"{k}: {label}");
                    }
                }
                if (to.HasValue)
                {
                    var label = tileLabelByIndex(to.Value);
                    if (!string.IsNullOrWhiteSpace(label))
                    {
                        var k = TranslateField(type, "detail", "to_tile", "to_tile");
                        facts.Add($"{k}: {label}");
                    }
                }
            }
        }
        else if (string.Equals(type, SanguoGameEnded.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "EndReason", "end_reason");
            AddFact(facts, type, root, "WinnerPlayerId", "winner_player_id");
        }
        else if (string.Equals(type, SanguoRandomEventApplied.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "PlayerId", "player_id");
            AddFact(facts, type, root, "EventId", "event_id");
            AddFact(facts, type, root, "PickedId", "picked_id");
            AddFact(facts, type, root, "EffectKind", "effect_kind");
            AddFact(facts, type, root, "EncounterId", "encounter_id");
            AddFact(facts, type, root, "EncounterTarget", "encounter_target");

            var moneyDelta = TryGetIntLoose(root, "MoneyDelta");
            if (moneyDelta.HasValue && moneyDelta.Value != 0)
            {
                var label = TranslateField(type, "delta", "money_delta", "money_delta");
                deltas.Add($"{label}: {moneyDelta.Value}");
            }
            var stepDelta = TryGetIntLoose(root, "StepDelta");
            if (stepDelta.HasValue && stepDelta.Value != 0)
            {
                var label = TranslateField(type, "delta", "step_delta", "step_delta");
                deltas.Add($"{label}: {stepDelta.Value}");
            }

            AddAppliedMultipliersFacts(facts, type, root);
        }
        else
        {
            // Generic: include some common fields without duplicating full payload.
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "TurnNumber", "turn");
            AddFact(facts, type, root, "RoundNumber", "round");
            AddFact(facts, type, root, "PlayerId", "player_id");
            AddFact(facts, type, root, "ActivePlayerId", "active_player_id");
            AddAppliedMultipliersFacts(facts, type, root);
        }

        sb.AppendLine();

        if (deltas.Count != 0)
        {
            sb.AppendLine("deltas:");
            foreach (var d in deltas)
            {
                sb.AppendLine($"- {d}");
            }
            sb.AppendLine();
        }

        if (facts.Count != 0)
        {
            sb.AppendLine("facts:");
            foreach (var f in facts)
            {
                sb.AppendLine($"- {f}");
            }
        }

        return sb.ToString().TrimEnd();
    }

    private static void AddFact(List<string> facts, string eventType, JsonElement root, string propertyName, string factKey)
    {
        if (!TryGetPropertyLoose(root, propertyName, out var el))
        {
            return;
        }

        var label = TranslateField(eventType, "detail", factKey, factKey);
        switch (el.ValueKind)
        {
            case JsonValueKind.String:
                var s = el.GetString();
                if (!string.IsNullOrWhiteSpace(s)) facts.Add($"{label}: {s}");
                break;
            case JsonValueKind.Number:
                facts.Add($"{label}: {el}");
                break;
            case JsonValueKind.True:
            case JsonValueKind.False:
                facts.Add($"{label}: {el.GetBoolean().ToString().ToLowerInvariant()}");
                break;
        }
    }

    private static void AddAppliedMultipliersFacts(List<string> facts, string eventType, JsonElement root)
    {
        if (!TryGetPropertyLoose(root, "AppliedMultipliers", out var m) || m.ValueKind != JsonValueKind.Object)
        {
            return;
        }

        var effective = TryGetDecimalLoose(m, "Effective");
        if (effective.HasValue)
        {
            var label = TranslateField(eventType, "detail", "mult.effective", "mult.effective");
            facts.Add($"{label}: {FormatDecimal(effective.Value)}");
        }

        var sources = TryGetIntLoose(m, "Sources");
        if (sources.HasValue)
        {
            var label = TranslateField(eventType, "detail", "mult.sources", "mult.sources");
            facts.Add($"{label}: {sources.Value}");
        }

        var character = TryGetDecimalLoose(m, "Character");
        if (character.HasValue)
        {
            var label = TranslateField(eventType, "detail", "mult.character", "mult.character");
            facts.Add($"{label}: {FormatDecimal(character.Value)}");
        }

        var building = TryGetDecimalLoose(m, "Building");
        if (building.HasValue)
        {
            var label = TranslateField(eventType, "detail", "mult.building", "mult.building");
            facts.Add($"{label}: {FormatDecimal(building.Value)}");
        }

        var ev = TryGetDecimalLoose(m, "Event");
        if (ev.HasValue)
        {
            var label = TranslateField(eventType, "detail", "mult.event", "mult.event");
            facts.Add($"{label}: {FormatDecimal(ev.Value)}");
        }

        var card = TryGetDecimalLoose(m, "ActionCard");
        if (card.HasValue)
        {
            var label = TranslateField(eventType, "detail", "mult.action_card", "mult.action_card");
            facts.Add($"{label}: {FormatDecimal(card.Value)}");
        }
    }

    private static string BuildAppliedMultipliersSuffix(JsonElement root)
    {
        if (!TryGetPropertyLoose(root, "AppliedMultipliers", out var m) || m.ValueKind != JsonValueKind.Object)
        {
            return string.Empty;
        }

        var effective = TryGetDecimalLoose(m, "Effective");
        if (!effective.HasValue)
        {
            return string.Empty;
        }

        var suffix = $" mult={FormatDecimal(effective.Value)}";

        var sources = TryGetIntLoose(m, "Sources") ?? 0;
        if (sources == 0)
        {
            return suffix;
        }

        // Only display breakdown factors when Sources indicates they are trustworthy.
        // UI must not compute money; it only echoes the event payload values.
        if ((sources & 1) != 0)
        {
            var c = TryGetDecimalLoose(m, "Character");
            if (c.HasValue) suffix += $" c={FormatDecimal(c.Value)}";
        }
        if ((sources & 2) != 0)
        {
            var b = TryGetDecimalLoose(m, "Building");
            if (b.HasValue) suffix += $" b={FormatDecimal(b.Value)}";
        }
        if ((sources & 4) != 0)
        {
            var e = TryGetDecimalLoose(m, "Event");
            if (e.HasValue) suffix += $" e={FormatDecimal(e.Value)}";
        }
        if ((sources & 8) != 0)
        {
            var a = TryGetDecimalLoose(m, "ActionCard");
            if (a.HasValue) suffix += $" a={FormatDecimal(a.Value)}";
        }

        return suffix;
    }

    private static string BuildSummaryPrefix(string type)
    {
        var prefix = $"ui.hud.event.{type}";
        var title = TranslateOrFallback($"{prefix}.title", type);
        var summary = TranslateOrFallback($"{prefix}.summary", title);

        if (string.Equals(summary, type, StringComparison.Ordinal))
        {
            return type;
        }

        return $"{summary} ({type})";
    }

    private static string TranslateField(string eventType, string section, string fieldKey, string fallback)
    {
        var key = $"ui.hud.event.{eventType}.{section}.{fieldKey}";
        return TranslateOrFallback(key, fallback);
    }

    private static string TranslateOrFallback(string key, string fallback)
    {
        var text = TranslationServer.Translate(key);
        if (string.IsNullOrWhiteSpace(text) || string.Equals(text, key, StringComparison.Ordinal))
        {
            return fallback;
        }
        return text;
    }

    private static bool TryGetPropertyLoose(JsonElement obj, string expectedName, out JsonElement value)
    {
        if (obj.ValueKind != JsonValueKind.Object)
        {
            value = default;
            return false;
        }

        foreach (var p in obj.EnumerateObject())
        {
            var name = p.Name;
            if (string.Equals(name, expectedName, StringComparison.OrdinalIgnoreCase))
            {
                value = p.Value;
                return true;
            }

            if (string.Equals(name.Trim(), expectedName, StringComparison.OrdinalIgnoreCase))
            {
                value = p.Value;
                return true;
            }
        }

        value = default;
        return false;
    }

    private static string? TryGetStringLoose(JsonElement obj, string expectedName)
    {
        if (!TryGetPropertyLoose(obj, expectedName, out var value))
        {
            return null;
        }

        if (value.ValueKind == JsonValueKind.String)
        {
            return value.GetString();
        }

        return value.ValueKind == JsonValueKind.Null ? null : value.ToString();
    }

    private static int? TryGetIntLoose(JsonElement obj, string expectedName)
    {
        if (!TryGetPropertyLoose(obj, expectedName, out var value))
        {
            return null;
        }

        if (value.ValueKind == JsonValueKind.Number)
        {
            if (value.TryGetInt32(out var i)) return i;
            if (value.TryGetInt64(out var l) && l is >= int.MinValue and <= int.MaxValue) return (int)l;
            return null;
        }

        if (value.ValueKind == JsonValueKind.String && int.TryParse(value.GetString(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed))
        {
            return parsed;
        }

        return null;
    }

    private static bool? TryGetBoolLoose(JsonElement obj, string expectedName)
    {
        if (!TryGetPropertyLoose(obj, expectedName, out var value))
        {
            return null;
        }

        if (value.ValueKind == JsonValueKind.True || value.ValueKind == JsonValueKind.False)
        {
            return value.GetBoolean();
        }

        if (value.ValueKind == JsonValueKind.String && bool.TryParse(value.GetString(), out var parsed))
        {
            return parsed;
        }

        return null;
    }

    private static decimal? TryGetDecimalLoose(JsonElement obj, string expectedName)
    {
        if (!TryGetPropertyLoose(obj, expectedName, out var value))
        {
            return null;
        }

        if (value.ValueKind == JsonValueKind.Number)
        {
            if (value.TryGetDecimal(out var d)) return d;
            if (value.TryGetInt64(out var l)) return l;
            if (value.TryGetDouble(out var dbl)) return (decimal)dbl;
            return null;
        }

        if (value.ValueKind == JsonValueKind.String && decimal.TryParse(value.GetString(), NumberStyles.Number, CultureInfo.InvariantCulture, out var parsed))
        {
            return parsed;
        }

        return null;
    }

    private static string FormatDecimal(decimal value) => value.ToString("0.##", CultureInfo.InvariantCulture);

    private static string FormatSignedDecimal(decimal value)
    {
        if (value == 0m) return "0";
        return value > 0m ? $"+{FormatDecimal(value)}" : FormatDecimal(value);
    }
}
