using FluentAssertions;
using Game.Core.Domain.ValueObjects;
using Xunit;

namespace Game.Core.Tests.Domain.ValueObjects;

public class PositionTests
{
    [Fact]
    public void Add_returns_new_position_and_keeps_immutable()
    {
        var p = new Position(1, 2);
        var p2 = p.Add(3, 4);
        p.X.Should().Be(1);
        p.Y.Should().Be(2);
        p2.X.Should().Be(4);
        p2.Y.Should().Be(6);
        p.Should().NotBe(p2);
    }
}

