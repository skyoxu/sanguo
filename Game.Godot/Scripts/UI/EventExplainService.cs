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
        var additive = new List<string>(16);
        var multiplicative = new List<string>(16);

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

            AddAppliedMultipliersFacts(additive, multiplicative, type, root);
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

            AddAppliedMultipliersFacts(additive, multiplicative, type, root);
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

            AddAppliedMultipliersFacts(additive, multiplicative, type, root);
        }
        else if (string.Equals(type, SanguoCityTollSynergyPaid.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "TurnNumber", "turn");
            AddFact(facts, type, root, "PayerId", "payer_id");
            AddFact(facts, type, root, "OwnerId", "owner_id");
            AddFact(facts, type, root, "LandingCityId", "landing_city_id");
            AddFact(facts, type, root, "RegionId", "region_id");
            AddFact(facts, type, root, "ExpectedTotalAmount", "expected_total_amount");
            AddFact(facts, type, root, "PaidTotalAmount", "paid_total_amount");
            AddFact(facts, type, root, "ExpectedCitiesCount", "expected_cities_count");
            AddFact(facts, type, root, "PaidCitiesCount", "paid_cities_count");

            if (TryGetPropertyLoose(root, "Breakdown", out var breakdown) && breakdown.ValueKind == JsonValueKind.Array)
            {
                var idx = 0;
                foreach (var item in breakdown.EnumerateArray())
                {
                    idx++;
                    var cityId = TryGetStringLoose(item, "CityId") ?? $"item_{idx}";
                    var amount = TryGetDecimalLoose(item, "Amount");
                    if (amount.HasValue)
                    {
                        var label = TranslateField(type, "detail", "breakdown_amount", "breakdown_amount");
                        facts.Add($"{label}[{cityId}]: {FormatDecimal(amount.Value)}");
                    }

                    AddAppliedMultipliersFacts(additive, multiplicative, type, item, $"breakdown[{cityId}]");
                }
            }
        }
        else
        {
            // Generic: include some common fields without duplicating full payload.
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "TurnNumber", "turn");
            AddFact(facts, type, root, "RoundNumber", "round");
            AddFact(facts, type, root, "PlayerId", "player_id");
            AddFact(facts, type, root, "ActivePlayerId", "active_player_id");
            AddAppliedMultipliersFacts(additive, multiplicative, type, root);
        }

        AppendSection(sb, "deltas", deltas);
        AppendSection(sb, "facts", facts);
        AppendSection(sb, TranslateField(type, "detail", "mult.additive", "additive"), additive);
        AppendSection(sb, TranslateField(type, "detail", "mult.multiplicative", "multiplicative"), multiplicative);

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

    private static void AddAppliedMultipliersFacts(
        List<string> additive,
        List<string> multiplicative,
        string eventType,
        JsonElement root,
        string? prefix = null)
    {
        if (!TryGetAppliedMultipliersElement(root, out var m))
        {
            return;
        }

        AddAppliedMultipliersFactsFromElement(additive, multiplicative, eventType, m, prefix);
    }

    private static string BuildAppliedMultipliersSuffix(JsonElement root)
    {
        if (!TryGetAppliedMultipliersElement(root, out var m))
        {
            return string.Empty;
        }

        return BuildAppliedMultipliersInline(m);
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
        var text = TryTranslate(key);
        if (!string.IsNullOrWhiteSpace(text))
        {
            return text!;
        }

        var sharedKey = $"ui.hud.event.shared.{section}.{fieldKey}";
        var shared = TryTranslate(sharedKey);
        if (!string.IsNullOrWhiteSpace(shared))
        {
            return shared!;
        }

        return fallback;
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

    private static string? TryTranslate(string key)
    {
        var text = TranslationServer.Translate(key);
        if (string.IsNullOrWhiteSpace(text) || string.Equals(text, key, StringComparison.Ordinal))
        {
            return null;
        }
        return text;
    }

    private static void AddAppliedMultipliersFactsFromElement(
        List<string> additive,
        List<string> multiplicative,
        string eventType,
        JsonElement applied,
        string? prefix = null)
    {
        var sources = TryGetIntLoose(applied, "Sources");
        var prefixLabel = string.IsNullOrWhiteSpace(prefix) ? string.Empty : $"{prefix} ";

        var baseSteps = TryGetIntLoose(applied, "BaseSteps");
        if (baseSteps.HasValue)
        {
            AddLabeledValue(additive, prefixLabel, TranslateField(eventType, "detail", "mult.base_steps", "base_steps"), baseSteps.Value.ToString(CultureInfo.InvariantCulture));
        }

        AddStepDelta(additive, prefixLabel, eventType, applied, "CharacterStepDelta", AppliedMultiplierSources.Character, sources, "mult.character_step_delta", "character_step_delta");
        AddStepDelta(additive, prefixLabel, eventType, applied, "BuildingStepDelta", AppliedMultiplierSources.Building, sources, "mult.building_step_delta", "building_step_delta");
        AddStepDelta(additive, prefixLabel, eventType, applied, "EventStepDelta", AppliedMultiplierSources.Event, sources, "mult.event_step_delta", "event_step_delta");
        AddStepDelta(additive, prefixLabel, eventType, applied, "ActionCardStepDelta", AppliedMultiplierSources.ActionCard, sources, "mult.action_card_step_delta", "action_card_step_delta");
        AddStepDelta(additive, prefixLabel, eventType, applied, "RelicStepDelta", AppliedMultiplierSources.Relic, sources, "mult.relic_step_delta", "relic_step_delta");
        AddStepDelta(additive, prefixLabel, eventType, applied, "RegionStepDelta", AppliedMultiplierSources.Region, sources, "mult.region_step_delta", "region_step_delta");

        var effectiveSteps = TryGetIntLoose(applied, "EffectiveSteps");
        if (effectiveSteps.HasValue)
        {
            AddLabeledValue(multiplicative, prefixLabel, TranslateField(eventType, "detail", "mult.effective_steps", "effective_steps"), effectiveSteps.Value.ToString(CultureInfo.InvariantCulture));
            AddLabeledValue(multiplicative, prefixLabel, TranslateField(eventType, "detail", "mult.step", "step"), AppliedMultipliers.Step.ToString(CultureInfo.InvariantCulture));
        }

        var effectiveMultiplier = TryGetDecimalLoose(applied, "Effective");
        if (!effectiveMultiplier.HasValue && effectiveSteps.HasValue)
        {
            effectiveMultiplier = effectiveSteps.Value * AppliedMultipliers.Step;
        }
        if (effectiveMultiplier.HasValue)
        {
            AddLabeledValue(multiplicative, prefixLabel, TranslateField(eventType, "detail", "mult.effective_multiplier", "effective_multiplier"), FormatDecimal(effectiveMultiplier.Value));
        }

        AddMultiplier(multiplicative, prefixLabel, eventType, applied, "Character", AppliedMultiplierSources.Character, sources, "mult.character_multiplier", "character_multiplier");
        AddMultiplier(multiplicative, prefixLabel, eventType, applied, "Building", AppliedMultiplierSources.Building, sources, "mult.building_multiplier", "building_multiplier");
        AddMultiplier(multiplicative, prefixLabel, eventType, applied, "Event", AppliedMultiplierSources.Event, sources, "mult.event_multiplier", "event_multiplier");
        AddMultiplier(multiplicative, prefixLabel, eventType, applied, "ActionCard", AppliedMultiplierSources.ActionCard, sources, "mult.action_card_multiplier", "action_card_multiplier");
        AddMultiplier(multiplicative, prefixLabel, eventType, applied, "Relic", AppliedMultiplierSources.Relic, sources, "mult.relic_multiplier", "relic_multiplier");
        AddMultiplier(multiplicative, prefixLabel, eventType, applied, "Region", AppliedMultiplierSources.Region, sources, "mult.region_multiplier", "region_multiplier");

        if (sources.HasValue)
        {
            var label = TranslateField(eventType, "detail", "mult.sources", "sources");
            AddLabeledValue(multiplicative, prefixLabel, label, FormatSourcesList(eventType, sources.Value));
        }
    }

    private static void AddStepDelta(
        List<string> additive,
        string prefixLabel,
        string eventType,
        JsonElement applied,
        string propertyName,
        AppliedMultiplierSources sourceFlag,
        int? sourcesMask,
        string labelKey,
        string fallback)
    {
        var value = TryGetIntLoose(applied, propertyName);
        if (!value.HasValue)
        {
            return;
        }

        if (sourcesMask.HasValue)
        {
            if (sourcesMask.Value == 0)
            {
                return;
            }
            if ((sourcesMask.Value & (int)sourceFlag) == 0)
            {
                return;
            }
        }

        if (value.Value == 0)
        {
            return;
        }

        var label = TranslateField(eventType, "detail", labelKey, fallback);
        AddLabeledValue(additive, prefixLabel, label, FormatSignedInt(value.Value));
    }

    private static void AddMultiplier(
        List<string> multiplicative,
        string prefixLabel,
        string eventType,
        JsonElement applied,
        string propertyName,
        AppliedMultiplierSources sourceFlag,
        int? sourcesMask,
        string labelKey,
        string fallback)
    {
        var value = TryGetDecimalLoose(applied, propertyName);
        if (!value.HasValue)
        {
            return;
        }

        if (sourcesMask.HasValue)
        {
            if (sourcesMask.Value == 0)
            {
                return;
            }
            if ((sourcesMask.Value & (int)sourceFlag) == 0)
            {
                return;
            }
        }

        var label = TranslateField(eventType, "detail", labelKey, fallback);
        AddLabeledValue(multiplicative, prefixLabel, label, FormatDecimal(value.Value));
    }

    private static string FormatSourcesList(string eventType, int sources)
    {
        if (sources == 0)
        {
            return TranslateField(eventType, "detail", "mult.source.none", "none");
        }

        var parts = new List<string>(6);
        if ((sources & (int)AppliedMultiplierSources.Character) != 0)
            parts.Add(TranslateField(eventType, "detail", "mult.source.character", "character"));
        if ((sources & (int)AppliedMultiplierSources.Building) != 0)
            parts.Add(TranslateField(eventType, "detail", "mult.source.building", "building"));
        if ((sources & (int)AppliedMultiplierSources.Event) != 0)
            parts.Add(TranslateField(eventType, "detail", "mult.source.event", "event"));
        if ((sources & (int)AppliedMultiplierSources.ActionCard) != 0)
            parts.Add(TranslateField(eventType, "detail", "mult.source.action_card", "action_card"));
        if ((sources & (int)AppliedMultiplierSources.Relic) != 0)
            parts.Add(TranslateField(eventType, "detail", "mult.source.relic", "relic"));
        if ((sources & (int)AppliedMultiplierSources.Region) != 0)
            parts.Add(TranslateField(eventType, "detail", "mult.source.region", "region"));

        return string.Join(", ", parts);
    }

    private static string BuildAppliedMultipliersInline(JsonElement applied)
    {
        var effectiveMultiplier = TryGetDecimalLoose(applied, "Effective");
        var effectiveSteps = TryGetIntLoose(applied, "EffectiveSteps");
        if (!effectiveMultiplier.HasValue && effectiveSteps.HasValue)
        {
            effectiveMultiplier = effectiveSteps.Value * AppliedMultipliers.Step;
        }

        if (!effectiveMultiplier.HasValue)
        {
            return string.Empty;
        }

        return $" mult={FormatDecimal(effectiveMultiplier.Value)}";
    }

    private static bool TryGetAppliedMultipliersElement(JsonElement root, out JsonElement applied)
    {
        if (TryGetPropertyLoose(root, "AppliedMultipliers", out applied) && applied.ValueKind == JsonValueKind.Object)
        {
            return true;
        }

        if (TryGetPropertyLoose(root, "AppliedMultipliersAfter", out applied) && applied.ValueKind == JsonValueKind.Object)
        {
            return true;
        }

        applied = default;
        return false;
    }

    private static void AddLabeledValue(List<string> lines, string prefixLabel, string label, string value)
    {
        if (string.IsNullOrWhiteSpace(prefixLabel))
        {
            lines.Add($"{label}: {value}");
        }
        else
        {
            lines.Add($"{prefixLabel}{label}: {value}");
        }
    }

    private static void AppendSection(StringBuilder sb, string label, List<string> lines)
    {
        if (lines.Count == 0)
        {
            return;
        }

        sb.AppendLine();
        sb.AppendLine($"{label}:");
        foreach (var line in lines)
        {
            sb.AppendLine($"- {line}");
        }
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

    private static string FormatSignedInt(int value)
    {
        if (value == 0) return "0";
        return value > 0 ? $"+{value}" : value.ToString(CultureInfo.InvariantCulture);
    }
}
