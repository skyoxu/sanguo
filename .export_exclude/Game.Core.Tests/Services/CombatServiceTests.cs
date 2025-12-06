using FluentAssertions;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class CombatServiceTests
{
    [Fact]
    public void ApplyDamage_RawAmount()
    {
        var player = new Player(100);
        var svc = new CombatService();
        svc.ApplyDamage(player, 40);
        player.Health.Current.Should().Be(60);
    }

    [Fact]
    public void ApplyDamage_TypedDamage()
    {
        var player = new Player(100);
        var svc = new CombatService();
        svc.ApplyDamage(player, new Damage(25, DamageType.Fire));
        player.Health.Current.Should().Be(75);
    }
}

