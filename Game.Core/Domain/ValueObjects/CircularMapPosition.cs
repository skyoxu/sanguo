using System;

namespace Game.Core.Domain.ValueObjects;

/// <summary>
/// Represents a position on a circular (wrap-around) map.
/// </summary>
public readonly record struct CircularMapPosition
{
    /// <summary>
    /// Current position index (0-based).
    /// </summary>
    public int Current { get; }

    /// <summary>
    /// Total number of positions on the map.
    /// </summary>
    public int TotalPositions { get; }

    /// <summary>
    /// Creates a circular map position.
    /// </summary>
    /// <param name="current">Current position index. Must be in range [0, totalPositions-1].</param>
    /// <param name="totalPositions">Total map positions. Must be greater than zero.</param>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when arguments are out of the valid range.</exception>
    public CircularMapPosition(int current, int totalPositions)
    {
        if (totalPositions <= 0)
            throw new ArgumentOutOfRangeException(nameof(totalPositions), "Total positions must be greater than zero.");

        if (current < 0 || current >= totalPositions)
            throw new ArgumentOutOfRangeException(nameof(current), $"Current position must be between 0 and {totalPositions - 1}.");

        Current = current;
        TotalPositions = totalPositions;
    }

    /// <summary>
    /// Advances by the given number of steps and wraps around automatically.
    /// </summary>
    /// <param name="steps">Steps to advance (can be negative).</param>
    /// <returns>New position.</returns>
    public CircularMapPosition Advance(int steps)
    {
        var next = (Current + steps) % TotalPositions;
        if (next < 0)
            next += TotalPositions;

        return new CircularMapPosition(next, TotalPositions);
    }
}

