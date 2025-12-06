namespace Game.Core.Utilities;

public static class MathHelper
{
    public static int Clamp(int value, int min, int max)
        => value < min ? min : (value > max ? max : value);

    public static double Clamp(double value, double min, double max)
        => value < min ? min : (value > max ? max : value);

    public static double Lerp(double a, double b, double t)
        => a + (b - a) * Clamp(t, 0.0, 1.0);
}

