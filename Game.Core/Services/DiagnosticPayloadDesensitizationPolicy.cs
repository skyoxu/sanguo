using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

namespace Game.Core.Services;

/// <summary>
/// Applies build-mode aware desensitization to diagnostic payload fields.
/// </summary>
public static class DiagnosticPayloadDesensitizationPolicy
{
    private static readonly string[] SensitiveKeyTokens =
    {
        "token",
        "secret",
        "password",
        "authorization",
        "trace",
        "path",
        "payload",
        "raw",
        "diagnostic",
    };

    public static IReadOnlyDictionary<string, string> Apply(string buildMode, IReadOnlyDictionary<string, string> payload)
    {
        ArgumentNullException.ThrowIfNull(payload);

        var exposeRaw = I18nMissingKeyExposurePolicy.AllowsDiagnosticRawKeyExposure(buildMode);
        var output = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var key in payload.Keys.OrderBy(static x => x, StringComparer.Ordinal))
        {
            payload.TryGetValue(key, out var value);
            var safeValue = value ?? string.Empty;
            output[key] = !exposeRaw && IsSensitiveKey(key)
                ? MaskValueDeterministically(safeValue)
                : safeValue;
        }

        return output;
    }

    private static bool IsSensitiveKey(string key)
    {
        if (string.IsNullOrWhiteSpace(key))
        {
            return false;
        }

        var lowered = key.Trim().ToLowerInvariant();
        return SensitiveKeyTokens.Any(lowered.Contains);
    }

    private static string MaskValueDeterministically(string value)
    {
        if (string.IsNullOrEmpty(value))
        {
            return string.Empty;
        }

        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(value));
        var token = Convert.ToHexString(hash.AsSpan(0, 6)).ToLowerInvariant();
        return $"[masked:{token}]";
    }
}

