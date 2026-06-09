using System.Collections.Generic;
using FluentAssertions;
using Game.Core.State;
using Xunit;

namespace Game.Core.Tests.State;

public class GameStateMachineTests
{
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

    [Fact]
    public void ShouldRejectTransition_WhenStateFlowIsInvalid()
    {
        var fsm = new GameStateMachine();
        fsm.Resume().Should().BeFalse();
        fsm.End().Should().BeTrue();
        fsm.End().Should().BeFalse();
        fsm.Start().Should().BeFalse();
    }

    // ACC:T204.1 ACC:T204.3 ACC:T204.4 ACC:T204.7 ACC:T204.8 ACC:T204.9 ACC:T204.10 ACC:T204.11 ACC:T204.12 ACC:T204.13 ACC:T204.14
    [Fact]
    public void ShouldResolveExplicitEntryStates_WhenStartupContinueAndRuntimeTransitionsRun()
    {
        var fsm = new GameStateMachine();
        var transitions = new List<(GameFlowState Previous, GameFlowState Next)>();
        fsm.OnTransition += (previous, next) => transitions.Add((previous, next));

        fsm.Start().Should().BeTrue();
        fsm.State.Should().Be(GameFlowState.Running);

        fsm.Pause().Should().BeTrue();
        fsm.State.Should().Be(GameFlowState.Paused);

        fsm.Resume().Should().BeTrue();
        fsm.State.Should().Be(GameFlowState.Running);

        transitions.Should().BeEquivalentTo(
            new[]
            {
                (GameFlowState.Initialized, GameFlowState.Running),
                (GameFlowState.Running, GameFlowState.Paused),
                (GameFlowState.Paused, GameFlowState.Running),
            },
            options => options.WithStrictOrdering());
    }

    // ACC:T204.2 ACC:T204.5 ACC:T204.6
    [Fact]
    public void ShouldPreserveCurrentState_WhenEntryTransitionIsInvalid()
    {
        var initialized = new GameStateMachine();

        initialized.Resume().Should().BeFalse();
        initialized.State.Should().Be(GameFlowState.Initialized);

        initialized.Pause().Should().BeFalse();
        initialized.State.Should().Be(GameFlowState.Initialized);

        initialized.Start().Should().BeTrue();
        initialized.State.Should().Be(GameFlowState.Running);

        initialized.Start().Should().BeFalse();
        initialized.State.Should().Be(GameFlowState.Running);

        initialized.End().Should().BeTrue();
        initialized.State.Should().Be(GameFlowState.GameOver);

        initialized.Start().Should().BeFalse();
        initialized.Resume().Should().BeFalse();
        initialized.End().Should().BeFalse();
        initialized.State.Should().Be(GameFlowState.GameOver);
    }
}
