using FluentAssertions;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class CollisionServiceTests
{
    [Fact]
    public void AabbIntersects_ShouldDetectOverlap()
    {
        CollisionService.AabbIntersects(0, 0, 10, 10, 5, 5, 10, 10).Should().BeTrue();
        CollisionService.AabbIntersects(0, 0, 10, 10, 11, 11, 5, 5).Should().BeFalse();
    }

    [Fact]
    public void CircleIntersects_ShouldDetectTouching()
    {
        CollisionService.CircleIntersects(0, 0, 5, 8, 0, 3).Should().BeTrue();
        CollisionService.CircleIntersects(0, 0, 5, 11, 0, 5).Should().BeFalse();
    }
}

