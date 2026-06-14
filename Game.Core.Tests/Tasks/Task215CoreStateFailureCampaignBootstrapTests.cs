using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task215CoreStateFailureCampaignBootstrapTests
{
    // ACC:T215.4 ACC:T215.5 ACC:T215.6 ACC:T215.7
    [Fact]
    public void ShouldRetryBootstrap_WhenPreviousStartupFailed()
    {
        var failedState = CoreStateFailureCampaignBootstrapState.Failed(
            campaignId: "campaign-1",
            failureCode: "content_pack_missing",
            previousAttempt: 2);
        var input = new CoreStateFailureCampaignBootstrapInput(
            CampaignId: "campaign-1",
            RequestedAction: CoreStateFailureCampaignBootstrapAction.Retry,
            Seed: "seed-215",
            DiceFlowReady: true);

        var first = CoreStateFailureCampaignBootstrapper.Bootstrap(failedState, input);
        var second = CoreStateFailureCampaignBootstrapper.Bootstrap(failedState, input);

        first.Accepted.Should().BeTrue();
        first.ReasonCode.Should().BeEmpty();
        first.State.Phase.Should().Be(CoreStateFailureCampaignBootstrapPhase.Running);
        first.State.Attempt.Should().Be(3);
        first.State.CampaignId.Should().Be("campaign-1");
        first.State.FailureCode.Should().BeEmpty();
        first.State.DiceFlowReady.Should().BeTrue();
        first.StartupOutcome.Should().Be("canonical_startup_path");
        first.EvidenceRefs.Should().Contain("ACC:T215");
        second.Should().BeEquivalentTo(first);
    }

    // ACC:T215.9
    [Fact]
    public void ShouldRefuseInvalidBootstrapInput_WhenInputIsInvalidOrNonApplicable()
    {
        var failedState = CoreStateFailureCampaignBootstrapState.Failed(
            campaignId: "campaign-1",
            failureCode: "content_pack_missing",
            previousAttempt: 4);
        var invalidInput = new CoreStateFailureCampaignBootstrapInput(
            CampaignId: "",
            RequestedAction: CoreStateFailureCampaignBootstrapAction.Retry,
            Seed: "seed-215",
            DiceFlowReady: true);

        var result = CoreStateFailureCampaignBootstrapper.Bootstrap(failedState, invalidInput);

        result.Accepted.Should().BeFalse();
        result.ReasonCode.Should().Be(CoreStateFailureCampaignBootstrapper.InvalidInputReason);
        result.StartupOutcome.Should().Be("startup_failure_refused");
        result.State.Should().Be(failedState);
    }

    // ACC:T215.8
    [Fact]
    public void ShouldRemainPureCore_WhenBootstrapEvidenceIsExposed()
    {
        var state = CoreStateFailureCampaignBootstrapState.Failed(
            campaignId: "campaign-1",
            failureCode: "timeout",
            previousAttempt: 0);
        var input = new CoreStateFailureCampaignBootstrapInput(
            CampaignId: "campaign-1",
            RequestedAction: CoreStateFailureCampaignBootstrapAction.EnterRun,
            Seed: "seed-215",
            DiceFlowReady: true);

        var result = CoreStateFailureCampaignBootstrapper.Bootstrap(state, input);

        typeof(CoreStateFailureCampaignBootstrapper).Assembly.GetReferencedAssemblies()
            .Should().NotContain(assembly => assembly.Name == "GodotSharp" || assembly.Name == "GodotSharpEditor");
        result.Accepted.Should().BeTrue();
        result.EvidenceRefs.Should().Contain("ACC:T215");
        result.State.Phase.Should().Be(CoreStateFailureCampaignBootstrapPhase.Running);
    }
}
