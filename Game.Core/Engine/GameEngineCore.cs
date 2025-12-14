using Game.Core.Contracts;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Ports;
using Game.Core.Services;

namespace Game.Core.Engine;

public class GameEngineCore
{
    private readonly IScoreService _score;
    private readonly CombatService _combat;
    private readonly InventoryService _inventorySvc;
    private readonly IEventBus _bus;
    private readonly ITime? _time;

    private DateTime _startUtc;
    private double _distanceTraveled;
    private int _moves;
    private int _enemiesDefeated;

    public GameConfig Config { get; private set; }
    public GameState State { get; private set; }

    public GameEngineCore(GameConfig config, Inventory inventory, IEventBus bus, IScoreService scoreService, ITime? time = null)
    {
        Config = config;
        _score = scoreService ?? throw new ArgumentNullException(nameof(scoreService));
        _bus = bus ?? throw new ArgumentNullException(nameof(bus));
        _combat = new CombatService(_bus);
        _inventorySvc = new InventoryService(inventory);
        _time = time;
        _enemiesDefeated = 0;

        State = new GameState(
            Id: Guid.NewGuid().ToString("N"),
            Level: 1,
            Score: 0,
            Health: config.InitialHealth,
            Inventory: new List<string>(),
            Position: new Position(0, 0),
            Timestamp: DateTime.UtcNow
        );
    }

    public GameState Start()
    {
        _startUtc = DateTime.UtcNow;
        Publish(CoreGameEvents.GameStarted, JsonElementEventData.FromObject(new { stateId = State.Id }));
        return State;
    }

    public GameState Move(double dx, double dy)
    {
        var old = State.Position;
        var next = old.Add(dx, dy);
        _distanceTraveled += Math.Sqrt(dx * dx + dy * dy);
        _moves++;
        State = State with { Position = next, Timestamp = DateTime.UtcNow };
        Publish(CoreGameEvents.PlayerMoved, JsonElementEventData.FromObject(new { x = next.X, y = next.Y }));
        return State;
    }

    public GameState ApplyDamage(Damage dmg, CombatConfig? rules = null)
    {
        var final = _combat.CalculateDamage(dmg, rules);
        var newHp = Math.Max(0, State.Health - final);
        State = State with { Health = newHp, Timestamp = DateTime.UtcNow };
        Publish(CoreGameEvents.PlayerHealthChanged, JsonElementEventData.FromObject(new { health = newHp, delta = -final }));
        return State;
    }

    public GameState AddScore(int basePoints)
    {
        var added = _score.ComputeAddedScore(basePoints, Config);
        State = State with { Score = State.Score + added, Timestamp = DateTime.UtcNow };
        Publish(CoreGameEvents.ScoreChanged, JsonElementEventData.FromObject(new { score = State.Score, basePoints, added }));
        return State;
    }

    public GameResult End()
    {
        var playTime = (DateTime.UtcNow - _startUtc).TotalSeconds;
        var stats = new GameStatistics(
            TotalMoves: _moves,
            ItemsCollected: 0,
            EnemiesDefeated: _enemiesDefeated,
            DistanceTraveled: _distanceTraveled,
            AverageReactionTime: 0.0
        );
        var result = new GameResult(State.Score, State.Level, playTime, Array.Empty<string>(), stats);
        Publish(CoreGameEvents.GameEnded, JsonElementEventData.FromObject(new { score = result.FinalScore }));
        return result;
    }

    private void Publish(string type, IEventData? data)
    {
        _ = _bus.PublishAsync(new DomainEvent(type, nameof(GameEngineCore), data, DateTime.UtcNow, Guid.NewGuid().ToString("N")));
    }
}
