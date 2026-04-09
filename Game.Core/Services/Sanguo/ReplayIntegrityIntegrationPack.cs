using System;
using System.Linq;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Task 70 closure artifact: integrates replay integrity split evidence from T83 and T84.
/// </summary>
public static class ReplayIntegrityIntegrationPack
{
    public const string SplitScopeT83 = "T83-A013A014-ReplayTrustAndSaveUntrusted";
    public const string SplitScopeT84 = "T84-A015-ReplayMismatchModeTransition";

    public static ReplayIntegrityIntegrationEvidence BuildEvidence(
        Task83ReplayIntegritySplitEvidence task83Evidence,
        Task84ReplayMismatchSplitEvidence task84Evidence)
    {
        var task83Delivered = task83Evidence.HasDeterministicEvidence &&
            task83Evidence.CoversA013A014Semantics;
        var task84Delivered = task84Evidence.HasDeterministicEvidence &&
            task84Evidence.CoversA015Semantics &&
            task84Evidence.EntersDefinedMismatchModeOnTrustFailure;

        return EvaluateSplitEvidence(
            hasTask83Evidence: task83Delivered,
            hasTask84Evidence: task84Delivered,
            splitScopes: MergeSplitScopes(task83Evidence.SplitScopes, task84Evidence.SplitScopes));
    }

    public static ReplayIntegrityIntegrationEvidence EvaluateSplitEvidence(
        bool hasTask83Evidence,
        bool hasTask84Evidence,
        params string[] splitScopes)
    {
        var normalizedScopes = splitScopes
            .Where(scope => !string.IsNullOrWhiteSpace(scope))
            .Select(scope => scope.Trim())
            .Distinct(StringComparer.Ordinal)
            .OrderBy(scope => scope, StringComparer.Ordinal)
            .ToArray();

        return new ReplayIntegrityIntegrationEvidence(
            Task83Delivered: hasTask83Evidence,
            Task84Delivered: hasTask84Evidence,
            SplitScopes: normalizedScopes);
    }

    private static string[] MergeSplitScopes(string[]? task83SplitScopes, string[]? task84SplitScopes)
    {
        return (task83SplitScopes ?? Array.Empty<string>())
            .Concat(task84SplitScopes ?? Array.Empty<string>())
            .ToArray();
    }
}

public readonly record struct Task83ReplayIntegritySplitEvidence(
    bool HasDeterministicEvidence,
    bool CoversA013A014Semantics,
    string[] SplitScopes);

public readonly record struct Task84ReplayMismatchSplitEvidence(
    bool HasDeterministicEvidence,
    bool CoversA015Semantics,
    bool EntersDefinedMismatchModeOnTrustFailure,
    string[] SplitScopes);

public readonly record struct ReplayIntegrityIntegrationEvidence(
    bool Task83Delivered,
    bool Task84Delivered,
    string[] SplitScopes)
{
    public bool HasScope(string splitScope) =>
        SplitScopes.Any(scope => string.Equals(scope, splitScope, StringComparison.Ordinal));

    public bool IsClosureComplete =>
        Task83Delivered &&
        Task84Delivered &&
        HasScope(ReplayIntegrityIntegrationPack.SplitScopeT83) &&
        HasScope(ReplayIntegrityIntegrationPack.SplitScopeT84);
}
