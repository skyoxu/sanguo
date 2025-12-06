using Game.Core.Domain.ValueObjects;

namespace Game.Core.Domain;

public class Player
{
    public Health Health { get; private set; }
    public Position Position { get; private set; }

    public Player(int maxHealth = 100)
    {
        Health = new Health(maxHealth);
        Position = new Position(0, 0);
    }

    public void TakeDamage(int amount)
    {
        Health = Health.TakeDamage(amount);
    }

    public void Move(double dx, double dy)
    {
        Position = Position.Add(dx, dy);
    }

    public bool IsAlive => Health.IsAlive;
}
