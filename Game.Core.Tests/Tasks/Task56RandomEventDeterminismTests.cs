using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task56RandomEventDeterminismTests
{
    // ACC:T56.1
    [Fact]
    public void RandomEventDefinition_ShouldBeConstructible()
    {
        var ev = new SanguoRandomEventDefinition(
            "ev001",
            "丰收",
            "desc",
            1);

        ev.MultiplierStepDelta.Should().Be(1);
    }
}
