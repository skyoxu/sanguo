using FluentAssertions;
using Game.Core.Services;
using System;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class SanguoGlobalEventRoundGateTests
{
    [Fact]
    public void TryMarkChecked_ShouldThrow_WhenRoundNumberNonPositive()
    {
        var gate = new SanguoGlobalEventRoundGate();

        Action act = () => gate.TryMarkChecked(0);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void TryMarkChecked_ShouldReturnFalse_WhenAlreadyChecked()
    {
        var gate = new SanguoGlobalEventRoundGate();

        gate.TryMarkChecked(1).Should().BeTrue();
        gate.TryMarkChecked(1).Should().BeFalse();
    }
}
