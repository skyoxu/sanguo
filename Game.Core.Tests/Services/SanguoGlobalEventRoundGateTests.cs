using FluentAssertions;
using Game.Core.Services;
using System;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class SanguoGlobalEventRoundGateTests
{
    // ACC:T124.1
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenRoundNumberIsNotPositive()
    {
        var gate = new SanguoGlobalEventRoundGate();

        Action act = () => gate.TryMarkChecked(0);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void ShouldReturnFalse_WhenRoundWasAlreadyChecked()
    {
        var gate = new SanguoGlobalEventRoundGate();

        gate.TryMarkChecked(1).Should().BeTrue();
        gate.TryMarkChecked(1).Should().BeFalse();
    }

    // ACC:T124.1
    [Fact]
    public void ShouldKeepRoundBoundaryChecksReplayStable_WhenApplyingSameRoundSequenceTwice()
    {
        var firstReplay = new SanguoGlobalEventRoundGate();
        var secondReplay = new SanguoGlobalEventRoundGate();

        var firstResult = new[]
        {
            firstReplay.TryMarkChecked(1),
            firstReplay.TryMarkChecked(2),
            firstReplay.TryMarkChecked(2),
            firstReplay.TryMarkChecked(3),
        };
        var secondResult = new[]
        {
            secondReplay.TryMarkChecked(1),
            secondReplay.TryMarkChecked(2),
            secondReplay.TryMarkChecked(2),
            secondReplay.TryMarkChecked(3),
        };

        secondResult.Should().Equal(firstResult);
    }
}
