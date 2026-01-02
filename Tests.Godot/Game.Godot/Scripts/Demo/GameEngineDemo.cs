using Godot;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Engine;
using Game.Core.Services;
using Game.Godot.Adapters;

namespace Game.Godot.Scripts.Demo;

public partial class GameEngineDemo : Node
{
    private GameEngineCore _engine = default!;

    public override void _Ready()
    {
        var bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (bus == null)
        {
            bus = new EventBusAdapter { Name = "EventBus" };
            AddChild(bus);
        }
        var cfg = new GameConfig(MaxLevel: 10, InitialHealth: 100, ScoreMultiplier: 1.0, AutoSave: false, Difficulty: Difficulty.Medium);
        var inv = new Game.Core.Domain.Inventory();
        _engine = new GameEngineCore(cfg, inv, bus, new ScoreService());
        // Defer start until UI emits ui.menu.start
    }

    public void AddScore(int basePoints)
    {
        _engine.AddScore(basePoints);
    }

    public void ApplyDamage(int amount)
    {
        _engine.ApplyDamage(new Damage(amount, DamageType.Physical, IsCritical: false));
    }
    public void StartGame()
    {
        _engine.Start();
    }
}
