using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class CombatServiceTests
{
    private sealed class CapturingEventBus : IEventBus
    {
        public List<DomainEvent> Published { get; } = new();

        public Task PublishAsync(DomainEvent evt)
        {
            Published.Add(evt);
            return Task.CompletedTask;
        }

        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => NoopDisposable.Instance;

        private sealed class NoopDisposable : IDisposable
        {
            public static NoopDisposable Instance { get; } = new();

            public void Dispose()
            {
            }
        }
    }

    [Fact]
    public void CalculateDamageAppliesResistanceAndCritical()
    {
        var cfg = new CombatConfig { CritMultiplier = 2.0 };
        cfg.Resistances[DamageType.Fire] = 0.5; // 50% resist

        var svc = new CombatService(NullEventBus.Instance);
        var baseFire = new Damage(100, DamageType.Fire);
        var reduced = svc.CalculateDamage(baseFire, cfg);
        reduced.Should().Be(50);

        var crit = new Damage(100, DamageType.Fire, IsCritical: true);
        var reducedCrit = svc.CalculateDamage(crit, cfg);
        reducedCrit.Should().Be(100); // 100 * 0.5 * 2.0
    }

    [Fact]
    public void CalculateDamageWithArmorMitigatesLinearly()
    {
        var cfg = new CombatConfig();
        var svc = new CombatService(NullEventBus.Instance);
        var dmg = new Damage(40, DamageType.Physical);
        var res = svc.CalculateDamage(dmg, cfg, armor: 10);
        res.Should().Be(30);
    }

    [Fact]
    public void ApplyDamageReducesPlayerHealth()
    {
        var p = new Player(maxHealth: 100);
        var svc = new CombatService(NullEventBus.Instance);
        svc.ApplyDamage(p, new Damage(25, DamageType.Physical));
        p.Health.Current.Should().Be(75);
    }

    [Fact]
    public void ApplyDamageWithIntAmountReducesHealth()
    {
        // Arrange
        var player = new Player(maxHealth: 100);
        var svc = new CombatService(NullEventBus.Instance);

        // Act
        svc.ApplyDamage(player, 30);

        // Assert
        player.Health.Current.Should().Be(70);
    }

    [Fact]
    public void ApplyDamageWithConfigAppliesCalculatedDamage()
    {
        // Arrange
        var player = new Player(maxHealth: 100);
        var cfg = new CombatConfig { CritMultiplier = 2.0 };
        cfg.Resistances[DamageType.Fire] = 0.5;
        var svc = new CombatService(NullEventBus.Instance);
        var damage = new Damage(40, DamageType.Fire);

        // Act
        svc.ApplyDamage(player, damage, cfg);

        // Assert
        player.Health.Current.Should().Be(80); // 40 * 0.5 = 20 damage
    }

    [Fact]
    public void ApplyDamageWithEventBusPublishesEvent()
    {
        // Arrange
        var player = new Player(maxHealth: 100);
        var eventBus = new CapturingEventBus();
        var svc = new CombatService(eventBus);
        var damage = new Damage(25, DamageType.Physical);

        // Act
        svc.ApplyDamage(player, damage);

        // Assert
        player.Health.Current.Should().Be(75);
        eventBus.Published.Should().ContainSingle();
        var evt = eventBus.Published[0];
        evt.Type.Should().Be(CoreGameEvents.PlayerDamaged);
        evt.Source.Should().Be(nameof(CombatService));
        Guid.TryParseExact(evt.Id, "N", out _).Should().BeTrue();
        evt.DataContentType.Should().Be("application/json");

        var data = evt.Data.Should().BeOfType<JsonElementEventData>().Which.Value;
        data.GetProperty("amount").GetInt32().Should().Be(25);
        data.GetProperty("type").GetString().Should().Be("Physical");
        data.GetProperty("critical").GetBoolean().Should().BeFalse();
    }
}
