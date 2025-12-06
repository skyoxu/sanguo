using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;

namespace Game.Core.Services;

public class CombatService
{
    private readonly IEventBus? _bus;

    public CombatService(IEventBus? bus = null)
    {
        _bus = bus;
    }

    public void ApplyDamage(Player player, int amount)
    {
        player.TakeDamage(amount);
    }

    public void ApplyDamage(Player player, Damage damage)
    {
        // Placeholder for future type-based mitigation; for now apply raw amount
        player.TakeDamage(damage.EffectiveAmount);
        _ = _bus?.PublishAsync(new Contracts.DomainEvent(
            Type: "player.damaged",
            Source: nameof(CombatService),
            Data: new { amount = damage.EffectiveAmount, type = damage.Type.ToString(), critical = damage.IsCritical },
            Timestamp: DateTime.UtcNow,
            Id: $"dmg-{DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()}"
        ));
    }

    public int CalculateDamage(Damage damage, CombatConfig? config = null)
    {
        config ??= CombatConfig.Default;
        var amount = Math.Max(0, damage.EffectiveAmount);
        double mult = 1.0;
        if (config.Resistances.TryGetValue(damage.Type, out var r)) mult *= r;
        if (damage.IsCritical) mult *= Math.Max(1.0, config.CritMultiplier);
        var result = (int)Math.Round(amount * mult);
        return Math.Max(0, result);
    }

    public int CalculateDamage(Damage damage, CombatConfig config, int armor)
    {
        var baseDmg = CalculateDamage(damage, config);
        // Simple linear armor mitigate; can be replaced with non-linear curve later
        var mitigated = Math.Max(0, baseDmg - Math.Max(0, armor));
        return mitigated;
    }

    public void ApplyDamage(Player player, Damage damage, CombatConfig config)
    {
        var final = CalculateDamage(damage, config);
        player.TakeDamage(final);
        _ = _bus?.PublishAsync(new Contracts.DomainEvent(
            Type: "player.damaged",
            Source: nameof(CombatService),
            Data: new { amount = final, type = damage.Type.ToString(), critical = damage.IsCritical },
            Timestamp: DateTime.UtcNow,
            Id: $"dmg-{DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()}"
        ));
    }
}
