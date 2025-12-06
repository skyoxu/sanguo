using Game.Core.Domain.ValueObjects;

namespace Game.Core.Domain;

public class CombatConfig
{
    public Dictionary<DamageType, double> Resistances { get; } = new();
    public double CritChance { get; init; } = 0.0; // not used without RNG; prefer Damage.IsCritical in deterministic flows
    public double CritMultiplier { get; init; } = 2.0; // applied when damage.IsCritical

    public static CombatConfig Default => new();
}

