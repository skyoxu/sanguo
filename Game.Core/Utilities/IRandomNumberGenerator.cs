namespace Game.Core.Utilities;

/// <summary>
/// Abstraction for random number generation, used to make core logic deterministic in tests.
/// </summary>
public interface IRandomNumberGenerator
{
    int NextInt(int minInclusive, int maxExclusive);

    double NextDouble();
}

internal sealed class ThreadLocalRandomNumberGenerator : IRandomNumberGenerator
{
    public static readonly ThreadLocalRandomNumberGenerator Instance = new();

    private ThreadLocalRandomNumberGenerator()
    {
    }

    public int NextInt(int minInclusive, int maxExclusive)
        => RandomHelper.NextInt(minInclusive, maxExclusive);

    public double NextDouble()
        => RandomHelper.NextDouble();
}

