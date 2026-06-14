using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task217CampaignRunmodeIsolationTests
{
    // ACC:T217.1 ACC:T217.2 ACC:T217.3 ACC:T217.4 ACC:T217.5 ACC:T217.6 ACC:T217.7 ACC:T217.8 ACC:T217.9 ACC:T217.10 ACC:T217.11 ACC:T217.12 ACC:T217.13 ACC:T217.14 ACC:T217.15
    [Fact]
    public void ShouldApplyIsolationOnlyToCampaignRunmode_WhenFailureStateIsolationIsRequested()
    {
        var campaignOutcome = CampaignRunmodeIsolationPolicy.Evaluate("campaign", requestIsolation: true);
        var nonCampaignOutcome = CampaignRunmodeIsolationPolicy.Evaluate("classic", requestIsolation: true);
        var skippedCampaignOutcome = CampaignRunmodeIsolationPolicy.Evaluate("campaign", requestIsolation: false);

        campaignOutcome.CampaignIsolationApplied.Should().BeTrue();
        campaignOutcome.NonCampaignIsolationApplied.Should().BeFalse();
        campaignOutcome.SplitScope.Should().Be(CampaignRunmodeIsolationPolicy.SplitScopeR1);
        campaignOutcome.DependsOnParentResponsibilities.Should().BeFalse();

        nonCampaignOutcome.CampaignIsolationApplied.Should().BeFalse();
        nonCampaignOutcome.NonCampaignIsolationApplied.Should().BeFalse();
        nonCampaignOutcome.SplitScope.Should().Be(CampaignRunmodeIsolationPolicy.SplitScopeR1);
        nonCampaignOutcome.DependsOnParentResponsibilities.Should().BeFalse();

        skippedCampaignOutcome.CampaignIsolationApplied.Should().BeFalse();
        skippedCampaignOutcome.NonCampaignIsolationApplied.Should().BeFalse();
        skippedCampaignOutcome.SplitScope.Should().Be(CampaignRunmodeIsolationPolicy.SplitScopeR1);
        skippedCampaignOutcome.DependsOnParentResponsibilities.Should().BeFalse();

        typeof(CampaignRunmodeIsolationPolicy).Assembly.GetReferencedAssemblies()
            .Should().NotContain(assembly => assembly.Name == "GodotSharp" || assembly.Name == "GodotSharpEditor");
    }
}
