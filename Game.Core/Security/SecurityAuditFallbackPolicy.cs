using System;

namespace Game.Core.Security;

public static class SecurityAuditFallbackPolicy
{
    public static bool TryWriteWithFallback(
        string primarySinkPath,
        string fallbackSinkPath,
        Func<string, bool> tryWrite,
        Action<string>? warningSink = null)
    {
        ArgumentNullException.ThrowIfNull(tryWrite);

        if (TryWrite(primarySinkPath, "primary", tryWrite, warningSink))
        {
            return true;
        }

        warningSink?.Invoke($"Primary audit sink failed; attempting fallback sink: {fallbackSinkPath}");
        return TryWrite(fallbackSinkPath, "fallback", tryWrite, warningSink);
    }

    private static bool TryWrite(
        string sinkPath,
        string sinkName,
        Func<string, bool> tryWrite,
        Action<string>? warningSink)
    {
        if (string.IsNullOrWhiteSpace(sinkPath))
        {
            warningSink?.Invoke($"{sinkName} audit sink path is empty.");
            return false;
        }

        try
        {
            return tryWrite(sinkPath);
        }
        catch (Exception ex)
        {
            warningSink?.Invoke($"{sinkName} audit sink write failed: {ex.Message}");
            return false;
        }
    }
}
