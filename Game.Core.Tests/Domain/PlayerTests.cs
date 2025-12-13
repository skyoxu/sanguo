using FluentAssertions;
using Game.Core.Domain;
using Xunit;

namespace Game.Core.Tests.Domain;

public class PlayerTests
{
    [Fact]
    public void NewPlayerHasFullHealthAndOriginPosition()
    {
        var p = new Player(maxHealth: 50);
        p.Health.Maximum.Should().Be(50);
        p.Health.Current.Should().Be(50);
        p.IsAlive.Should().BeTrue();
        p.Position.X.Should().Be(0);
        p.Position.Y.Should().Be(0);
    }

    [Fact]
    public void MoveAndTakeDamageUpdateState()
    {
        var p = new Player(maxHealth: 10);
        p.Move(1.5, -2);
        p.Position.X.Should().Be(1.5);
        p.Position.Y.Should().Be(-2);
        p.TakeDamage(7);
        p.Health.Current.Should().Be(3);
    }
}

