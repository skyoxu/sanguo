using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task58BuildingBuildWindowTests
{
    // ACC:T58.2
    [Fact]
    public void BuildingBuilt_EventType_ShouldBeStable()
    {
        SanguoBuildingBuilt.EventType.Should().Be("core.sanguo.building.built");
    }
}

