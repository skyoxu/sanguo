using FluentAssertions;
using Game.Core.State;
using Xunit;

namespace Game.Core.Tests.State;

public class GameStateMachineTests
{
    [Fact]
    public void StartPauseResumeEnd_NormalFlow()
    {
        var sm = new GameStateMachine();
        sm.State.Should().Be(GameFlowState.Initialized);
        sm.Start().Should().BeTrue();
        sm.State.Should().Be(GameFlowState.Running);
        sm.Pause().Should().BeTrue();
        sm.State.Should().Be(GameFlowState.Paused);
        sm.Resume().Should().BeTrue();
        sm.State.Should().Be(GameFlowState.Running);
        sm.End().Should().BeTrue();
        sm.State.Should().Be(GameFlowState.GameOver);
    }

    [Fact]
    public void InvalidTransitions_ReturnFalseAndKeepState()
    {
        var sm = new GameStateMachine();
        sm.Pause().Should().BeFalse();
        sm.State.Should().Be(GameFlowState.Initialized);
        sm.End().Should().BeTrue();
        sm.End().Should().BeFalse();
    }
}

