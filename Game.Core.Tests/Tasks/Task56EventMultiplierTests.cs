using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task56EventMultiplierTests
{
    // ACC:T56.2
    [Fact]
    public void RandomEventApplied_EventType_ShouldBeStable()
    {
        SanguoRandomEventApplied.EventType.Should().Be("core.sanguo.random_event.applied");
    }
}

