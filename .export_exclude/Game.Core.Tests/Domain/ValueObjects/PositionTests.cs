using FluentAssertions;
using Game.Core.Domain.ValueObjects;
using Xunit;

namespace Game.Core.Tests.Domain.ValueObjects;

public class PositionTests
{
    [Fact]
    public void Add_ShouldDisplaceCoordinates()
    {
        var p = new Position(1.0, 2.0);
        var p2 = p.Add(3.0, -1.0);
        p2.X.Should().Be(4.0);
        p2.Y.Should().Be(1.0);
        // immutability for record struct ensures original unchanged
        p.X.Should().Be(1.0);
        p.Y.Should().Be(2.0);
    }
}

