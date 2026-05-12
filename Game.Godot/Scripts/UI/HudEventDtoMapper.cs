using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

public static class HudEventDtoMapper
{
    public static bool TryParseGameStarted(JsonElement root, out HudGameStartedDto dto)
    {
        dto = new HudGameStartedDto(
            new Dictionary<string, string>(StringComparer.Ordinal),
            Array.Empty<string>(),
            0,
            0,
            string.Empty,
            string.Empty,
            string.Empty,
            string.Empty,
            string.Empty);

        if (!root.TryGetProperty("game_start_config", out var configElement) || configElement.ValueKind != JsonValueKind.Object)
        {
            return false;
        }

        var assignments = new Dictionary<string, string>(StringComparer.Ordinal);
        if (configElement.TryGetProperty("character_assignments", out var assignmentsElement)
            && assignmentsElement.ValueKind == JsonValueKind.Object)
        {
            foreach (var property in assignmentsElement.EnumerateObject())
            {
                var playerId = property.Name ?? string.Empty;
                var characterId = property.Value.ValueKind == JsonValueKind.String
                    ? (property.Value.GetString() ?? string.Empty)
                    : string.Empty;

                if (string.IsNullOrWhiteSpace(playerId) || string.IsNullOrWhiteSpace(characterId))
                {
                    continue;
                }

                assignments[playerId] = characterId;
            }
        }

        var playersCount = TryGetInt(configElement, "players_count", out var parsedCount) ? parsedCount : assignments.Count;
        var startingMoney = TryGetInt(configElement, "starting_money_preset", out var parsedMoney) ? parsedMoney : 0;
        var commanderId = TryGetString(configElement, "commander_id", out var parsedCommanderId) ? parsedCommanderId : string.Empty;
        var activeStrategemId = TryGetString(configElement, "active_strategem_id", out var parsedActiveStrategemId) ? parsedActiveStrategemId : string.Empty;
        var passiveStrategemId = TryGetString(configElement, "passive_strategem_id", out var parsedPassiveStrategemId) ? parsedPassiveStrategemId : string.Empty;
        var difficultyCode = TryGetString(configElement, "difficulty", out var parsedDifficultyCode) ? parsedDifficultyCode : string.Empty;
        var runMode = TryGetString(configElement, "run_mode", out var parsedRunMode) ? parsedRunMode : string.Empty;
        var playerIds = new List<string>(assignments.Keys);
        playerIds.Sort(StringComparer.Ordinal);
        if (playerIds.Count == 0 && playersCount > 0)
        {
            for (var i = 1; i <= playersCount; i++)
            {
                playerIds.Add($"p{i}");
            }
        }

        dto = new HudGameStartedDto(
            assignments,
            playerIds,
            playersCount,
            startingMoney,
            commanderId,
            activeStrategemId,
            passiveStrategemId,
            difficultyCode,
            runMode);
        return true;
    }

    public static bool TryParseBossChallengePrompted(JsonElement root, out HudBossChallengePromptedDto dto)
    {
        dto = default;
        if (!TryGetRequiredString(root, "BossId", out var bossId))
        {
            return false;
        }

        var roundNumber = TryGetInt(root, "RoundNumber", out var parsedRoundNumber) ? parsedRoundNumber : 0;
        var mapCycleNumber = TryGetInt(root, "MapCycleNumber", out var parsedMapCycleNumber) ? parsedMapCycleNumber : roundNumber;
        var pressureForecast = TryGetInt(root, "NextRoundPressureForecast", out var parsedPressureForecast) ? parsedPressureForecast : 0;

        dto = new HudBossChallengePromptedDto(bossId, roundNumber, mapCycleNumber, pressureForecast);
        return true;
    }

    public static bool TryParseObjectiveSkipped(JsonElement root, out HudObjectiveSkippedDto dto)
    {
        dto = default;
        if (!TryGetRequiredString(root, "ObjectiveId", out var objectiveId))
        {
            return false;
        }

        if (!TryGetRequiredString(root, "Reason", out var reason))
        {
            return false;
        }

        var bossId = TryGetString(root, "BossId", out var parsedBossId) ? parsedBossId : string.Empty;
        var roundNumber = TryGetInt(root, "RoundNumber", out var parsedRound) ? parsedRound : 0;
        var mapCycleNumber = TryGetInt(root, "MapCycleNumber", out var parsedMapCycleNumber) ? parsedMapCycleNumber : roundNumber;

        dto = new HudObjectiveSkippedDto(objectiveId, reason, bossId, roundNumber, mapCycleNumber);
        return true;
    }

    public static bool TryParseScore(JsonElement root, out HudScoreDto dto)
    {
        var value = 0;
        if (TryGetInt(root, "value", out var parsedValue))
        {
            value = parsedValue;
        }
        else if (TryGetInt(root, "score", out parsedValue))
        {
            value = parsedValue;
        }

        dto = new HudScoreDto(value);
        return true;
    }

