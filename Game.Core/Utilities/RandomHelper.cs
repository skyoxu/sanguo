namespace Game.Core.Utilities;

public static class RandomHelper
{
    private static readonly ThreadLocal<Random> _rng = new(() => new Random());

    public static int NextInt(int minInclusive, int maxExclusive)
        => _rng.Value!.Next(minInclusive, maxExclusive);

    public static double NextDouble()
        => _rng.Value!.NextDouble();
}

