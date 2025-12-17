using Game.Core.Domain.Threading;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;

namespace Game.Core.Domain;

/// <summary>
/// Treasury accumulator for overflow money when a credit operation would exceed a player's max money cap.
/// </summary>
/// <remarks>
/// This is intentionally kept in the domain layer (pure C#), and enforces single-threaded access.
/// The treasury is not capped by <see cref="MoneyValue"/> max; it accumulates minor units in a checked long.
/// </remarks>
public sealed class SanguoTreasury
{
    private readonly ThreadAccessGuard _threadGuard;
    private long _minorUnits;

    public SanguoTreasury()
    {
        _threadGuard = ThreadAccessGuard.CaptureCurrentThread();
        _minorUnits = 0;
    }

    /// <summary>
    /// Total treasury amount in minor units (1/<see cref="MoneyValue.MinorUnitsPerUnit"/>).
    /// </summary>
    public long MinorUnits
    {
        get
        {
            AssertThread();
            return _minorUnits;
        }
    }

    /// <summary>
    /// Deposits an overflow amount into the treasury.
    /// </summary>
    /// <param name="amount">Overflow amount to deposit. Must be non-negative.</param>
    public void Deposit(MoneyValue amount)
    {
        AssertThread();

        if (amount < MoneyValue.Zero)
            throw new ArgumentOutOfRangeException(nameof(amount), "Amount must be non-negative.");

        _minorUnits = checked(_minorUnits + amount.MinorUnits);
    }

    private void AssertThread() => _threadGuard.AssertCurrentThread();
}

