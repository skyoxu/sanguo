using FluentAssertions;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class CollisionServiceTests
{
    [Fact]
    public void AabbIntersectsBasicCases()
    {
        CollisionService.AabbIntersects(0,0,10,10, 5,5,10,10).Should().BeTrue();
        CollisionService.AabbIntersects(0,0,10,10, 11,0,10,10).Should().BeFalse();
        CollisionService.AabbIntersects(0,0,10,10, -11,0,10,10).Should().BeFalse();
    }

    [Fact]
    public void CircleIntersectsAndDistance()
    {
        CollisionService.CircleIntersects(0,0,3, 4,0,3).Should().BeTrue();
        CollisionService.CircleIntersects(0,0,1, 5,0,1).Should().BeFalse();
        var d = CollisionService.Distance(new Position(0,0), new Position(3,4));
        d.Should().BeApproximately(5, 3);
    }

    [Fact]
    public void PointInAabbBoundaryInclusive()
    {
        CollisionService.PointInAabb(0,0, 0,0, 10,10).Should().BeTrue();
        CollisionService.PointInAabb(10,10, 0,0, 10,10).Should().BeTrue();
        CollisionService.PointInAabb(11,10, 0,0, 10,10).Should().BeFalse();
    }
}

