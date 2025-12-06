namespace Game.Core.Domain.ValueObjects;

/// <summary>
/// Immutable value object representing health points.
/// </summary>
public record Health
{
    public int Current { get; init; }
    public int Maximum { get; init; }

    public Health(int maximum)
    {
        ArgumentOutOfRangeException.ThrowIfNegative(maximum, nameof(maximum));
        Maximum = maximum;
        Current = maximum;
    }

    public Health TakeDamage(int amount)
    {
        if (amount < 0)
            throw new ArgumentOutOfRangeException(nameof(amount));
        var newCurrent = Math.Max(0, Current - amount);
        return this with { Current = newCurrent };
    }

    public bool IsAlive => Current > 0;
}

