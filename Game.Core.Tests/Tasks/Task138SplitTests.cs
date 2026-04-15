using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task138SplitTests
{
    // ACC:T138.1
    [Fact]
    public void ShouldPublishDeterministicBlockedReason_WhenSkipEligibilityIsRuleBlocked()
    {
        var module = new EventTileAutoTriggerEnforcementModule();

        module.SetSkipEligibility(isEligible: false, blockedReason: "boss-action-pending");
        var rejectedByRule = module.EvaluateSkip();

        rejectedByRule.IsAllowed.Should().BeFalse("rule-blocked scenarios must reject skip");
        rejectedByRule.BlockedReason.Should().Be("boss-action-pending");
        module.LastSkipBlockedReason.Should().Be("boss-action-pending");

        module.SetSkipEligibility(isEligible: true);
        var allowedByRule = module.EvaluateSkip();

        allowedByRule.IsAllowed.Should().BeTrue("eligible scenarios must allow skip");
        allowedByRule.BlockedReason.Should().BeNull();
        module.LastSkipBlockedReason.Should().BeNull();
    }

    // ACC:T138.2
    [Fact]
    public void ShouldRejectSkipWithMandatoryEventResolutionReason_WhenEventResolutionIsActive()
    {
        var module = new EventTileAutoTriggerEnforcementModule();

        module.SetSkipEligibility(isEligible: true);
        module.OnPlayerLanded(EventTileType.Event);

        var decision = module.EvaluateSkip();

        decision.IsAllowed.Should().BeFalse();
        decision.BlockedReason.Should().Be(EventTileAutoTriggerEnforcementModule.SkipBlockedReasonMandatoryEventResolutionActive);
        module.LastSkipBlockedReason.Should().Be(EventTileAutoTriggerEnforcementModule.SkipBlockedReasonMandatoryEventResolutionActive);
    }
}
