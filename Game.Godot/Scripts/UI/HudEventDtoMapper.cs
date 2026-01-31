using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

public static class HudEventDtoMapper
{
    public static bool TryParseGameStarted(JsonElement root, out HudGameStartedDto dto)
    {
        dto = new HudGameStartedDto(new Dictionary<string, string>(StringComparer.Ordinal));

        if (!root.TryGetProperty("game_start_config", out var configElement) || configElement.ValueKind != JsonValueKind.Object)
        {
            return false;
        }

        if (!configElement.TryGetProperty("character_assignments", out var assignmentsElement)
            || assignmentsElement.ValueKind != JsonValueKind.Object)
        {
            return false;
        }

        var assignments = new Dictionary<string, string>(StringComparer.Ordinal);
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

        dto = new HudGameStartedDto(assignments);
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
