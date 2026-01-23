namespace Game.Core.Utilities;

/// <summary>
/// Deterministic RNG implementation for gameplay reproducibility (seeded).
/// </summary>
/// <remarks>
/// Uses SplitMix64 to produce a stable pseudo-random sequence for a given seed.
/// This type is pure C# and does not depend on engine APIs.
/// </remarks>
public sealed class DeterministicRandomNumberGenerator : IRandomNumberGenerator
{
    private ulong _state;

    public DeterministicRandomNumberGenerator(int seed)
    {
        // Avoid the all-zero state while still being fully deterministic for a given seed.
        _state = 0x9E3779B97F4A7C15UL ^ (uint)seed;
        if (_state == 0)
        {
            _state = 0xD1B54A32D192ED03UL;
        }
    }

    public int NextInt(int minInclusive, int maxExclusive)
    {
        if (maxExclusive <= minInclusive)
            throw new ArgumentOutOfRangeException(nameof(maxExclusive), "maxExclusive must be greater than minInclusive.");

        var range = (ulong)(maxExclusive - minInclusive);
        if (range == 1)
            return minInclusive;

        // Rejection sampling to reduce modulo bias.
        var limit = ulong.MaxValue - (ulong.MaxValue % range);
        ulong value;
        do
        {
            value = NextUInt64();
        }
        while (value >= limit);

        return (int)(minInclusive + (long)(value % range));
    }

    public double NextDouble()
    {
        // 53 bits for IEEE 754 double fraction.
        var value = NextUInt64() >> 11;
        return value * (1.0 / 9007199254740992.0); // 2^53
    }

    private ulong NextUInt64()
    {
        _state += 0x9E3779B97F4A7C15UL;
        var z = _state;
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9UL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBUL;
        return z ^ (z >> 31);
    }
}

