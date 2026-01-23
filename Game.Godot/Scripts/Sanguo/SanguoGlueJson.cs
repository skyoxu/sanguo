using System;
using System.Text.Json;

namespace Game.Godot.Scripts.Sanguo;

internal static class SanguoGlueJson
{
    private static readonly JsonDocumentOptions Options = new() { MaxDepth = 32 };

    internal static string? TryExtractAiDecisionType(string dataJson)
    {
        return TryExtractStringProperty(dataJson, "DecisionType");
    }

    internal static string? TryExtractCorrelationId(string dataJson)
    {
        return TryExtractStringProperty(dataJson, "CorrelationId");
    }

    internal static string? TryExtractActivePlayerId(string dataJson)
    {
        return TryExtractStringProperty(dataJson, "ActivePlayerId");
    }

    internal static string? TryExtractPlayerId(string dataJson)
    {
        return TryExtractStringProperty(dataJson, "PlayerId");
    }

    internal static string? TryExtractCardId(string dataJson)
    {
        return TryExtractStringProperty(dataJson, "CardId");
    }

    internal static string? TryExtractAction(string dataJson)
    {
        return TryExtractStringProperty(dataJson, "Action");
    }

    internal static string? TryExtractSaveSlotId(string dataJson)
    {
        return TryExtractStringProperty(dataJson, "SaveSlotId");
    }

    internal static int? TryExtractIntProperty(string dataJson, string propertyName)
    {
        var json = string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson;
        if (json.Length > 65536)
        {
            return null;
        }

        try
        {
            using var doc = JsonDocument.Parse(json, Options);
            if (!doc.RootElement.TryGetProperty(propertyName, out var el))
            {
                return null;
            }

            if (el.ValueKind != JsonValueKind.Number)
            {
                return null;
            }

            return el.TryGetInt32(out var v) ? v : null;
        }
        catch
        {
            return null;
        }
    }

    internal static bool IsAiPlayerId(string? playerId)
    {
        return !string.IsNullOrWhiteSpace(playerId) && playerId.StartsWith("ai-", StringComparison.OrdinalIgnoreCase);
    }

    private static string? TryExtractStringProperty(string dataJson, string propertyName)
    {
        var json = string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson;
        if (json.Length > 65536)
        {
            return null;
        }

        try
        {
            using var doc = JsonDocument.Parse(json, Options);
            if (!doc.RootElement.TryGetProperty(propertyName, out var el) || el.ValueKind != JsonValueKind.String)
            {
                return null;
            }

            var value = el.GetString();
            return string.IsNullOrWhiteSpace(value) ? null : value;
        }
        catch
        {
            return null;
        }
    }
}
