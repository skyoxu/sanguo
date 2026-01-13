using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task57ActionCardWindowTests
{
    // ACC:T57.2
    [Fact]
    public void ActionCardPlayed_EventType_ShouldBeStable()
    {
        SanguoActionCardPlayed.EventType.Should().Be("core.sanguo.action_card.played");
    }
}

