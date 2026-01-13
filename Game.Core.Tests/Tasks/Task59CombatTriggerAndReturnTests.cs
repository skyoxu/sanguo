using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task59CombatTriggerAndReturnTests
{
    // ACC:T59.1
    [Fact]
    public void CombatStarted_EventType_ShouldBeStable()
    {
        SanguoCombatStarted.EventType.Should().Be("core.sanguo.combat.started");
    }
}

