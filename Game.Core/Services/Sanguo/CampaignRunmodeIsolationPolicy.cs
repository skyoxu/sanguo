using System;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// T85 split scope policy:
/// isolate only campaign runmode and keep non-campaign behavior untouched.
/// </summary>
public static class CampaignRunmodeIsolationPolicy
{
    public const string CampaignRunmode = "campaign";
    public const string SplitScopeR1 = "R1-Isolation";

    public static CampaignRunmodeIsolationOutcome Evaluate(string? runmode, bool requestIsolation)
    {
        return Evaluate(runmode, requestIsolation, parentResponsibilityProbe: null);
    }

    public static CampaignRunmodeIsolationOutcome Evaluate(
        string? runmode,
        bool requestIsolation,
        Func<bool>? parentResponsibilityProbe)
    {
        var isCampaign = string.Equals((runmode ?? string.Empty).Trim(), CampaignRunmode, StringComparison.OrdinalIgnoreCase);
        var campaignIsolationApplied = isCampaign && requestIsolation;
        _ = parentResponsibilityProbe;

        // T85 only owns campaign isolation; non-campaign paths are explicitly not isolated.
        return new CampaignRunmodeIsolationOutcome(
            CampaignIsolationApplied: campaignIsolationApplied,
            NonCampaignIsolationApplied: false,
            SplitScope: SplitScopeR1,
            DependsOnParentResponsibilities: false);
    }
}

public sealed record CampaignRunmodeIsolationOutcome(
    bool CampaignIsolationApplied,
    bool NonCampaignIsolationApplied,
    string SplitScope,
    bool DependsOnParentResponsibilities);
