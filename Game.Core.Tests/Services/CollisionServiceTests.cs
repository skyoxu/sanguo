using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class CollisionServiceTests
{
    [Fact]
    public void AabbIntersects_basic_cases()
    {
        Assert.True(CollisionService.AabbIntersects(0,0,10,10, 5,5,10,10));
        Assert.False(CollisionService.AabbIntersects(0,0,10,10, 11,0,10,10));
        Assert.False(CollisionService.AabbIntersects(0,0,10,10, -11,0,10,10));
    }

    [Fact]
    public void CircleIntersects_and_Distance()
    {
        Assert.True(CollisionService.CircleIntersects(0,0,3, 4,0,3));
        Assert.False(CollisionService.CircleIntersects(0,0,1, 5,0,1));
        var d = CollisionService.Distance(new Position(0,0), new Position(3,4));
        Assert.Equal(5, d, 3);
    }

    [Fact]
    public void PointInAabb_boundary_inclusive()
    {
        Assert.True(CollisionService.PointInAabb(0,0, 0,0, 10,10));
        Assert.True(CollisionService.PointInAabb(10,10, 0,0, 10,10));
        Assert.False(CollisionService.PointInAabb(11,10, 0,0, 10,10));
    }
}

