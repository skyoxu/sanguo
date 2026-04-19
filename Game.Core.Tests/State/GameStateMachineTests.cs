using FluentAssertions;
using Game.Core.State;
using Xunit;

namespace Game.Core.Tests.State;

public class GameStateMachineTests
{
    // ACC:T96.2
    [Fact]
    public void ShouldReachGameOver_WhenFollowingHappyPathTransitions()
    {
        var fsm = new GameStateMachine();
        int calls = 0;
        fsm.OnTransition += (prev, next) => calls++;

        fsm.Start().Should().BeTrue();
        fsm.Pause().Should().BeTrue();
        fsm.Resume().Should().BeTrue();
        fsm.End().Should().BeTrue();

        fsm.State.Should().Be(GameFlowState.GameOver);
        calls.Should().Be(4);
    }

    // ACC:T96.2
    [Fact]
    public void ShouldRejectTransition_WhenStateFlowIsInvalid()
    {
        var fsm = new GameStateMachine();
        fsm.Resume().Should().BeFalse();
        fsm.End().Should().BeTrue();
        fsm.End().Should().BeFalse();
        fsm.Start().Should().BeFalse();
    }
}
