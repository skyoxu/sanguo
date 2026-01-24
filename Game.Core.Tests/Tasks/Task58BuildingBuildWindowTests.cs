using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task58BuildingBuildWindowTests
{
    // ACC:T58.2
    // ACC:T58.3
    [Fact]
    public void ShouldExposeStableEventType_WhenBuildingBuilt()
    {
        SanguoBuildingBuilt.EventType.Should().Be("core.sanguo.building.built");
    }
}

