using System;
using System.Collections.Generic;
using System.Linq;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Deterministically aggregates signal-compliance checks into one task-scoped report.
/// </summary>
public sealed class SignalComplianceAggregator
{
    private static readonly string[] RequiredChecks =
    {
        "naming",
        "documentation",
        "lifecycle",
    };

    private static readonly string[] AcceptanceRefs =
    {
        "R11",
        "PH9-B4",
    };

    public IReadOnlyList<SignalComplianceReport> Aggregate(
        string taskId,
        IReadOnlyCollection<SignalComplianceCheckResult> checks)
    {
        if (string.IsNullOrWhiteSpace(taskId))
        {
            throw new ArgumentException("Task id must not be empty.", nameof(taskId));
        }

        if (checks is null)
        {
            throw new ArgumentNullException(nameof(checks));
        }

        var normalizedChecks = checks
            .Where(static item => !string.IsNullOrWhiteSpace(item.CheckName))
            .Select(static item => item with
            {
                CheckName = item.CheckName.Trim(),
                EvidencePath = item.EvidencePath.Trim(),
            })
            .ToArray();

        var passedByCheck = normalizedChecks
            .Where(static item => item.Passed)
            .GroupBy(static item => item.CheckName, StringComparer.Ordinal)
            .ToDictionary(
                static group => group.Key,
                static group => group
                    .Select(static item => item.EvidencePath)
                    .FirstOrDefault(static path => !string.IsNullOrWhiteSpace(path)) ?? string.Empty,
                StringComparer.Ordinal);

        var anyByCheck = normalizedChecks
            .GroupBy(static item => item.CheckName, StringComparer.Ordinal)
            .ToDictionary(
                static group => group.Key,
                static _ => true,
                StringComparer.Ordinal);

        var coveredChecks = RequiredChecks
            .Where(required => passedByCheck.ContainsKey(required))
            .ToArray();

        var evidencePaths = coveredChecks
            .Select(name => passedByCheck[name])
            .Where(static path => !string.IsNullOrWhiteSpace(path))
            .ToArray();

        var missingChecks = RequiredChecks
            .Where(required => !anyByCheck.ContainsKey(required))
            .ToArray();

        var failedChecks = RequiredChecks
            .Where(required => anyByCheck.ContainsKey(required) && !passedByCheck.ContainsKey(required))
            .ToArray();

        var report = new SignalComplianceReport(
            taskId.Trim(),
            coveredChecks,
            evidencePaths,
            AcceptanceRefs,
            missingChecks,
            failedChecks,
            missingChecks.Length == 0 && failedChecks.Length == 0);

        return new[] { report };
    }
}

public sealed record SignalComplianceCheckResult(string CheckName, bool Passed, string EvidencePath);

public sealed record SignalComplianceReport(
    string TaskId,
    IReadOnlyList<string> CoveredChecks,
    IReadOnlyList<string> EvidencePaths,
    IReadOnlyList<string> AcceptanceRefs,
    IReadOnlyList<string> MissingChecks,
    IReadOnlyList<string> FailedChecks,
    bool IsCompliant);
