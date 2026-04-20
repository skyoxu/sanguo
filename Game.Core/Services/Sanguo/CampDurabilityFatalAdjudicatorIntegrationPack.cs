using System;
using System.Linq;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Task 100 closure artifact: aggregates split evidence from T129 (fatal preemption)
/// and T130 (camp-fail settlement routing).
/// </summary>
public static class CampDurabilityFatalAdjudicatorIntegrationPack
{
    public const string SplitScopeT129 = "T129-R3-A001-FatalPreemption";
    public const string SplitScopeT130 = "T130-R3-CampFailSettlementRouting";

    public static CampDurabilityFatalAdjudicatorIntegrationEvidence EvaluateSplitEvidence(
        bool hasTask129Evidence,
        bool hasTask130Evidence,
        bool additionalImplementationRequired,
        params string[] splitScopes)
    {
        var normalizedScopes = splitScopes
            .Where(scope => !string.IsNullOrWhiteSpace(scope))
            .Select(scope => scope.Trim())
            .Distinct(StringComparer.Ordinal)
            .OrderBy(scope => scope, StringComparer.Ordinal)
            .ToArray();

        return new CampDurabilityFatalAdjudicatorIntegrationEvidence(
            Task129Delivered: hasTask129Evidence,
            Task130Delivered: hasTask130Evidence,
            AdditionalImplementationRequired: additionalImplementationRequired,
            SplitScopes: normalizedScopes);
    }
}

public readonly record struct CampDurabilityFatalAdjudicatorIntegrationEvidence(
    bool Task129Delivered,
    bool Task130Delivered,
    bool AdditionalImplementationRequired,
    string[] SplitScopes)
{
    public bool HasScope(string splitScope) =>
        SplitScopes.Any(scope => string.Equals(scope, splitScope, StringComparison.Ordinal));

    public bool IsClosureComplete =>
        Task129Delivered &&
        Task130Delivered &&
        !AdditionalImplementationRequired &&
        HasScope(CampDurabilityFatalAdjudicatorIntegrationPack.SplitScopeT129) &&
        HasScope(CampDurabilityFatalAdjudicatorIntegrationPack.SplitScopeT130);
}
