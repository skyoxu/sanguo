using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task130SplitTests
{
    // ACC:T130.1
    [Fact]
    [Trait("acceptance", "ACC:T130.1")]
    public void ShouldRouteToDefeatSettlement_WhenCampConditionIsFatal()
    {
        var router = new CampFailSettlementRouter();
        var initialState = SettlementRouteState.InProgress();

        var result = router.Route(initialState, campDurability: 0, currentTick: 12);

        result.NextScreen.Should().Be("defeat_settlement");
        result.EndReason.Should().Be("camp_durability_fatal");
        result.EvidenceScope.Should().Be("R3");
        result.DeadlockDetected.Should().BeFalse();
    }

    [Fact]
    public void ShouldRemainUnchanged_WhenCampConditionIsNotFatal()
    {
        var router = new CampFailSettlementRouter();
        var initialState = SettlementRouteState.InProgress();

        var result = router.Route(initialState, campDurability: 3, currentTick: 12);

        result.NextScreen.Should().Be("in_progress");
        result.EndReason.Should().BeNull();
        result.DeadlockDetected.Should().BeFalse();
        result.NextState.Should().Be(initialState);
    }

    [Fact]
    public void ShouldAvoidLoopDeadlock_WhenFatalSignalRepeatsInSameTick()
    {
        var router = new CampFailSettlementRouter();
        var initialState = SettlementRouteState.InProgress();

        var first = router.Route(initialState, campDurability: 0, currentTick: 21);
        var second = router.Route(first.NextState, campDurability: 0, currentTick: 21);

        second.DeadlockDetected.Should().BeFalse();
        second.NextScreen.Should().Be("defeat_settlement");
        second.EvidenceScope.Should().Be("R3");
    }

}
