using System;
using System.Text.Json;

namespace Game.Core.Security;

public static class SecurityAuditJsonlValidator
{
    public static bool TryValidateLine(string jsonlLine, out string reason)
    {
        reason = "deny";

        if (string.IsNullOrWhiteSpace(jsonlLine))
        {
            reason = "deny:empty_line";
            return false;
        }

        try
        {
            using var doc = JsonDocument.Parse(jsonlLine);
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                reason = "deny:not_json_object";
                return false;
            }

            if (!TryGetNonEmptyString(root, "ts", out var ts))
            {
                reason = "deny:missing_field:ts";
                return false;
            }

            if (!TryGetNonEmptyString(root, "action", out _))
            {
                reason = "deny:missing_field:action";
                return false;
            }

            if (!TryGetNonEmptyString(root, "reason", out _))
            {
                reason = "deny:missing_field:reason";
                return false;
            }

            if (!TryGetNonEmptyString(root, "target", out _))
            {
                reason = "deny:missing_field:target";
                return false;
            }

            if (!TryGetNonEmptyString(root, "caller", out _))
            {
                reason = "deny:missing_field:caller";
                return false;
            }

            if (!DateTimeOffset.TryParse(ts, out _))
            {
                reason = "deny:invalid_ts";
                return false;
            }

            reason = "allow:valid_security_audit_jsonl";
            return true;
        }
        catch (JsonException)
        {
            reason = "deny:invalid_json";
            return false;
        }
    }

    public static bool TryValidate(string jsonlLine, out string reason) => TryValidateLine(jsonlLine, out reason);

    private static bool TryGetNonEmptyString(JsonElement obj, string name, out string value)
    {
        value = string.Empty;
        if (!obj.TryGetProperty(name, out var prop))
        {
            return false;
        }

        if (prop.ValueKind != JsonValueKind.String)
        {
            return false;
        }

        value = prop.GetString() ?? string.Empty;
        return !string.IsNullOrWhiteSpace(value);
    }
}

