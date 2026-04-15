using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task104SplitIntegrationTests
{
    // ACC:T104.1
    [Fact]
    public void ShouldEnterMandatoryEventResolutionAndRejectSkip_WhenLandingOnEventTile()
    {
        var module = new EventTileAutoTriggerEnforcementModule();

        module.OnPlayerLanded(EventTileType.Event);
        var skipDecision = module.EvaluateSkip();

        module.IsAwaitingMandatoryEventResolution.Should().BeTrue("event tile landing must auto-trigger mandatory resolution");
        module.AuditTrail.Should().ContainInOrder("PlayerLanded", "MandatoryEventResolutionEntered");
        skipDecision.IsAllowed.Should().BeFalse("skip must be rejected while mandatory event resolution is active");
        skipDecision.BlockedReason.Should().Be(EventTileAutoTriggerEnforcementModule.SkipBlockedReasonMandatoryEventResolutionActive);
    }

    // ACC:T104.2
    [Fact]
    public void ShouldAllowSkipOnlyAcrossSplitBehavior_WhenNoBlockingRuleIsActive()
    {
        var module = new EventTileAutoTriggerEnforcementModule();

        module.SetSkipEligibility(isEligible: false, blockedReason: "boss-action-pending");
        var ruleBlocked = module.EvaluateSkip();

        module.OnPlayerLanded(EventTileType.Normal);
        module.SetSkipEligibility(isEligible: true);
        var allowed = module.EvaluateSkip();

        ruleBlocked.IsAllowed.Should().BeFalse("split-task guard matrix must keep skip as rule-blocked fallback");
        ruleBlocked.BlockedReason.Should().Be("boss-action-pending");
        allowed.IsAllowed.Should().BeTrue("skip should be allowed only when no blocking rule remains");
        allowed.BlockedReason.Should().BeNull();
    }
}
