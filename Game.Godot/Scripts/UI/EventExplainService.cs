using Game.Core.Contracts.Sanguo;
using Godot;
using Game.Core.Services;
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
        Func<int, string?>? tileLabelByIndex = null,
        Func<string, string?>? tileLabelById = null,
        Func<string, string?>? regionLabelById = null,
        Func<string, string?>? cardLabelById = null,
        Func<string, string?>? relicLabelById = null,
        Func<string, string?>? eventLabelById = null,
        Func<string, string?>? eventPoolLabelById = null)
    {
        var correlationId = TryGetStringLoose(root, "CorrelationId");
        var causationId = TryGetStringLoose(root, "CausationId");

        var summary = BuildSummary(
            type,
            root,
            tileLabelById,
            regionLabelById,
            cardLabelById,
            relicLabelById,
            eventLabelById,
            eventPoolLabelById);
        var details = BuildDetails(
            type,
            root,
            tileLabelByIndex,
            tileLabelById,
            regionLabelById,
            cardLabelById,
            relicLabelById,
            eventLabelById,
            eventPoolLabelById,
            source,
            eventId,
            timestampIso,
            correlationId,
            causationId);

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

    private static string BuildSummary(
        string type,
        JsonElement root,
        Func<string, string?>? tileLabelById,
        Func<string, string?>? regionLabelById,
        Func<string, string?>? cardLabelById,
        Func<string, string?>? relicLabelById,
        Func<string, string?>? eventLabelById,
        Func<string, string?>? eventPoolLabelById)
    {
        var prefix = BuildSummaryPrefix(type);
        var multiplierSuffix = BuildAppliedMultipliersSuffix(type, root);

        if (string.Equals(type, SanguoCityTollPaid.EventType, StringComparison.Ordinal))
        {
            var payerId = TryGetStringLoose(root, "PayerId") ?? string.Empty;
            var ownerId = TryGetStringLoose(root, "OwnerId") ?? string.Empty;
            var cityId = TryGetStringLoose(root, "CityId") ?? string.Empty;
            var amount = TryGetDecimalLoose(root, "Amount");
            var ownerAmount = TryGetDecimalLoose(root, "OwnerAmount");
            var overflow = TryGetDecimalLoose(root, "TreasuryOverflow");
            var cityLabel = ResolveNamedValue(tileLabelById, cityId);

            var parts = new List<string>(8) { prefix };
            AddSummaryPart(parts, type, "payer_id", "payer", payerId);
            AddSummaryPart(parts, type, "owner_id", "owner", ownerId);
            AddSummaryPart(parts, type, "city_id", "city", cityLabel);
            AddSummaryPart(parts, type, "amount", "amount", amount);
            AddSummaryPart(parts, type, "owner_amount", "owner_amount", ownerAmount);
            if (overflow.HasValue && overflow.Value != 0m)
            {
                AddSummaryPart(parts, type, "treasury_overflow", "treasury_overflow", overflow);
            }

            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoMonthSettled.EventType, StringComparison.Ordinal))
        {
            var year = TryGetIntLoose(root, "Year");
            var month = TryGetIntLoose(root, "Month");
            var turn = TryGetIntLoose(root, "TurnNumber");
            var parts = new List<string>(6) { prefix };
            AddSummaryPart(parts, type, "turn", "turn", turn);
            AddSummaryPart(parts, type, "year", "year", year);
            AddSummaryPart(parts, type, "month", "month", month);
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
            AddSummaryPart(parts, type, "player_id", "player", playerId);
            AddSummaryPart(parts, type, "from_index", "from", from);
            AddSummaryPart(parts, type, "to_index", "to", to);
            AddSummaryPart(parts, type, "steps", "steps", steps);
            AddSummaryPart(parts, type, "passed_start", "passed_start", passedStart);
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoGameEnded.EventType, StringComparison.Ordinal))
        {
            var reason = TryGetStringLoose(root, "EndReason");
            var winner = TryGetStringLoose(root, "WinnerPlayerId");
            var parts = new List<string>(6) { prefix };
            var reasonLabel = TranslateTokenValue(type, "end_reason", reason);
            AddSummaryPart(parts, type, "end_reason", "reason", reasonLabel);
            AddSummaryPart(parts, type, "winner_player_id", "winner", winner);
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoAiDecisionMade.EventType, StringComparison.Ordinal))
        {
            var aiPlayerId = TryGetStringLoose(root, "AiPlayerId");
            var decisionType = TryGetStringLoose(root, "DecisionType");
            var reason = TryGetStringLoose(root, "Reason");
            var targetCityId = TryGetStringLoose(root, "TargetCityId");
            var pickedId = TryGetStringLoose(root, "PickedId");
            var decisionLabel = TranslateTokenValue(type, "decision_type", decisionType);
            var targetLabel = ResolveNamedValue(tileLabelById, targetCityId);

            var parts = new List<string>(8) { prefix };
            AddSummaryPart(parts, type, "ai_player_id", "ai", aiPlayerId);
            AddSummaryPart(parts, type, "decision_type", "decision", decisionLabel);
            if (!string.IsNullOrWhiteSpace(reason))
            {
                var label = TranslateField(type, "detail", "reason", "reason");
                var reasonLabel = TranslateReasonToken(type, reason);
                parts.Add($"{label}={reasonLabel}");
            }
            AddSummaryPart(parts, type, "target_city_id", "target", targetLabel);
            AddSummaryPart(parts, type, "picked_id", "picked_id", pickedId);
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoRandomEventApplied.EventType, StringComparison.Ordinal))
        {
            var playerId = TryGetStringLoose(root, "PlayerId");
            var eventId = TryGetStringLoose(root, "EventId");
            var pickedId = TryGetStringLoose(root, "PickedId");
            var effectKind = TryGetStringLoose(root, "EffectKind");
            var uiMessage = TryGetStringLoose(root, "UiMessage");
            var resolvedPickedId = !string.IsNullOrWhiteSpace(pickedId) ? pickedId : eventId;
            var pickedLabelKey = !string.IsNullOrWhiteSpace(pickedId) ? "picked_id" : "event_id";
            var pickedLabelValue = ResolveNamedValue(eventLabelById, resolvedPickedId);
            var sourceLabel = ResolveRandomEventSourceLabel(type, root, resolvedPickedId, eventPoolLabelById);
            var roundNumber = TryGetRoundNumber(root);
            var moneyDelta = TryGetIntLoose(root, "MoneyDelta");
            var stepDelta = TryGetIntLoose(root, "StepDelta");
            var nextStep = ResolveRandomEventNextStepLabel(type, effectKind, root);
            var effectKindLabel = TranslateTokenValue(type, "effect_kind", effectKind);

            var parts = new List<string>(10) { prefix };
            if (!string.IsNullOrWhiteSpace(uiMessage))
            {
                var label = TranslateField(type, "detail", "prompt_message", "message");
                parts.Add($"{label}={uiMessage}");
            }
            AddSummaryPart(parts, type, "player_id", "player", playerId);
            AddSummaryPart(parts, type, pickedLabelKey, pickedLabelKey, pickedLabelValue);
            AddSummaryPart(parts, type, "effect_kind", "kind", effectKindLabel);

            var meta = new List<string>(8);
            if (!string.IsNullOrWhiteSpace(sourceLabel))
            {
                var label = TranslateField(type, "detail", "trigger_source", "source");
                meta.Add($"{label}={sourceLabel}");
            }
            if (roundNumber.HasValue)
            {
                var label = TranslateField(type, "detail", "trigger_round", "round");
                meta.Add($"{label}={roundNumber.Value}");
            }
            if (moneyDelta.HasValue && moneyDelta.Value != 0)
            {
                var label = TranslateField(type, "delta", "money_delta", "money_delta");
                meta.Add($"{label}={FormatSignedInt(moneyDelta.Value)}");
            }
            if (stepDelta.HasValue && stepDelta.Value != 0)
            {
                var label = TranslateField(type, "delta", "step_delta", "step_delta");
                meta.Add($"{label}={FormatSignedInt(stepDelta.Value)}");
            }
            if (!string.IsNullOrWhiteSpace(nextStep))
            {
                var label = TranslateField(type, "detail", "next_step", "next_step");
                meta.Add($"{label}={nextStep}");
            }

            var suffix = meta.Count == 0 ? string.Empty : $" | {string.Join(" | ", meta)}";
            return string.Join(' ', parts) + suffix + multiplierSuffix;
        }

        if (string.Equals(type, SanguoLootGranted.EventType, StringComparison.Ordinal))
        {
            var playerId = TryGetStringLoose(root, "PlayerId");
            var lootKind = TryGetStringLoose(root, "LootKind");
            var moneyDelta = TryGetIntLoose(root, "MoneyDelta");
            var cardId = TryGetStringLoose(root, "CardId");
            var relicId = TryGetStringLoose(root, "RelicId");
            var sourceKind = TryGetStringLoose(root, "SourceKind");
            var sourceId = TryGetStringLoose(root, "SourceId");
            var lootKindLabel = TranslateTokenValue(type, "loot_kind", lootKind);
            var cardLabel = ResolveNamedValue(cardLabelById, cardId);
            var relicLabel = ResolveNamedValue(relicLabelById, relicId);
            var sourceKindLabel = TranslateTokenValue(type, "source_kind", sourceKind);
            var sourceIdLabel = ResolveSourceIdValue(sourceKind, sourceId, cardLabelById, relicLabelById, eventLabelById);

            var parts = new List<string>(10) { prefix };
            AddSummaryPart(parts, type, "player_id", "player", playerId);
            AddSummaryPart(parts, type, "loot_kind", "loot_kind", lootKindLabel);
            AddSummaryPart(parts, type, "card_id", "card", cardLabel);
            AddSummaryPart(parts, type, "relic_id", "relic", relicLabel);

            var meta = new List<string>(6);
            if (moneyDelta.HasValue && moneyDelta.Value != 0)
            {
                var label = TranslateField(type, "delta", "money_delta", "money_delta");
                meta.Add($"{label}={FormatSignedInt(moneyDelta.Value)}");
            }
            if (!string.IsNullOrWhiteSpace(sourceKind))
            {
                var label = TranslateField(type, "detail", "source_kind", "source_kind");
                meta.Add($"{label}={sourceKindLabel}");
            }
            if (!string.IsNullOrWhiteSpace(sourceIdLabel))
            {
                var label = TranslateField(type, "detail", "source_id", "source_id");
                meta.Add($"{label}={sourceIdLabel}");
            }

            var suffix = meta.Count == 0 ? string.Empty : $" | {string.Join(" | ", meta)}";
            return string.Join(' ', parts) + suffix + multiplierSuffix;
        }

        if (string.Equals(type, SanguoRelicApplied.EventType, StringComparison.Ordinal))
        {
            var playerId = TryGetStringLoose(root, "PlayerId");
            var relicId = TryGetStringLoose(root, "RelicId");
            var effectKind = TryGetStringLoose(root, "EffectKind");
            var moneyDelta = TryGetIntLoose(root, "MoneyDelta");
            var stepDelta = TryGetIntLoose(root, "StepDelta");
            var relicLabel = ResolveNamedValue(relicLabelById, relicId);
            var effectKindLabel = TranslateTokenValue(type, "effect_kind", effectKind);

            var parts = new List<string>(8) { prefix };
            AddSummaryPart(parts, type, "player_id", "player", playerId);
            AddSummaryPart(parts, type, "relic_id", "relic", relicLabel);
            AddSummaryPart(parts, type, "effect_kind", "kind", effectKindLabel);

            var meta = new List<string>(4);
            if (moneyDelta.HasValue && moneyDelta.Value != 0)
            {
                var label = TranslateField(type, "delta", "money_delta", "money_delta");
                meta.Add($"{label}={FormatSignedInt(moneyDelta.Value)}");
            }
            if (stepDelta.HasValue && stepDelta.Value != 0)
            {
                var label = TranslateField(type, "delta", "step_delta", "step_delta");
                meta.Add($"{label}={FormatSignedInt(stepDelta.Value)}");
            }

            var suffix = meta.Count == 0 ? string.Empty : $" | {string.Join(" | ", meta)}";
            return string.Join(' ', parts) + suffix + multiplierSuffix;
        }

        if (string.Equals(type, SanguoCardLost.EventType, StringComparison.Ordinal))
        {
            var playerId = TryGetStringLoose(root, "PlayerId");
            var cardId = TryGetStringLoose(root, "CardId");
            var reason = TryGetStringLoose(root, "ReasonCode");
            var sourceKind = TryGetStringLoose(root, "SourceKind");
            var sourceId = TryGetStringLoose(root, "SourceId");
            var cardLabel = ResolveNamedValue(cardLabelById, cardId);
            var sourceKindLabel = TranslateTokenValue(type, "source_kind", sourceKind);
            var sourceIdLabel = ResolveSourceIdValue(sourceKind, sourceId, cardLabelById, relicLabelById, eventLabelById);

            var parts = new List<string>(8) { prefix };
            AddSummaryPart(parts, type, "player_id", "player", playerId);
            AddSummaryPart(parts, type, "card_id", "card", cardLabel);

            var meta = new List<string>(4);
            if (!string.IsNullOrWhiteSpace(reason))
            {
                var label = TranslateField(type, "detail", "reason_code", "reason");
                var translatedReason = TranslateReasonToken(type, reason);
                meta.Add($"{label}={translatedReason}");
            }
            if (!string.IsNullOrWhiteSpace(sourceKind))
            {
                var label = TranslateField(type, "detail", "source_kind", "source_kind");
                meta.Add($"{label}={sourceKindLabel}");
            }
            if (!string.IsNullOrWhiteSpace(sourceIdLabel))
            {
                var label = TranslateField(type, "detail", "source_id", "source_id");
                meta.Add($"{label}={sourceIdLabel}");
            }

            var suffix = meta.Count == 0 ? string.Empty : $" | {string.Join(" | ", meta)}";
            return string.Join(' ', parts) + suffix + multiplierSuffix;
        }

        if (string.Equals(type, SanguoActionCardPlayed.EventType, StringComparison.Ordinal))
        {
            var cardId = TryGetStringLoose(root, "CardId");
            var effectKind = TryGetStringLoose(root, "EffectKind");
            var durationRounds = TryGetIntLoose(root, "DurationRounds");
            var stepDelta = TryGetIntLoose(root, "StepDelta");
            var cardLabel = ResolveNamedValue(cardLabelById, cardId);
            var effectKindLabel = TranslateTokenValue(type, "effect_kind", effectKind);

            var parts = new List<string>(6) { prefix };
            AddSummaryPart(parts, type, "card_id", "card", cardLabel);
            AddSummaryPart(parts, type, "effect_kind", "effect_kind", effectKindLabel);

            var meta = new List<string>(4);
            if (durationRounds.HasValue)
            {
                var label = TranslateField(type, "detail", "duration_rounds", "duration_rounds");
                meta.Add($"{label}={durationRounds.Value}");
            }
            if (stepDelta.HasValue && stepDelta.Value != 0)
            {
                var label = TranslateField(type, "delta", "step_delta", "step_delta");
                meta.Add($"{label}={FormatSignedInt(stepDelta.Value)}");
            }

            var suffix = meta.Count == 0 ? string.Empty : $" | {string.Join(" | ", meta)}";
            return string.Join(' ', parts) + suffix + multiplierSuffix;
        }

        if (string.Equals(type, SanguoCityOwnerChanged.EventType, StringComparison.Ordinal))
        {
            var cityId = TryGetStringLoose(root, "CityId");
            var reason = TryGetStringLoose(root, "ReasonCode");
            var cityLabel = ResolveNamedValue(tileLabelById, cityId);

            var parts = new List<string>(6) { prefix };
            AddSummaryPart(parts, type, "city_id", "city", cityLabel);

            var meta = new List<string>(4);
            if (!string.IsNullOrWhiteSpace(reason))
            {
                var label = TranslateField(type, "detail", "reason_code", "reason");
                var translatedReason = TranslateReasonToken(type, reason);
                meta.Add($"{label}={translatedReason}");
            }

            var suffix = meta.Count == 0 ? string.Empty : $" | {string.Join(" | ", meta)}";
            return string.Join(' ', parts) + suffix + multiplierSuffix;
        }

        if (string.Equals(type, SanguoCombatStarted.EventType, StringComparison.Ordinal))
        {
            var encounterId = TryGetStringLoose(root, "EncounterId");
            var randomSeed = TryGetIntLoose(root, "RandomSeed");

            var parts = new List<string>(6) { prefix };
            AddSummaryPart(parts, type, "encounter_id", "encounter", encounterId);

            var meta = new List<string>(4);
            if (randomSeed.HasValue)
            {
                var label = TranslateField(type, "detail", "random_seed", "random_seed");
                meta.Add($"{label}={randomSeed.Value}");
            }

            var suffix = meta.Count == 0 ? string.Empty : $" | {string.Join(" | ", meta)}";
            return string.Join(' ', parts) + suffix + multiplierSuffix;
        }

        if (string.Equals(type, SanguoCombatEnded.EventType, StringComparison.Ordinal))
        {
            string? outcome = null;
            int? moneyDelta = null;
            if (TryGetPropertyLoose(root, "Result", out var result) && result.ValueKind == JsonValueKind.Object)
            {
                outcome = TryGetStringLoose(result, "Outcome");
                moneyDelta = TryGetIntLoose(result, "MoneyDelta");
            }
            var outcomeLabel = TranslateTokenValue(type, "outcome", outcome);

            var parts = new List<string>(6) { prefix };
            AddSummaryPart(parts, type, "outcome", "outcome", outcomeLabel);

            var meta = new List<string>(4);
            if (moneyDelta.HasValue && moneyDelta.Value != 0)
            {
                var label = TranslateField(type, "delta", "money_delta", "money_delta");
                meta.Add($"{label}={FormatSignedInt(moneyDelta.Value)}");
            }

            var suffix = meta.Count == 0 ? string.Empty : $" | {string.Join(" | ", meta)}";
            return string.Join(' ', parts) + suffix + multiplierSuffix;
        }

        if (string.Equals(type, SanguoGameStarted.EventType, StringComparison.Ordinal))
        {
            var mapId = TryGetStringLoose(root, "MapId");
            var playersCount = TryGetIntLoose(root, "PlayersCount");
            var mapLabel = ResolveNamedValue(id => $"map.{id}.name", mapId);

            var parts = new List<string>(6) { prefix };
            AddSummaryPart(parts, type, "map_id", "map", mapLabel);
            AddSummaryPart(parts, type, "players_count", "players", playersCount);
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoGameTurnStarted.EventType, StringComparison.Ordinal))
        {
            var turn = TryGetIntLoose(root, "TurnNumber");
            var year = TryGetIntLoose(root, "Year");
            var month = TryGetIntLoose(root, "Month");
            var day = TryGetIntLoose(root, "Day");

            var parts = new List<string>(8) { prefix };
            AddSummaryPart(parts, type, "turn", "turn", turn);
            AddSummaryPart(parts, type, "year", "year", year);
            AddSummaryPart(parts, type, "month", "month", month);
            AddSummaryPart(parts, type, "day", "day", day);
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoGameTurnAdvanced.EventType, StringComparison.Ordinal))
        {
            var turn = TryGetIntLoose(root, "TurnNumber");
            var year = TryGetIntLoose(root, "Year");
            var month = TryGetIntLoose(root, "Month");
            var day = TryGetIntLoose(root, "Day");

            var parts = new List<string>(8) { prefix };
            AddSummaryPart(parts, type, "turn", "turn", turn);
            AddSummaryPart(parts, type, "year", "year", year);
            AddSummaryPart(parts, type, "month", "month", month);
            AddSummaryPart(parts, type, "day", "day", day);
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoGameTurnEnded.EventType, StringComparison.Ordinal))
        {
            var turn = TryGetIntLoose(root, "TurnNumber");
            var parts = new List<string>(6) { prefix };
            AddSummaryPart(parts, type, "turn", "turn", turn);
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoGameSaved.EventType, StringComparison.Ordinal))
        {
            var saveSlotId = TryGetStringLoose(root, "SaveSlotId");
            var contentPackId = TryGetStringLoose(root, "ContentPackId");
            var contentPackVersion = TryGetIntLoose(root, "ContentPackVersion");
            var parts = new List<string>(4) { prefix };
            AddSummaryPart(parts, type, "save_slot_id", "save_slot", saveSlotId);
            AddSummaryPart(parts, type, "content_pack_id", "pack", contentPackId);
            AddSummaryPart(parts, type, "content_pack_version", "pack_version", contentPackVersion);
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoGameLoaded.EventType, StringComparison.Ordinal))
        {
            var saveSlotId = TryGetStringLoose(root, "SaveSlotId");
            var contentPackId = TryGetStringLoose(root, "ContentPackId");
            var contentPackVersion = TryGetIntLoose(root, "ContentPackVersion");
            var parts = new List<string>(4) { prefix };
            AddSummaryPart(parts, type, "save_slot_id", "save_slot", saveSlotId);
            AddSummaryPart(parts, type, "content_pack_id", "pack", contentPackId);
            AddSummaryPart(parts, type, "content_pack_version", "pack_version", contentPackVersion);
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoPlayerEliminated.EventType, StringComparison.Ordinal))
        {
            var reason = TryGetStringLoose(root, "ReasonCode");
            var moneyAfter = TryGetDecimalLoose(root, "MoneyAfter");
            var parts = new List<string>(6) { prefix };
            if (!string.IsNullOrWhiteSpace(reason))
            {
                var label = TranslateField(type, "detail", "reason_code", "reason");
                var translatedReason = TranslateReasonToken(type, reason);
                parts.Add($"{label}={translatedReason}");
            }
            if (moneyAfter.HasValue)
            {
                var label = TranslateField(type, "detail", "money_after", "money_after");
                parts.Add($"{label}={FormatDecimal(moneyAfter.Value)}");
            }
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoRegionCaptured.EventType, StringComparison.Ordinal))
        {
            var regionId = TryGetStringLoose(root, "RegionId");
            var ownerId = TryGetStringLoose(root, "OwnerId");
            var reason = TryGetStringLoose(root, "ReasonCode");
            var regionLabel = ResolveNamedValue(regionLabelById, regionId);

            var parts = new List<string>(8) { prefix };
            AddSummaryPart(parts, type, "region_id", "region", regionLabel);
            AddSummaryPart(parts, type, "owner_id", "owner", ownerId);

            var meta = new List<string>(4);
            if (!string.IsNullOrWhiteSpace(reason))
            {
                var label = TranslateField(type, "detail", "reason_code", "reason");
                var translatedReason = TranslateReasonToken(type, reason);
                meta.Add($"{label}={translatedReason}");
            }

            if (TryGetPropertyLoose(root, "CityIds", out var cityIds) && cityIds.ValueKind == JsonValueKind.Array)
            {
                var label = TranslateField(type, "detail", "city_ids_count", "city_ids_count");
                meta.Add($"{label}={cityIds.GetArrayLength()}");
            }

            var suffix = meta.Count == 0 ? string.Empty : $" | {string.Join(" | ", meta)}";
            return string.Join(' ', parts) + suffix + multiplierSuffix;
        }

        if (string.Equals(type, SanguoRegionLost.EventType, StringComparison.Ordinal))
        {
            var regionId = TryGetStringLoose(root, "RegionId");
            var ownerId = TryGetStringLoose(root, "OwnerId");
            var reason = TryGetStringLoose(root, "ReasonCode");
            var regionLabel = ResolveNamedValue(regionLabelById, regionId);

            var parts = new List<string>(8) { prefix };
            AddSummaryPart(parts, type, "region_id", "region", regionLabel);
            AddSummaryPart(parts, type, "owner_id", "owner", ownerId);

            var meta = new List<string>(4);
            if (!string.IsNullOrWhiteSpace(reason))
            {
                var label = TranslateField(type, "detail", "reason_code", "reason");
                var translatedReason = TranslateReasonToken(type, reason);
                meta.Add($"{label}={translatedReason}");
            }
            var triggerCityId = TryGetStringLoose(root, "TriggerCityId");
            var triggerCityLabel = ResolveNamedValue(tileLabelById, triggerCityId);
            if (!string.IsNullOrWhiteSpace(triggerCityLabel))
            {
                var label = TranslateField(type, "detail", "trigger_city_id", "trigger_city_id");
                meta.Add($"{label}={triggerCityLabel}");
            }

            var suffix = meta.Count == 0 ? string.Empty : $" | {string.Join(" | ", meta)}";
            return string.Join(' ', parts) + suffix + multiplierSuffix;
        }

        if (string.Equals(type, SanguoSeasonEventApplied.EventType, StringComparison.Ordinal))
        {
            var year = TryGetIntLoose(root, "Year");
            var season = TryGetIntLoose(root, "Season");
            var yieldMultiplier = TryGetDecimalLoose(root, "YieldMultiplier");

            var parts = new List<string>(6) { prefix };
            AddSummaryPart(parts, type, "year", "year", year);
            AddSummaryPart(parts, type, "season", "season", season);
            AddSummaryPart(parts, type, "yield_multiplier", "yield_multiplier", yieldMultiplier);
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoYearPriceAdjusted.EventType, StringComparison.Ordinal))
        {
            var cityId = TryGetStringLoose(root, "CityId");
            var year = TryGetIntLoose(root, "Year");
            var oldPrice = TryGetDecimalLoose(root, "OldPrice");
            var newPrice = TryGetDecimalLoose(root, "NewPrice");
            var cityLabel = ResolveNamedValue(tileLabelById, cityId);

            var parts = new List<string>(8) { prefix };
            AddSummaryPart(parts, type, "city_id", "city", cityLabel);
            AddSummaryPart(parts, type, "year", "year", year);
            AddSummaryPart(parts, type, "old_price", "old_price", oldPrice);
            AddSummaryPart(parts, type, "new_price", "new_price", newPrice);
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (string.Equals(type, SanguoCityTollSynergyPaid.EventType, StringComparison.Ordinal))
        {
            var payerId = TryGetStringLoose(root, "PayerId");
            var ownerId = TryGetStringLoose(root, "OwnerId");
            var landingCityId = TryGetStringLoose(root, "LandingCityId");
            var regionId = TryGetStringLoose(root, "RegionId");
            var paidTotal = TryGetDecimalLoose(root, "PaidTotalAmount");
            var paidCities = TryGetIntLoose(root, "PaidCitiesCount");
            var landingCityLabel = ResolveNamedValue(tileLabelById, landingCityId);
            var regionLabel = ResolveNamedValue(regionLabelById, regionId);

            var parts = new List<string>(10) { prefix };
            AddSummaryPart(parts, type, "payer_id", "payer", payerId);
            AddSummaryPart(parts, type, "owner_id", "owner", ownerId);
            AddSummaryPart(parts, type, "landing_city_id", "landing_city", landingCityLabel);
            AddSummaryPart(parts, type, "region_id", "region", regionLabel);
            AddSummaryPart(parts, type, "paid_total_amount", "paid_total", paidTotal);
            AddSummaryPart(parts, type, "paid_cities_count", "cities", paidCities);
            return string.Join(' ', parts);
        }

        // Generic fallbacks used by existing tests:
        var playerIdFallback = TryGetStringLoose(root, "PlayerId") ?? TryGetStringLoose(root, "ActivePlayerId");
        if (TryGetPropertyLoose(root, "Value", out var value) && value.ValueKind == JsonValueKind.Number)
        {
            var parts = new List<string>(4) { prefix };
            AddSummaryPart(parts, type, "player_id", "player", playerIdFallback);
            AddSummaryPart(parts, type, "value", "value", value.ToString());
            return string.Join(' ', parts) + multiplierSuffix;
        }

        if (TryGetPropertyLoose(root, "CityId", out var cityIdProp))
        {
            var city = cityIdProp.ValueKind == JsonValueKind.String ? (cityIdProp.GetString() ?? string.Empty) : cityIdProp.ToString();
            var cityLabel = ResolveNamedValue(tileLabelById, city);
            var parts = new List<string>(6) { prefix };
            AddSummaryPart(parts, type, "player_id", "player", playerIdFallback);
            AddSummaryPart(parts, type, "city_id", "city", cityLabel);
            if (TryGetPropertyLoose(root, "Price", out var price) && price.ValueKind == JsonValueKind.Number)
            {
                AddSummaryPart(parts, type, "price", "price", price.ToString());
            }
            return string.Join(' ', parts) + multiplierSuffix;
        }

        var fallbackParts = new List<string>(3) { prefix };
        AddSummaryPart(fallbackParts, type, "player_id", "player", playerIdFallback);
        return string.Join(' ', fallbackParts) + multiplierSuffix;
    }

    private static string BuildDetails(
        string type,
        JsonElement root,
        Func<int, string?>? tileLabelByIndex,
        Func<string, string?>? tileLabelById,
        Func<string, string?>? regionLabelById,
        Func<string, string?>? cardLabelById,
        Func<string, string?>? relicLabelById,
        Func<string, string?>? eventLabelById,
        Func<string, string?>? eventPoolLabelById,
        string source,
        string eventId,
        string timestampIso,
        string? correlationId,
        string? causationId)
    {
        var sb = new StringBuilder(512);
        var typeLabel = TranslateMetaLabel("type", "type");
        sb.AppendLine($"{typeLabel}: {BuildSummaryPrefix(type)}");
        var tsLabel = TranslateMetaLabel("ts", "time");
        sb.AppendLine($"{tsLabel}: {timestampIso}");

        var deltas = new List<string>(8);
        var facts = new List<string>(32);
        var additive = new List<string>(16);
        var multiplicative = new List<string>(16);

        if (string.Equals(type, SanguoCityTollPaid.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "TurnNumber", "turn");
            AddFact(facts, type, root, "CityId", "city_id", tileLabelById);
            AddFact(facts, type, root, "PayerId", "payer_id");
            AddFact(facts, type, root, "OwnerId", "owner_id");

            var amount = TryGetDecimalLoose(root, "Amount");
            var ownerAmount = TryGetDecimalLoose(root, "OwnerAmount");
            var overflow = TryGetDecimalLoose(root, "TreasuryOverflow");

            if (amount.HasValue)
            {
                var payerId = TryGetStringLoose(root, "PayerId") ?? "payer";
                var moneyLabel = TranslateField(type, "delta", "money_delta", "money_delta");
                deltas.Add($"{moneyLabel}[{payerId}]: -{FormatDecimal(amount.Value)}");
            }
            if (ownerAmount.HasValue)
            {
                var ownerId = TryGetStringLoose(root, "OwnerId") ?? "owner";
                var ownerMoneyLabel = TranslateField(type, "delta", "money_delta", "money_delta");
                deltas.Add($"{ownerMoneyLabel}[{ownerId}]: +{FormatDecimal(ownerAmount.Value)}");
            }
            if (overflow.HasValue && overflow.Value != 0m)
            {
                var treasuryLabel = TranslateField(type, "delta", "treasury_delta", "treasury_delta");
                deltas.Add($"{treasuryLabel}: +{FormatDecimal(overflow.Value)}");
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
                        var moneyDeltaLabel = TranslateField(type, "delta", "money_delta", "money_delta");
                        deltas.Add($"{moneyDeltaLabel}[{pid}]: {FormatSignedDecimal(delta.Value)}");
                        count++;
                        if (count >= 12)
                        {
                            var moneyDeltaTruncLabel = TranslateField(type, "delta", "money_delta", "money_delta");
                            deltas.Add($"{moneyDeltaTruncLabel}[...]: (truncated)");
                            break;
                        }
                    }
                }
                var settlementsCountLabel = TranslateField(type, "detail", "player_settlements_count", "player_settlements_count");
                facts.Add($"{settlementsCountLabel}: {settlements.GetArrayLength()}");
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
                    var labelKey = tileLabelByIndex(from.Value);
                    var label = ResolveNameKeyValue(labelKey);
                    if (!string.IsNullOrWhiteSpace(label))
                    {
                        var k = TranslateField(type, "detail", "from_tile", "from_tile");
                        facts.Add($"{k}: {label}");
                    }
                }
                if (to.HasValue)
                {
                    var labelKey = tileLabelByIndex(to.Value);
                    var label = ResolveNameKeyValue(labelKey);
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
            AddFact(facts, type, root, "EndReason", "end_reason", tokenCategory: "end_reason");
            AddFact(facts, type, root, "WinnerPlayerId", "winner_player_id");
        }
        else if (string.Equals(type, SanguoRandomEventApplied.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "PlayerId", "player_id");
            AddFact(facts, type, root, "EventId", "event_id", eventLabelById);
            AddFact(facts, type, root, "PickedId", "picked_id", eventLabelById);
            AddFact(facts, type, root, "EffectKind", "effect_kind", tokenCategory: "effect_kind");
            AddFact(facts, type, root, "EncounterId", "encounter_id");
            AddFact(facts, type, root, "EncounterTarget", "encounter_target");
            AddFact(facts, type, root, "UiMessage", "prompt_message");

            var sourceLabel = ResolveRandomEventSourceLabel(
                type,
                root,
                TryGetStringLoose(root, "PickedId") ?? TryGetStringLoose(root, "EventId"),
                eventPoolLabelById);
            if (!string.IsNullOrWhiteSpace(sourceLabel))
            {
                var label = TranslateField(type, "detail", "trigger_source", "source");
                facts.Add($"{label}: {sourceLabel}");
            }

            var roundNumber = TryGetRoundNumber(root);
            if (roundNumber.HasValue)
            {
                var label = TranslateField(type, "detail", "trigger_round", "round");
                facts.Add($"{label}: {roundNumber.Value}");
            }

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

            var nextStep = ResolveRandomEventNextStepLabel(type, TryGetStringLoose(root, "EffectKind"), root);
            if (!string.IsNullOrWhiteSpace(nextStep))
            {
                var label = TranslateField(type, "detail", "next_step", "next_step");
                facts.Add($"{label}: {nextStep}");
            }

            AddAppliedMultipliersFacts(additive, multiplicative, type, root);
        }
        else if (string.Equals(type, SanguoLootGranted.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "PlayerId", "player_id");
            AddFact(facts, type, root, "LootKind", "loot_kind", tokenCategory: "loot_kind");
            AddFact(facts, type, root, "CardId", "card_id", cardLabelById);
            AddFact(facts, type, root, "RelicId", "relic_id", relicLabelById);
            AddFact(facts, type, root, "SourceKind", "source_kind", tokenCategory: "source_kind");
            AddSourceIdFact(facts, type, root, "SourceId", "source_id", cardLabelById, relicLabelById, eventLabelById);

            var moneyDelta = TryGetIntLoose(root, "MoneyDelta");
            if (moneyDelta.HasValue && moneyDelta.Value != 0)
            {
                var label = TranslateField(type, "delta", "money_delta", "money_delta");
                deltas.Add($"{label}: {FormatSignedInt(moneyDelta.Value)}");
            }
        }
        else if (string.Equals(type, SanguoRelicApplied.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "PlayerId", "player_id");
            AddFact(facts, type, root, "RelicId", "relic_id", relicLabelById);
            AddFact(facts, type, root, "EffectKind", "effect_kind", tokenCategory: "effect_kind");

            var moneyDelta = TryGetIntLoose(root, "MoneyDelta");
            if (moneyDelta.HasValue && moneyDelta.Value != 0)
            {
                var label = TranslateField(type, "delta", "money_delta", "money_delta");
                deltas.Add($"{label}: {FormatSignedInt(moneyDelta.Value)}");
            }
            var stepDelta = TryGetIntLoose(root, "StepDelta");
            if (stepDelta.HasValue && stepDelta.Value != 0)
            {
                var label = TranslateField(type, "delta", "step_delta", "step_delta");
                deltas.Add($"{label}: {FormatSignedInt(stepDelta.Value)}");
            }
        }
        else if (string.Equals(type, SanguoCardLost.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "PlayerId", "player_id");
            AddFact(facts, type, root, "CardId", "card_id", cardLabelById);
            AddFact(facts, type, root, "ReasonCode", "reason_code");
            AddFact(facts, type, root, "SourceKind", "source_kind", tokenCategory: "source_kind");
            AddSourceIdFact(facts, type, root, "SourceId", "source_id", cardLabelById, relicLabelById, eventLabelById);
        }
        else if (string.Equals(type, SanguoActionCardPlayed.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "PlayerId", "player_id");
            AddFact(facts, type, root, "CardId", "card_id", cardLabelById);
            AddFact(facts, type, root, "EffectKind", "effect_kind", tokenCategory: "effect_kind");
            AddFact(facts, type, root, "DurationRounds", "duration_rounds");

            var stepDelta = TryGetIntLoose(root, "StepDelta");
            if (stepDelta.HasValue && stepDelta.Value != 0)
            {
                var label = TranslateField(type, "delta", "step_delta", "step_delta");
                deltas.Add($"{label}: {FormatSignedInt(stepDelta.Value)}");
            }

            if (TryGetPropertyLoose(root, "AppliedMultipliersAfter", out var after) && after.ValueKind == JsonValueKind.Object)
            {
                var prefix = TranslateField(type, "detail", "applied_multipliers_after", "applied_multipliers_after");
                AddAppliedMultipliersFactsFromElement(additive, multiplicative, type, after, prefix);
            }
        }
        else if (string.Equals(type, SanguoCityOwnerChanged.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "TurnNumber", "turn");
            AddFact(facts, type, root, "CityId", "city_id", tileLabelById);
            AddFact(facts, type, root, "OldOwnerId", "old_owner_id");
            AddFact(facts, type, root, "NewOwnerId", "new_owner_id");
            AddFact(facts, type, root, "ReasonCode", "reason_code");
        }
        else if (string.Equals(type, SanguoCombatStarted.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "PlayerId", "player_id");
            AddFact(facts, type, root, "EncounterId", "encounter_id");
            AddFact(facts, type, root, "RandomSeed", "random_seed");
        }
        else if (string.Equals(type, SanguoCombatEnded.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "PlayerId", "player_id");
            AddFact(facts, type, root, "EncounterId", "encounter_id");

            if (TryGetPropertyLoose(root, "Result", out var result) && result.ValueKind == JsonValueKind.Object)
            {
                var outcome = TryGetStringLoose(result, "Outcome");
                if (!string.IsNullOrWhiteSpace(outcome))
                {
                    var label = TranslateField(type, "detail", "outcome", "outcome");
                    var translatedOutcome = TranslateTokenValue(type, "outcome", outcome);
                    facts.Add($"{label}: {translatedOutcome}");
                }

                var moneyDelta = TryGetIntLoose(result, "MoneyDelta");
                if (moneyDelta.HasValue && moneyDelta.Value != 0)
                {
                    var label = TranslateField(type, "delta", "money_delta", "money_delta");
                    deltas.Add($"{label}: {FormatSignedInt(moneyDelta.Value)}");
                }

                var encounterTarget = TryGetIntLoose(result, "EncounterTarget");
                if (encounterTarget.HasValue)
                {
                    var label = TranslateField(type, "detail", "encounter_target", "encounter_target");
                    facts.Add($"{label}: {encounterTarget.Value}");
                }

                var effectiveCombatRating = TryGetIntLoose(result, "EffectiveCombatRating");
                if (effectiveCombatRating.HasValue)
                {
                    var label = TranslateField(type, "detail", "effective_combat_rating", "effective_combat_rating");
                    facts.Add($"{label}: {effectiveCombatRating.Value}");
                }
            }
        }
        else if (string.Equals(type, SanguoGameStarted.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "MapId", "map_id", id => $"map.{id}.name");
            AddFact(facts, type, root, "PlayersCount", "players_count");
            AddFact(facts, type, root, "StartingMoneyPreset", "starting_money_preset");
            AddFact(facts, type, root, "GlobalEventIntervalTurns", "global_event_interval_turns");
            AddFact(facts, type, root, "RandomSeed", "random_seed");
        }
        else if (string.Equals(type, SanguoGameTurnStarted.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "TurnNumber", "turn");
            AddFact(facts, type, root, "ActivePlayerId", "active_player_id");
            AddFact(facts, type, root, "Year", "year");
            AddFact(facts, type, root, "Month", "month");
            AddFact(facts, type, root, "Day", "day");
        }
        else if (string.Equals(type, SanguoGameTurnAdvanced.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "TurnNumber", "turn");
            AddFact(facts, type, root, "ActivePlayerId", "active_player_id");
            AddFact(facts, type, root, "Year", "year");
            AddFact(facts, type, root, "Month", "month");
            AddFact(facts, type, root, "Day", "day");
        }
        else if (string.Equals(type, SanguoGameTurnEnded.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "TurnNumber", "turn");
            AddFact(facts, type, root, "ActivePlayerId", "active_player_id");
            AddFact(facts, type, root, "Year", "year");
            AddFact(facts, type, root, "Month", "month");
            AddFact(facts, type, root, "Day", "day");
        }
        else if (string.Equals(type, SanguoGameSaved.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "SaveSlotId", "save_slot_id");
            AddFact(facts, type, root, "ContentPackId", "content_pack_id");
            AddFact(facts, type, root, "ContentPackVersion", "content_pack_version");
        }
        else if (string.Equals(type, SanguoGameLoaded.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "SaveSlotId", "save_slot_id");
            AddFact(facts, type, root, "ContentPackId", "content_pack_id");
            AddFact(facts, type, root, "ContentPackVersion", "content_pack_version");
        }
        else if (string.Equals(type, SanguoPlayerEliminated.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "TurnNumber", "turn");
            AddFact(facts, type, root, "PlayerId", "player_id");
            AddFact(facts, type, root, "ReasonCode", "reason_code");
            AddFact(facts, type, root, "MoneyBefore", "money_before");
            AddFact(facts, type, root, "MoneyAfter", "money_after");
        }
        else if (string.Equals(type, SanguoRegionCaptured.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "RegionId", "region_id", regionLabelById);
            AddFact(facts, type, root, "OwnerId", "owner_id");
            AddFact(facts, type, root, "ReasonCode", "reason_code");

            if (TryGetPropertyLoose(root, "CityIds", out var cityIds) && cityIds.ValueKind == JsonValueKind.Array)
            {
                var label = TranslateField(type, "detail", "city_ids_count", "city_ids_count");
                facts.Add($"{label}: {cityIds.GetArrayLength()}");
            }
        }
        else if (string.Equals(type, SanguoRegionLost.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "RegionId", "region_id", regionLabelById);
            AddFact(facts, type, root, "OwnerId", "owner_id");
            AddFact(facts, type, root, "ReasonCode", "reason_code");
            AddFact(facts, type, root, "TriggerCityId", "trigger_city_id", tileLabelById);
        }
        else if (string.Equals(type, SanguoSeasonEventApplied.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "TurnNumber", "turn");
            AddFact(facts, type, root, "Year", "year");
            AddFact(facts, type, root, "Season", "season");
            AddFact(facts, type, root, "YieldMultiplier", "yield_multiplier");

            if (TryGetPropertyLoose(root, "AffectedRegionIds", out var regions) && regions.ValueKind == JsonValueKind.Array)
            {
                var label = TranslateField(type, "detail", "affected_regions_count", "affected_regions_count");
                facts.Add($"{label}: {regions.GetArrayLength()}");
            }

            AddAppliedMultipliersFacts(additive, multiplicative, type, root);
        }
        else if (string.Equals(type, SanguoYearPriceAdjusted.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "TurnNumber", "turn");
            AddFact(facts, type, root, "Year", "year");
            AddFact(facts, type, root, "CityId", "city_id", tileLabelById);
            AddFact(facts, type, root, "OldPrice", "old_price");
            AddFact(facts, type, root, "NewPrice", "new_price");

            AddAppliedMultipliersFacts(additive, multiplicative, type, root);
        }
        else if (string.Equals(type, SanguoCityTollSynergyPaid.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "TurnNumber", "turn");
            AddFact(facts, type, root, "PayerId", "payer_id");
            AddFact(facts, type, root, "OwnerId", "owner_id");
            AddFact(facts, type, root, "LandingCityId", "landing_city_id", tileLabelById);
            AddFact(facts, type, root, "RegionId", "region_id", regionLabelById);
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
                    var cityLabel = ResolveNamedValue(tileLabelById, cityId);
                    var amount = TryGetDecimalLoose(item, "Amount");
                    if (amount.HasValue)
                    {
                        var label = TranslateField(type, "detail", "breakdown_amount", "breakdown_amount");
                        facts.Add($"{label}[{cityLabel}]: {FormatDecimal(amount.Value)}");
                    }

                    AddAppliedMultipliersFacts(additive, multiplicative, type, item, $"breakdown[{cityLabel}]");
                }
            }
        }
        else if (string.Equals(type, SanguoAiDecisionMade.EventType, StringComparison.Ordinal))
        {
            AddFact(facts, type, root, "GameId", "game_id");
            AddFact(facts, type, root, "AiPlayerId", "ai_player_id");
            AddFact(facts, type, root, "DecisionType", "decision_type", tokenCategory: "decision_type");
            AddFact(facts, type, root, "DecisionNode", "decision_node");
            AddFact(facts, type, root, "FromState", "from_state");
            AddFact(facts, type, root, "ToState", "to_state");
            AddFact(facts, type, root, "TargetCityId", "target_city_id", tileLabelById);
            AddFact(facts, type, root, "RngContextId", "rng_context_id");
            AddFact(facts, type, root, "PickedId", "picked_id");
            AddFact(facts, type, root, "PickedIndex", "picked_index");

            var reason = TryGetStringLoose(root, "Reason");
            if (!string.IsNullOrWhiteSpace(reason))
            {
                var label = TranslateField(type, "detail", "reason", "reason");
                facts.Add($"{label}: {TranslateReasonToken(type, reason)}");
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

        AppendSection(sb, TranslateField(type, "detail", "deltas", "deltas"), deltas);
        AppendSection(sb, TranslateField(type, "detail", "facts", "facts"), facts);
        AppendSection(sb, TranslateField(type, "detail", "mult.additive", "additive"), additive);
        AppendSection(sb, TranslateField(type, "detail", "mult.multiplicative", "multiplicative"), multiplicative);

        return sb.ToString().TrimEnd();
    }

    private static void AddFact(
        List<string> facts,
        string eventType,
        JsonElement root,
        string propertyName,
        string factKey,
        Func<string, string?>? nameKeyResolver = null,
        string? tokenCategory = null)
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
                if (!string.IsNullOrWhiteSpace(s))
                {
                    if (string.Equals(propertyName, "ReasonCode", StringComparison.Ordinal))
                    {
                        var reason = TranslateReasonToken(eventType, s);
                        facts.Add($"{label}: {reason}");
                    }
                    else if (!string.IsNullOrWhiteSpace(tokenCategory))
                    {
                        var token = TranslateTokenValue(eventType, tokenCategory, s);
                        facts.Add($"{label}: {token}");
                    }
                    else if (nameKeyResolver != null)
                    {
                        var namedValue = ResolveNamedValue(nameKeyResolver, s);
                        facts.Add($"{label}: {namedValue}");
                    }
                    else
                    {
                        facts.Add($"{label}: {s}");
                    }
                }
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

    private static string TranslateReasonToken(string eventType, string reason)
    {
        var normalized = reason.Trim();
        if (string.IsNullOrWhiteSpace(normalized))
        {
            return reason;
        }

        var specificKey = $"ui.hud.event.{eventType}.detail.reason_code.{normalized}";
        var specific = TryTranslate(specificKey);
        if (!string.IsNullOrWhiteSpace(specific))
        {
            return specific!;
        }

        var sharedKey = $"ui.hud.event.shared.detail.reason_code.{normalized}";
        var shared = TryTranslate(sharedKey);
        if (!string.IsNullOrWhiteSpace(shared))
        {
            return shared!;
        }

        return reason;
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

    private static string BuildAppliedMultipliersSuffix(string eventType, JsonElement root)
    {
        if (!TryGetAppliedMultipliersElement(root, out var m))
        {
            return string.Empty;
        }

        return BuildAppliedMultipliersInline(eventType, m);
    }

    private static string BuildSummaryPrefix(string type)
    {
        var summary = TryTranslate($"ui.hud.event.{type}.summary");
        if (!string.IsNullOrWhiteSpace(summary))
        {
            return summary!;
        }

        var title = TryTranslate($"ui.hud.event.{type}.title");
        if (!string.IsNullOrWhiteSpace(title))
        {
            return title!;
        }

        return TranslateOrFallback("ui.hud.event.shared.summary.unknown", "event");
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

    private static string TranslateMetaLabel(string key, string fallback)
    {
        var text = TryTranslate($"ui.hud.event.shared.detail.meta.{key}");
        if (!string.IsNullOrWhiteSpace(text))
        {
            return text!;
        }

        return fallback;
    }

    private static string ResolveNameKeyValue(string? nameKey)
    {
        if (string.IsNullOrWhiteSpace(nameKey))
        {
            return string.Empty;
        }

        var translated = TryTranslate(nameKey);
        if (!string.IsNullOrWhiteSpace(translated))
        {
            return translated!;
        }

        return TranslateOrFallback("ui.hud.event.shared.detail.unknown", "unknown");
    }

    private static string? ResolveNamedLabel(Func<string, string?>? resolver, string? id)
    {
        if (resolver == null || string.IsNullOrWhiteSpace(id))
        {
            return null;
        }

        var key = resolver(id);
        if (string.IsNullOrWhiteSpace(key))
        {
            return null;
        }

        return TryTranslate(key);
    }

    private static string ResolveNamedValue(Func<string, string?>? resolver, string? id)
    {
        if (string.IsNullOrWhiteSpace(id))
        {
            return string.Empty;
        }

        if (resolver != null)
        {
            var key = resolver(id);
            if (!string.IsNullOrWhiteSpace(key))
            {
                var translated = TryTranslate(key);
                if (!string.IsNullOrWhiteSpace(translated))
                {
                    return translated!;
                }
            }
        }

        return TranslateOrFallback("ui.hud.event.shared.detail.unknown", "unknown");
    }

    private static string TranslateTokenValue(string eventType, string category, string? token)
    {
        if (string.IsNullOrWhiteSpace(token))
        {
            return string.Empty;
        }

        var normalized = NormalizeTokenKey(token);
        var specificKey = $"ui.hud.event.{eventType}.detail.{category}.{normalized}";
        var specific = TryTranslate(specificKey);
        if (!string.IsNullOrWhiteSpace(specific))
        {
            return specific!;
        }

        var sharedKey = $"ui.hud.event.shared.detail.{category}.{normalized}";
        var shared = TryTranslate(sharedKey);
        if (!string.IsNullOrWhiteSpace(shared))
        {
            return shared!;
        }

        return TranslateOrFallback("ui.hud.event.shared.detail.unknown", "unknown");
    }

    private static string NormalizeTokenKey(string token)
    {
        if (string.IsNullOrWhiteSpace(token))
        {
            return string.Empty;
        }

        var sb = new StringBuilder(token.Length * 2);
        foreach (var ch in token.Trim())
        {
            if (ch == '-' || ch == ' ')
            {
                if (sb.Length > 0 && sb[^1] != '_')
                {
                    sb.Append('_');
                }
                continue;
            }

            if (char.IsUpper(ch))
            {
                if (sb.Length > 0 && sb[^1] != '_')
                {
                    sb.Append('_');
                }
                sb.Append(char.ToLowerInvariant(ch));
                continue;
            }

            sb.Append(char.ToLowerInvariant(ch));
        }

        return sb.ToString();
    }

    private static string ResolveSourceIdValue(
        string? sourceKind,
        string? sourceId,
        Func<string, string?>? cardLabelById,
        Func<string, string?>? relicLabelById,
        Func<string, string?>? eventLabelById)
    {
        if (string.IsNullOrWhiteSpace(sourceId))
        {
            return string.Empty;
        }

        var normalized = NormalizeTokenKey(sourceKind ?? string.Empty);
        return normalized switch
        {
            "action_card" => ResolveNamedValue(cardLabelById, sourceId),
            "relic" => ResolveNamedValue(relicLabelById, sourceId),
            "event" => ResolveNamedValue(eventLabelById, sourceId),
            "event_tile" => ResolveNamedValue(eventLabelById, sourceId),
            _ => TranslateOrFallback("ui.hud.event.shared.detail.unknown", "unknown"),
        };
    }

    private static void AddSourceIdFact(
        List<string> facts,
        string eventType,
        JsonElement root,
        string propertyName,
        string factKey,
        Func<string, string?>? cardLabelById,
        Func<string, string?>? relicLabelById,
        Func<string, string?>? eventLabelById)
    {
        if (!TryGetPropertyLoose(root, propertyName, out var el) || el.ValueKind != JsonValueKind.String)
        {
            return;
        }

        var sourceId = el.GetString();
        if (string.IsNullOrWhiteSpace(sourceId))
        {
            return;
        }

        var sourceKind = TryGetStringLoose(root, "SourceKind");
        var resolved = ResolveSourceIdValue(sourceKind, sourceId, cardLabelById, relicLabelById, eventLabelById);
        if (string.IsNullOrWhiteSpace(resolved))
        {
            return;
        }

        var label = TranslateField(eventType, "detail", factKey, factKey);
        facts.Add($"{label}: {resolved}");
    }

    private static void AddSummaryPart(List<string> parts, string eventType, string fieldKey, string fallback, string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return;
        }

        var label = TranslateField(eventType, "detail", fieldKey, fallback);
        parts.Add($"{label}={value}");
    }

    private static void AddSummaryPart(List<string> parts, string eventType, string fieldKey, string fallback, int? value)
    {
        if (!value.HasValue)
        {
            return;
        }

        AddSummaryPart(parts, eventType, fieldKey, fallback, value.Value.ToString(CultureInfo.InvariantCulture));
    }

    private static void AddSummaryPart(List<string> parts, string eventType, string fieldKey, string fallback, bool? value)
    {
        if (!value.HasValue)
        {
            return;
        }

        AddSummaryPart(parts, eventType, fieldKey, fallback, value.Value.ToString().ToLowerInvariant());
    }

    private static void AddSummaryPart(List<string> parts, string eventType, string fieldKey, string fallback, decimal? value)
    {
        if (!value.HasValue)
        {
            return;
        }

        AddSummaryPart(parts, eventType, fieldKey, fallback, FormatDecimal(value.Value));
    }

    private static string? ResolveRandomEventSourceLabel(
        string eventType,
        JsonElement root,
        string? eventId,
        Func<string, string?>? eventPoolLabelById)
    {
        var token = ResolveRandomEventSourceToken(root, eventId);
        if (string.IsNullOrWhiteSpace(token))
        {
            return null;
        }

        var poolId = string.Equals(token, "global", StringComparison.Ordinal) ? "global" : "default";
        var poolLabel = ResolveNamedLabel(eventPoolLabelById, poolId);
        if (!string.IsNullOrWhiteSpace(poolLabel) && !IsUnknownPlaceholder(poolLabel))
        {
            return poolLabel;
        }

        var key = token == "global" ? "trigger_source.global" : "trigger_source.tile";
        return TranslateField(eventType, "detail", key, token);
    }

    private static string? ResolveRandomEventSourceToken(JsonElement root, string? eventId)
    {
        var triggerSource = TryGetStringLoose(root, "TriggerSource");
        if (!string.IsNullOrWhiteSpace(triggerSource))
        {
            var normalized = triggerSource.Trim().ToLowerInvariant();
            if (string.Equals(normalized, "global", StringComparison.Ordinal))
            {
                return "global";
            }
            if (string.Equals(normalized, "tile", StringComparison.Ordinal))
            {
                return "tile";
            }
        }

        var rngContextId = TryGetStringLoose(root, "RngContextId");
        if (!string.IsNullOrWhiteSpace(rngContextId))
        {
            var parts = rngContextId.Split(':', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
            if (parts.Length > 0)
            {
                var last = parts[^1];
                if (string.Equals(last, "global", StringComparison.OrdinalIgnoreCase))
                {
                    return "global";
                }
                if (string.Equals(last, "tile", StringComparison.OrdinalIgnoreCase))
                {
                    return "tile";
                }
            }
        }

        if (!string.IsNullOrWhiteSpace(eventId) && eventId.StartsWith(SanguoGlobalEventId.PrefixToken, StringComparison.Ordinal))
        {
            return "global";
        }

        return "tile";
    }

    private static int? TryGetRoundNumber(JsonElement root)
    {
        var round = TryGetIntLoose(root, "RoundNumber");
        if (round.HasValue)
        {
            return round;
        }

        var rngContextId = TryGetStringLoose(root, "RngContextId");
        if (string.IsNullOrWhiteSpace(rngContextId))
        {
            return null;
        }

        return TryParseRoundNumberFromRngContext(rngContextId);
    }

    private static int? TryParseRoundNumberFromRngContext(string rngContextId)
    {
        var parts = rngContextId.Split(':', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        for (var i = 0; i < parts.Length - 1; i++)
        {
            if (string.Equals(parts[i], "round", StringComparison.OrdinalIgnoreCase)
                && int.TryParse(parts[i + 1], NumberStyles.Integer, CultureInfo.InvariantCulture, out var round))
            {
                return round;
            }
        }

        if (parts.Length >= 3 && int.TryParse(parts[2], NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed))
        {
            return parsed;
        }

        return null;
    }

    private static string? ResolveRandomEventNextStepLabel(string eventType, string? effectKind, JsonElement root)
    {
        if (string.Equals(effectKind, SanguoEffectKinds.StartCombat, StringComparison.Ordinal))
        {
            return TranslateField(eventType, "detail", "next_step.resolve_combat", "resolve_combat");
        }

        if (TryGetPropertyLoose(root, "EncounterId", out var encounter) && encounter.ValueKind == JsonValueKind.String)
        {
            return TranslateField(eventType, "detail", "next_step.resolve_combat", "resolve_combat");
        }

        if (!string.IsNullOrWhiteSpace(effectKind))
        {
            return TranslateField(eventType, "detail", "next_step.continue", "continue");
        }

        return null;
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

    private static bool IsUnknownPlaceholder(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return true;
        }

        var trimmed = value.Trim();
        var hasMarker = false;
        foreach (var ch in trimmed)
        {
            if (ch == '?' || ch == '？' || ch == '\uFFFD')
            {
                hasMarker = true;
                continue;
            }

            if (char.IsWhiteSpace(ch))
            {
                continue;
            }

            return false;
        }

        return hasMarker;
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

    private static string BuildAppliedMultipliersInline(string eventType, JsonElement applied)
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

        var label = TranslateField(eventType, "detail", "mult.effective_multiplier", "multiplier");
        return $" {label}={FormatDecimal(effectiveMultiplier.Value)}";
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
