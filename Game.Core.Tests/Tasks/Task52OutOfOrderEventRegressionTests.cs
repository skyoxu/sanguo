using System;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task52OutOfOrderEventRegressionTests
{
    // ACC:T52.3
    [Fact]
    public void ActionCardPlayed_EventType_ShouldBeStable()
    {
        SanguoActionCardPlayed.EventType.Should().Be("core.sanguo.action_card.played");
    }

    // ACC:T52.4
    [Fact]
    public void RandomEventApplied_EventType_ShouldBeStable()
    {
        SanguoRandomEventApplied.EventType.Should().Be("core.sanguo.random_event.applied");
    }
}

