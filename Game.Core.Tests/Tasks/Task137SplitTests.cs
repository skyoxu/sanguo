using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task137SplitTests
{
    // ACC:T137.1
    [Fact]
    public void ShouldEnterMandatoryEventResolutionImmediately_WhenLandingOnEventTile()
    {
        var module = new EventTileAutoTriggerEnforcementModule();

        module.OnPlayerLanded(EventTileType.Event);

        module.IsAwaitingMandatoryEventResolution.Should().BeTrue("landing on an event tile must force immediate event resolution");
        module.IsTurnClosed.Should().BeFalse("turn flow should pause until mandatory event resolution completes");
        module.AuditTrail.Should().ContainInOrder("PlayerLanded", "MandatoryEventResolutionEntered");
    }

    [Fact]
    public void ShouldCloseTurn_WhenLandingOnNonEventTile()
    {
        var module = new EventTileAutoTriggerEnforcementModule();

        module.OnPlayerLanded(EventTileType.Normal);

        module.IsAwaitingMandatoryEventResolution.Should().BeFalse();
        module.IsTurnClosed.Should().BeTrue();
        module.AuditTrail.Should().ContainInOrder("PlayerLanded", "TurnEnded");
    }

    // ACC:T137.2
    [Fact]
    public void ShouldRejectSkipAndUnrelatedActions_WhenEventResolutionIsActive()
    {
        var module = new EventTileAutoTriggerEnforcementModule();

        module.OnPlayerLanded(EventTileType.Event);

        module.TrySkip().Should().BeFalse("skip must be blocked during mandatory event resolution");
        module.TryEndTurn().Should().BeFalse("end-turn must be blocked during mandatory event resolution");
        module.TryOpenShop().Should().BeFalse("unrelated actions must be blocked during mandatory event resolution");
        module.IsAwaitingMandatoryEventResolution.Should().BeTrue("blocked actions must not exit mandatory resolution state");
        module.IsTurnClosed.Should().BeFalse("blocked actions must not close the turn while mandatory event resolution is active");
    }
}
