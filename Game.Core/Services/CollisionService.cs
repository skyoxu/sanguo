using Game.Core.Domain.ValueObjects;

namespace Game.Core.Services;

public static class CollisionService
{
    public static bool AabbIntersects(double x1, double y1, double w1, double h1,
                                      double x2, double y2, double w2, double h2)
    {
        return x1 < x2 + w2 &&
               x1 + w1 > x2 &&
               y1 < y2 + h2 &&
               y1 + h1 > y2;
    }

    public static bool CircleIntersects(double x1, double y1, double r1,
                                        double x2, double y2, double r2)
    {
        var dx = x2 - x1;
        var dy = y2 - y1;
        var dist2 = dx * dx + dy * dy;
        var rr = (r1 + r2) * (r1 + r2);
        return dist2 <= rr;
    }

    public static bool PointInAabb(double px, double py, double x, double y, double w, double h)
    {
        return px >= x && px <= x + w && py >= y && py <= y + h;
    }

    public static double Distance(Position a, Position b)
    {
        var dx = b.X - a.X;
        var dy = b.Y - a.Y;
        return Math.Sqrt(dx * dx + dy * dy);
    }
}

