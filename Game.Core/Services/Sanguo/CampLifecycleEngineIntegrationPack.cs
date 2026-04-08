using System;
using System.Linq;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Task 75 closure artifact: aggregates split evidence from T87 (R2/R5) and T88 (A-003/A-005).
/// </summary>
public static class CampLifecycleEngineIntegrationPack
{
    public const string SplitScopeT87 = "T87-R2R5-CampLifecycleRules";
    public const string SplitScopeT88 = "T88-A003A005-LeaveCampSaveRetry";

    public static CampLifecycleEngineIntegrationEvidence BuildEvidence(
        Task87SplitEvidence task87Evidence,
        Task88SplitEvidence task88Evidence)
    {
        var task87Delivered = task87Evidence.HasDeterministicEvidence && task87Evidence.CoversR2R5Obligations;
        var task88Delivered = task88Evidence.HasDeterministicEvidence &&
            task88Evidence.CoversA003A005Obligations &&
            task88Evidence.RejectsNonLeaveCampStandIn;

        return EvaluateSplitEvidence(
            hasTask87Evidence: task87Delivered,
            hasTask88Evidence: task88Delivered,
            splitScopes: MergeSplitScopes(task87Evidence.SplitScopes, task88Evidence.SplitScopes));
    }

    public static CampLifecycleEngineIntegrationEvidence EvaluateSplitEvidence(
        bool hasTask87Evidence,
        bool hasTask88Evidence,
        params string[] splitScopes)
    {
        var normalizedScopes = splitScopes
            .Where(scope => !string.IsNullOrWhiteSpace(scope))
            .Select(scope => scope.Trim())
            .Distinct(StringComparer.Ordinal)
            .OrderBy(scope => scope, StringComparer.Ordinal)
            .ToArray();

        return new CampLifecycleEngineIntegrationEvidence(
            Task87Delivered: hasTask87Evidence,
            Task88Delivered: hasTask88Evidence,
            SplitScopes: normalizedScopes);
    }

    private static string[] MergeSplitScopes(string[]? task87SplitScopes, string[]? task88SplitScopes)
    {
        return (task87SplitScopes ?? Array.Empty<string>())
            .Concat(task88SplitScopes ?? Array.Empty<string>())
            .ToArray();
    }
}

public readonly record struct Task87SplitEvidence(
    bool HasDeterministicEvidence,
    bool CoversR2R5Obligations,
    string[] SplitScopes);

public readonly record struct Task88SplitEvidence(
    bool HasDeterministicEvidence,
    bool CoversA003A005Obligations,
    bool RejectsNonLeaveCampStandIn,
    string[] SplitScopes);

public readonly record struct CampLifecycleEngineIntegrationEvidence(
    bool Task87Delivered,
    bool Task88Delivered,
    string[] SplitScopes)
{
    public bool HasScope(string splitScope) =>
        SplitScopes.Any(scope => string.Equals(scope, splitScope, StringComparison.Ordinal));

    public bool IsClosureComplete =>
        Task87Delivered &&
        Task88Delivered &&
        HasScope(CampLifecycleEngineIntegrationPack.SplitScopeT87) &&
        HasScope(CampLifecycleEngineIntegrationPack.SplitScopeT88);
}
