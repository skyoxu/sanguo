using FluentAssertions;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Engine;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Engine;

public class GameEngineCoreTests
{
    private static GameConfig Cfg() => new(10, 100, 1.0, false, Difficulty.Medium);

    [Fact]
    public void Start_ShouldInitializeAndPublish()
    {
        var inv = new Inventory();
        var bus = new InMemoryEventBus();
        var engine = new GameEngineCore(Cfg(), inv, bus);
        var received = 0;
        using var d = bus.Subscribe(_ => { received++; return Task.CompletedTask; });
        var s = engine.Start();
        s.Level.Should().Be(1);
        received.Should().BeGreaterThan(0);
    }

    [Fact]
    public void Move_ShouldUpdatePosition_AndTrackStats()
    {
        var inv = new Inventory();
        var engine = new GameEngineCore(Cfg(), inv);
        engine.Start();
        var s = engine.Move(3, 4);
        s.Position.X.Should().Be(3);
        s.Position.Y.Should().Be(4);
        var result = engine.End();
        result.Statistics.DistanceTraveled.Should().BeApproximately(5.0, 0.001);
        result.Statistics.TotalMoves.Should().Be(1);
    }

    [Fact]
    public void ApplyDamage_ShouldReduceHealth()
    {
        var engine = new GameEngineCore(Cfg(), new Inventory());
        engine.Start();
        var s = engine.ApplyDamage(new Damage(25, DamageType.Physical));
        s.Health.Should().Be(75);
    }

    [Fact]
    public void AddScore_ShouldApplyConfig()
    {
        var cfg = Cfg() with { ScoreMultiplier = 1.5, Difficulty = Difficulty.Hard };
        var engine = new GameEngineCore(cfg, new Inventory());
        engine.Start();
        var s = engine.AddScore(100);
        s.Score.Should().Be(180); // 100 * 1.5 * 1.2
    }
}

