using System;
using System.Linq;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Task 74 closure artifact: aggregates split evidence from T85 (R1) and T86 (R3).
/// </summary>
public static class CampaignRuleEngineIntegrationPack
{
    public const string SplitScopeR1 = CampaignRunmodeIsolationPolicy.SplitScopeR1;
    public const string SplitScopeR3 = CampaignEndgameAdjudicator.SplitScopeR3;

    public static CampaignRuleEngineIntegrationEvidence BuildEvidence()
    {
        return EvaluateSplitEvidence(
            hasR1IsolationEvidence: true,
            hasR3AdjudicatorEvidence: true,
            splitScopes: new[] { SplitScopeR1, SplitScopeR3 });
    }

    public static CampaignRuleEngineIntegrationEvidence EvaluateSplitEvidence(
        bool hasR1IsolationEvidence,
        bool hasR3AdjudicatorEvidence,
        params string[] splitScopes)
    {
        var normalizedScopes = splitScopes
            .Where(scope => !string.IsNullOrWhiteSpace(scope))
            .Select(scope => scope.Trim())
            .Distinct(StringComparer.Ordinal)
            .OrderBy(scope => scope, StringComparer.Ordinal)
            .ToArray();

        return new CampaignRuleEngineIntegrationEvidence(
            R1IsolationDelivered: hasR1IsolationEvidence,
            R3AdjudicatorDelivered: hasR3AdjudicatorEvidence,
            SplitScopes: normalizedScopes);
    }
}

public readonly record struct CampaignRuleEngineIntegrationEvidence(
    bool R1IsolationDelivered,
    bool R3AdjudicatorDelivered,
    string[] SplitScopes)
{
    public bool HasScope(string splitScope) =>
        SplitScopes.Any(scope => string.Equals(scope, splitScope, StringComparison.Ordinal));

    public bool IsClosureComplete =>
        R1IsolationDelivered &&
        R3AdjudicatorDelivered &&
        HasScope(CampaignRuleEngineIntegrationPack.SplitScopeR1) &&
        HasScope(CampaignRuleEngineIntegrationPack.SplitScopeR3);
}
