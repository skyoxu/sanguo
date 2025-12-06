namespace Game.Core.Domain.ValueObjects;

public enum DamageType
{
    Physical,
    Magical,
    Fire,
    Ice,
    Poison,
    Holy,
    Shadow
}

public readonly record struct Damage(int Amount, DamageType Type, bool IsCritical = false)
{
    public int EffectiveAmount => Amount < 0 ? 0 : Amount;
}

