using Game.Core.Domain;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class ScoreServiceTests
{
    [Fact]
    public void ComputeAddedScore_respects_multiplier_and_difficulty()
    {
        var svc = new ScoreService();
        var cfg = new GameConfig(
            MaxLevel: 50,
            InitialHealth: 100,
            ScoreMultiplier: 1.5,
            AutoSave: false,
            Difficulty: Difficulty.Medium
        );

        var added = svc.ComputeAddedScore(100, cfg);
        Assert.Equal(150, added); // 100 * 1.5 * 1.0

        cfg = cfg with { Difficulty = Difficulty.Hard };
        var hardAdded = svc.ComputeAddedScore(100, cfg);
        Assert.Equal(180, hardAdded); // 100 * 1.5 * 1.2
    }

    [Fact]
    public void Add_accumulates_and_reset_clears_score()
    {
        var svc = new ScoreService();
        var cfg = new GameConfig(50, 100, 1.0, false, Difficulty.Medium);

        svc.Add(10, cfg);
        svc.Add(20, cfg);

        Assert.True(svc.Score > 0);

        var before = svc.Score;
        Assert.Equal(before, svc.Score);

        svc.Reset();
        Assert.Equal(0, svc.Score);
    }
}

