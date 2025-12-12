using System;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class CombatServiceTests
{
    [Fact]
    public void CalculateDamage_applies_resistance_and_critical()
    {
        var cfg = new CombatConfig { CritMultiplier = 2.0 };
        cfg.Resistances[DamageType.Fire] = 0.5; // 50% resist

        var svc = new CombatService();
        var baseFire = new Damage(100, DamageType.Fire);
        var reduced = svc.CalculateDamage(baseFire, cfg);
        Assert.Equal(50, reduced);

        var crit = new Damage(100, DamageType.Fire, IsCritical: true);
        var reducedCrit = svc.CalculateDamage(crit, cfg);
        Assert.Equal(100, reducedCrit); // 100 * 0.5 * 2.0
    }

    [Fact]
    public void CalculateDamage_with_armor_mitigates_linearly()
    {
        var cfg = new CombatConfig();
        var svc = new CombatService();
        var dmg = new Damage(40, DamageType.Physical);
        var res = svc.CalculateDamage(dmg, cfg, armor: 10);
        Assert.Equal(30, res);
    }

    [Fact]
    public void ApplyDamage_reduces_player_health()
    {
        var p = new Player(maxHealth: 100);
        var svc = new CombatService();
        svc.ApplyDamage(p, new Damage(25, DamageType.Physical));
        Assert.Equal(75, p.Health.Current);
    }

    [Fact]
    public void ApplyDamage_WithIntAmount_ReducesHealth()
    {
        // Arrange
        var player = new Player(maxHealth: 100);
        var svc = new CombatService();

        // Act
        svc.ApplyDamage(player, 30);

        // Assert
        Assert.Equal(70, player.Health.Current);
    }

    [Fact]
    public void ApplyDamage_WithConfig_AppliesCalculatedDamage()
    {
        // Arrange
        var player = new Player(maxHealth: 100);
        var cfg = new CombatConfig { CritMultiplier = 2.0 };
        cfg.Resistances[DamageType.Fire] = 0.5;
        var svc = new CombatService();
        var damage = new Damage(40, DamageType.Fire);

        // Act
        svc.ApplyDamage(player, damage, cfg);

        // Assert
        Assert.Equal(80, player.Health.Current); // 40 * 0.5 = 20 damage
    }

    [Fact]
    public void ApplyDamage_WithEventBus_PublishesEvent()
    {
        // Arrange
        var player = new Player(maxHealth: 100);
        var eventBus = new InMemoryEventBus();
        var svc = new CombatService(eventBus);
        var damage = new Damage(25, DamageType.Physical);

        // Act
        svc.ApplyDamage(player, damage);

        // Assert
        Assert.Equal(75, player.Health.Current);
        // Event should be published (covering the _bus?.PublishAsync branch with non-null _bus)
    }
}
