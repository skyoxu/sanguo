using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Game.Core.Services;

public static class LoggingGuidelinesGate
{
    public static LoggingGuidelinesGateReport Validate(string documentation, string configurationJson)
    {
        var missingRequirements = new List<string>();
        var checks = new List<LoggingGuidelinesGateCheck>
        {
            new("documentation", "structured-logging"),
            new("documentation", "redaction-rules"),
            new("documentation", "traceability-fields"),
            new("configuration", "baseline-path"),
            new("configuration", "redaction-rules"),
            new("configuration", "traceability-fields"),
        };

        if (!Contains(documentation, "structured logging"))
        {
            missingRequirements.Add("doc:structured-logging");
        }

        if (!Contains(documentation, "redaction rules"))
        {
            missingRequirements.Add("doc:redaction-rules");
        }

        if (!Contains(documentation, "traceability fields")
            || !Contains(documentation, "traceId")
            || !Contains(documentation, "spanId")
            || !Contains(documentation, "taskId"))
        {
            missingRequirements.Add("doc:traceability-fields");
        }

        if (!TryReadConfigObject(configurationJson, out var config))
        {
            missingRequirements.Add("config:baseline-path");
            missingRequirements.Add("config:redaction-rules");
            missingRequirements.Add("config:traceability-fields");
            return new LoggingGuidelinesGateReport(
                isSuccess: false,
                missingRequirements: missingRequirements,
                checks: checks);
        }

        if (!TryReadNonEmptyString(config, "loggingGuidelinesBaseline", out _))
        {
            missingRequirements.Add("config:baseline-path");
        }

        if (!ContainsAllArrayValues(config, "redactionRules", "email", "token"))
        {
            missingRequirements.Add("config:redaction-rules");
        }

        if (!ContainsAllArrayValues(config, "traceabilityFields", "traceId", "spanId", "taskId"))
        {
            missingRequirements.Add("config:traceability-fields");
        }

        return new LoggingGuidelinesGateReport(
            isSuccess: missingRequirements.Count == 0,
            missingRequirements: missingRequirements,
            checks: checks);
    }

    private static bool TryReadConfigObject(string json, out JsonElement config)
    {
        config = default;
        try
        {
            using var doc = JsonDocument.Parse(json);
            if (doc.RootElement.ValueKind != JsonValueKind.Object)
            {
                return false;
            }

            config = doc.RootElement.Clone();
            return true;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    private static bool TryReadNonEmptyString(JsonElement obj, string key, out string value)
    {
        value = string.Empty;
        if (!obj.TryGetProperty(key, out var property) || property.ValueKind != JsonValueKind.String)
        {
            return false;
        }

        value = property.GetString() ?? string.Empty;
        return !string.IsNullOrWhiteSpace(value);
    }

    private static bool ContainsAllArrayValues(JsonElement obj, string key, params string[] expectedValues)
    {
        if (!obj.TryGetProperty(key, out var property) || property.ValueKind != JsonValueKind.Array)
        {
            return false;
        }

        var values = property
            .EnumerateArray()
            .Where(static item => item.ValueKind == JsonValueKind.String)
            .Select(static item => item.GetString() ?? string.Empty)
            .ToHashSet(StringComparer.OrdinalIgnoreCase);

        return expectedValues.All(values.Contains);
    }

    private static bool Contains(string source, string value)
    {
        return source.IndexOf(value, StringComparison.OrdinalIgnoreCase) >= 0;
    }
}

public sealed class LoggingGuidelinesGateReport
{
    public LoggingGuidelinesGateReport(
        bool isSuccess,
        IReadOnlyList<string> missingRequirements,
        IReadOnlyList<LoggingGuidelinesGateCheck> checks)
    {
        IsSuccess = isSuccess;
        MissingRequirements = missingRequirements;
        Checks = checks;
    }

    public bool IsSuccess { get; }

    public IReadOnlyList<string> MissingRequirements { get; }

    public IReadOnlyList<LoggingGuidelinesGateCheck> Checks { get; }
}

public sealed class LoggingGuidelinesGateCheck
{
    public LoggingGuidelinesGateCheck(string kind, string code)
    {
        Kind = kind;
        Code = code;
    }

    public string Kind { get; }

    public string Code { get; }
}
