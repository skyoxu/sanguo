using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task52TurnPhaseWindowTests
{
    // ACC:T52.1
    [Fact]
    public void TurnPhase_ShouldContainBeforeRoll()
    {
        SanguoTurnPhase.BeforeRoll.Should().Be(SanguoTurnPhase.BeforeRoll);
    }
}

