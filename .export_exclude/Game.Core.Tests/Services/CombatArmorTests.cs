using FluentAssertions;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class CombatArmorTests
{
    [Fact]
    public void Armor_ReducesDamage_ClampAtZero()
    {
        var cfg = CombatConfig.Default;
        var svc = new CombatService();
        svc.CalculateDamage(new Damage(10, DamageType.Physical), cfg, armor: 3).Should().Be(7);
        svc.CalculateDamage(new Damage(10, DamageType.Physical), cfg, armor: 20).Should().Be(0);
    }
}

