using FluentAssertions;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class CombatRulesTests
{
    [Fact]
    public void Resistances_ShouldModifyDamage()
    {
        var cfg = new CombatConfig();
        cfg.Resistances[DamageType.Fire] = 0.5; // 50% resist
        var svc = new CombatService();
        svc.CalculateDamage(new Damage(40, DamageType.Fire), cfg).Should().Be(20);
        svc.CalculateDamage(new Damage(40, DamageType.Physical), cfg).Should().Be(40);
    }

    [Fact]
    public void Critical_ShouldApplyMultiplier()
    {
        var cfg = new CombatConfig { CritMultiplier = 2.0 };
        var svc = new CombatService();
        svc.CalculateDamage(new Damage(30, DamageType.Ice, IsCritical: true), cfg).Should().Be(60);
    }

    [Fact]
    public async Task ApplyDamage_ShouldPublishEvent_WhenBusProvided()
    {
        var bus = new InMemoryEventBus();
        var svc = new CombatService(bus);
        var player = new Player(100);
        var received = new List<Game.Core.Contracts.DomainEvent>();
        using var d = bus.Subscribe(evt => { received.Add(evt); return Task.CompletedTask; });
        svc.ApplyDamage(player, new Damage(25, DamageType.Physical));
        await bus.PublishAsync(new Game.Core.Contracts.DomainEvent("noop", "test", null, DateTime.UtcNow, "id")); // flush same loop
        received.Should().NotBeEmpty();
        received.Any(e => e.Type == "player.damaged").Should().BeTrue();
    }
}

