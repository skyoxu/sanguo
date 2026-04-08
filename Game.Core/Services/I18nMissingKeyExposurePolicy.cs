using System;

namespace Game.Core.Services;

/// <summary>
/// Build-mode dependent missing-key policy.
/// release: hide raw key and return friendly fallback.
/// dev/debug/editor: allow raw key for diagnostics.
/// </summary>
public static class I18nMissingKeyExposurePolicy
{
    public const string DefaultFriendlyFallback = "Explanation is temporarily unavailable.";

    public static string ResolveForBuildMode(string buildMode, string key, string friendlyFallback = DefaultFriendlyFallback)
    {
        if (string.IsNullOrWhiteSpace(key))
        {
            return string.Empty;
        }

        if (AllowsDiagnosticRawKeyExposure(buildMode))
        {
            return key;
        }

        return string.IsNullOrWhiteSpace(friendlyFallback) ? DefaultFriendlyFallback : friendlyFallback;
    }

    public static bool AllowsDiagnosticRawKeyExposure(string buildMode)
    {
        var normalized = (buildMode ?? string.Empty).Trim();
        return normalized.Equals("dev", StringComparison.OrdinalIgnoreCase)
               || normalized.Equals("debug", StringComparison.OrdinalIgnoreCase)
               || normalized.Equals("editor", StringComparison.OrdinalIgnoreCase);
    }
}