    public static bool TryParseHealth(JsonElement root, out HudHealthDto dto)
    {
        var value = 0;
        if (TryGetInt(root, "value", out var parsedValue))
        {
            value = parsedValue;
        }
        else if (TryGetInt(root, "health", out parsedValue))
        {
            value = parsedValue;
        }

        dto = new HudHealthDto(value);
        return true;
    }

    public static bool TryParseTurn(JsonElement root, out HudTurnDto dto)
    {
        var activePlayerId = string.Empty;
        if (TryGetString(root, "ActivePlayerId", out var activeValue))
        {
            activePlayerId = activeValue;
        }

        var year = TryGetInt(root, "Year", out var parsedYear) ? parsedYear : 0;
        var month = TryGetInt(root, "Month", out var parsedMonth) ? parsedMonth : 0;
        var day = TryGetInt(root, "Day", out var parsedDay) ? parsedDay : 0;

        dto = new HudTurnDto(activePlayerId, year, month, day);
        return true;
    }

    public static bool TryParsePlayerStateChanged(JsonElement root, out HudPlayerStateDto dto)
    {
        dto = default;

        if (!TryGetRequiredString(root, "PlayerId", out var playerId))
        {
            return false;
        }

        if (!TryGetDecimal(root, "Money", out var money))
        {
            return false;
        }

        var positionIndex = TryGetInt(root, "PositionIndex", out var parsedIndex) ? parsedIndex : -1;
        dto = new HudPlayerStateDto(playerId, money, positionIndex);
        return true;
    }

    public static bool TryParseDiceRolled(JsonElement root, out HudDiceRolledDto dto)
    {
        var playerId = string.Empty;
        if (TryGetString(root, "PlayerId", out var parsedPlayerId))
        {
            playerId = parsedPlayerId;
        }

        var value = 0;
        if (TryGetInt(root, "Value", out var parsedValue))
        {
            value = parsedValue;
        }
        else if (TryGetInt(root, "value", out parsedValue))
        {
            value = parsedValue;
        }

        dto = new HudDiceRolledDto(playerId, value);
        return true;
    }

    public static bool TryParseCityTollPaid(JsonElement root, out HudCityTollPaidDto dto)
    {
        var overflow = TryGetDecimal(root, "TreasuryOverflow", out var parsedOverflow) ? parsedOverflow : 0m;
        var payerId = TryGetString(root, "PayerId", out var parsedPayer) ? parsedPayer : null;
        var ownerId = TryGetString(root, "OwnerId", out var parsedOwner) ? parsedOwner : null;
        var cityId = TryGetString(root, "CityId", out var parsedCity) ? parsedCity : null;
        dto = new HudCityTollPaidDto(overflow, payerId, ownerId, cityId);
        return true;
    }

    public static bool TryParseCityBought(JsonElement root, out HudCityBoughtDto dto)
    {
        dto = default;
        if (!TryGetRequiredString(root, "BuyerId", out var buyerId))
        {
            return false;
        }

        if (!TryGetRequiredString(root, "CityId", out var cityId))
        {
            return false;
        }

        dto = new HudCityBoughtDto(buyerId, cityId);
        return true;
    }

    public static bool TryParseTokenMoved(JsonElement root, out HudTokenMovedDto dto)
    {
        dto = default;
        if (!TryGetRequiredString(root, "PlayerId", out var playerId))
        {
            return false;
        }

        if (!TryGetInt(root, "ToIndex", out var toIndex) || toIndex < 0)
        {
            return false;
        }

        var correlationId = TryGetString(root, "CorrelationId", out var parsedCorrelation)
            ? parsedCorrelation
            : string.Empty;

        dto = new HudTokenMovedDto(playerId, toIndex, correlationId);
        return true;
    }

    private static bool TryGetString(JsonElement root, string propertyName, out string value)
    {
        value = string.Empty;
        if (!root.TryGetProperty(propertyName, out var property) || property.ValueKind != JsonValueKind.String)
        {
            return false;
        }

        value = property.GetString() ?? string.Empty;
        return true;
    }

    private static bool TryGetRequiredString(JsonElement root, string propertyName, out string value)
    {
        if (!TryGetString(root, propertyName, out value))
        {
            return false;
        }

        return !string.IsNullOrWhiteSpace(value);
    }

    private static bool TryGetInt(JsonElement root, string propertyName, out int value)
    {
        value = 0;
        if (!root.TryGetProperty(propertyName, out var property) || property.ValueKind != JsonValueKind.Number)
        {
            return false;
        }

        return property.TryGetInt32(out value);
    }

    private static bool TryGetDecimal(JsonElement root, string propertyName, out decimal value)
    {
        value = 0m;
        if (!root.TryGetProperty(propertyName, out var property) || property.ValueKind != JsonValueKind.Number)
        {
            return false;
        }

        if (property.TryGetDecimal(out var parsed))
        {
            value = parsed;
            return true;
        }

        value = property.GetInt64();
        return true;
    }
}
