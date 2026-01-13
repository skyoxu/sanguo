using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task59CombatDeterminismTests
{
    // ACC:T59.2
    [Fact]
    public void CombatEnded_EventType_ShouldBeStable()
    {
        SanguoCombatEnded.EventType.Should().Be("core.sanguo.combat.ended");
    }
}

