using System;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public class Task85SplitTests
{
    // ACC:T85.1
    [Theory]
    [InlineData("campaign", true, true, false)]
    [InlineData("campaign", false, false, false)]
    [InlineData("sandbox", true, false, false)]
    [InlineData("classic", true, false, false)]
    [InlineData("", true, false, false)]
    [InlineData("   ", true, false, false)]
    [InlineData(null, true, false, false)]
    public void ApplyIsolationOnlyForCampaignRunmodeWhenEvaluatingRequestedIsolation(string? runmode, bool requestIsolation, bool expectedCampaignIsolation, bool expectedNonCampaignIsolation)
    {
        var outcome = CampaignRunmodeIsolationPolicy.Evaluate(runmode, requestIsolation);

        outcome.CampaignIsolationApplied.Should().Be(expectedCampaignIsolation);
        outcome.NonCampaignIsolationApplied.Should().Be(expectedNonCampaignIsolation);
    }

    // ACC:T85.2
    [Fact]
    public void ShouldAvoidParentResponsibilityProbe_WhenEvaluatingR1IsolationBoundary()
    {
        var probeCalls = 0;
        Func<bool> parentResponsibilityProbe = () =>
        {
            probeCalls++;
            return true;
        };

        var outcome = CampaignRunmodeIsolationPolicy.Evaluate("campaign", true, parentResponsibilityProbe);

        outcome.SplitScope.Should().Be(CampaignRunmodeIsolationPolicy.SplitScopeR1);
        outcome.DependsOnParentResponsibilities.Should().BeFalse(
            "T85 must be independently shippable and isolated from unsplit parent responsibilities");
        probeCalls.Should().Be(0, "T85 runmode isolation must not depend on unsplit parent responsibilities.");
    }

    // ACC:T85.3
    [Fact]
    public void ShouldProduceSameIsolationOutcome_WhenInputsAndPreconditionsAreIdentical()
    {
        var firstOutcome = CampaignRunmodeIsolationPolicy.Evaluate("campaign", true);
        var secondOutcome = CampaignRunmodeIsolationPolicy.Evaluate("campaign", true);

        secondOutcome.Should().BeEquivalentTo(firstOutcome);
    }
}
