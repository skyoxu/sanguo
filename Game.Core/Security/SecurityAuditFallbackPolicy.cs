using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

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

    public static void EnforceRotationCapAndBoundedTotalSize(
        IList<string> retainedFallbackPayloads,
        int rotationCapFiles,
        int boundedTotalSizeBytes)
    {
        ArgumentNullException.ThrowIfNull(retainedFallbackPayloads);

        if (rotationCapFiles <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(rotationCapFiles), rotationCapFiles, "Rotation cap must be positive.");
        }

        if (boundedTotalSizeBytes < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(boundedTotalSizeBytes), boundedTotalSizeBytes, "Bounded total size must be non-negative.");
        }

        while (retainedFallbackPayloads.Count > rotationCapFiles)
        {
            retainedFallbackPayloads.RemoveAt(0);
        }

        while (retainedFallbackPayloads.Count > 0 && SumUtf8Bytes(retainedFallbackPayloads) > boundedTotalSizeBytes)
        {
            retainedFallbackPayloads.RemoveAt(0);
        }
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

    private static int SumUtf8Bytes(IEnumerable<string> payloads)
    {
        return payloads.Sum(static payload => Encoding.UTF8.GetByteCount(payload ?? string.Empty));
    }
}
