using FluentAssertions;
using Game.Core.Domain;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class ScoreServiceTests
{
    [Fact]
    public void Add_AppliesMultiplier()
    {
        var svc = new ScoreService();
        var cfg = new GameConfig(MaxLevel: 10, InitialHealth: 100, ScoreMultiplier: 2.0, AutoSave: false, Difficulty: Difficulty.Medium);
        svc.Add(100, cfg);
        svc.Score.Should().Be(200);
    }

    [Fact]
    public void Add_NegativeBasePoints_Clamped()
    {
        var svc = new ScoreService();
        var cfg = new GameConfig(10, 100, 1.5, false, Difficulty.Easy);
        svc.Add(-50, cfg);
        svc.Score.Should().Be(0);
    }

    [Fact]
    public void Difficulty_ScalesScore()
    {
        var svc = new ScoreService();
        var cfgHard = new GameConfig(10, 100, 1.0, false, Difficulty.Hard);
        svc.Add(100, cfgHard);
        svc.Score.Should().Be(120);
    }
}
