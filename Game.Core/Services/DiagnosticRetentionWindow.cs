using System;
using System.Collections.Generic;
using System.Linq;
using Game.Core.Contracts;

namespace Game.Core.Services;

/// <summary>
/// Applies deterministic retention cleanup for diagnostic domain events.
/// </summary>
public static class DiagnosticRetentionWindow
{
    /// <summary>
    /// Removes diagnostics outside the retention window and keeps the latest bounded set.
    /// </summary>
    public static IReadOnlyList<DomainEvent> Cleanup(
        IReadOnlyList<DomainEvent> diagnostics,
        DateTime settlementUtc,
        TimeSpan retentionWindow,
        int maxRetainedRuns)
    {
        if (diagnostics is null || diagnostics.Count == 0)
        {
            return Array.Empty<DomainEvent>();
        }

        if (retentionWindow < TimeSpan.Zero || maxRetainedRuns <= 0)
        {
            return Array.Empty<DomainEvent>();
        }

        var cutoffUtc = settlementUtc - retentionWindow;
        var inWindow = diagnostics
            .Where(evt => evt.Timestamp >= cutoffUtc)
            .OrderBy(evt => evt.Timestamp)
            .ThenBy(evt => evt.Id, StringComparer.Ordinal)
            .ToList();

        if (inWindow.Count <= maxRetainedRuns)
        {
            return inWindow;
        }

        var skip = inWindow.Count - maxRetainedRuns;
        return inWindow.Skip(skip).ToList();
    }
}
