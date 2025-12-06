namespace Game.Core.Domain.ValueObjects;

public readonly record struct Position(double X, double Y)
{
    public Position Add(double dx, double dy) => new(X + dx, Y + dy);
}

