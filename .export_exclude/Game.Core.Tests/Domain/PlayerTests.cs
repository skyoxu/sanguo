using FluentAssertions;
using Game.Core.Domain;
using Xunit;

namespace Game.Core.Tests.Domain;

public class PlayerTests
{
    [Fact]
    public void Player_TakeDamage_ReducesHealth()
    {
        var player = new Player(maxHealth: 100);
        player.TakeDamage(30);
        player.Health.Current.Should().Be(70);
    }

    [Theory]
    [InlineData(100, 50, 50)]
    [InlineData(100, 150, 0)]
    [InlineData(50, 25, 25)]
    public void Player_TakeDamage_HandlesEdgeCases(int initial, int damage, int expected)
    {
        var player = new Player(maxHealth: initial);
        player.TakeDamage(damage);
        player.Health.Current.Should().Be(expected);
    }
}
