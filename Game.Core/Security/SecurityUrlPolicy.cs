using System;
using System.Collections.Generic;

namespace Game.Core.Security;

public static class SecurityUrlPolicy
{
    public static bool TryValidateExternalUrl(string url, string? allowedHostsCsv, bool allowInsecureDefaults, out string reason)
    {
        reason = "deny";

        if (string.IsNullOrWhiteSpace(url))
        {
            reason = "deny:empty_url";
            return false;
        }

        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri))
        {
            reason = "deny:invalid_url";
            return false;
        }

        if (!string.Equals(uri.Scheme, Uri.UriSchemeHttps, StringComparison.OrdinalIgnoreCase))
        {
            reason = $"deny:scheme_not_allowed:{uri.Scheme}";
            return false;
        }

        var host = uri.Host?.Trim() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(host))
        {
            reason = "deny:missing_host";
            return false;
        }

        var allowList = ParseCsv(allowedHostsCsv);
        if (allowList.Count == 0 && !allowInsecureDefaults)
        {
            reason = "deny:allowlist_not_configured";
            return false;
        }
        if (allowList.Count == 0 && allowInsecureDefaults)
        {
            reason = "allow:insecure_defaults_enabled";
            return true;
        }

        foreach (var allowed in allowList)
        {
            if (IsHostAllowed(host, allowed))
            {
                reason = "allow:https_host_allowlisted";
                return true;
            }
        }

        reason = "deny:host_not_allowlisted";
        return false;
    }

    public static bool TryValidateUrl(string url, string? allowedHostsCsv, bool allowInsecureDefaults, out string reason)
        => TryValidateExternalUrl(url, allowedHostsCsv, allowInsecureDefaults, out reason);

    public static bool TryValidate(string url, string? allowedHostsCsv, bool allowInsecureDefaults, out string reason)
        => TryValidateExternalUrl(url, allowedHostsCsv, allowInsecureDefaults, out reason);

    private static bool IsHostAllowed(string host, string allowed)
    {
        if (string.IsNullOrWhiteSpace(allowed))
        {
            return false;
        }

        if (string.Equals(host, allowed, StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }

        return host.EndsWith("." + allowed, StringComparison.OrdinalIgnoreCase);
    }

    private static List<string> ParseCsv(string? csv)
    {
        var list = new List<string>();
        var s = (csv ?? string.Empty).Trim();
        if (string.IsNullOrWhiteSpace(s))
        {
            return list;
        }

        foreach (var raw in s.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
        {
            var item = (raw ?? string.Empty).Trim().TrimStart('.').TrimEnd('.');
            if (string.IsNullOrWhiteSpace(item))
            {
                continue;
            }

            list.Add(item);
        }

        return list;
    }
}
