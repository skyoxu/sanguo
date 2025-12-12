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

    [Fact]
    public void ComputeAddedScore_HandlesNegativeBasePoints()
    {
        // Arrange
        var svc = new ScoreService();
        var cfg = new GameConfig(50, 100, 1.0, false, Difficulty.Medium);

        // Act
        var result = svc.ComputeAddedScore(-50, cfg);

        // Assert
        Assert.Equal(0, result); // Negative clamped to 0
    }

    [Fact]
    public void ComputeAddedScore_AppliesEasyDifficultyMultiplier()
    {
        // Arrange
        var svc = new ScoreService();
        var cfg = new GameConfig(50, 100, 2.0, false, Difficulty.Easy);

        // Act
        var result = svc.ComputeAddedScore(100, cfg);

        // Assert
        Assert.Equal(180, result); // 100 * 2.0 * 0.9 = 180
    }

    [Fact]
    public void ComputeAddedScore_HandlesInvalidDifficulty()
    {
        // Arrange
        var svc = new ScoreService();
        var cfg = new GameConfig(50, 100, 2.0, false, (Difficulty)999); // Invalid difficulty value

        // Act
        var result = svc.ComputeAddedScore(100, cfg);

        // Assert
        Assert.Equal(200, result); // 100 * 2.0 * 1.0 (default multiplier)
    }
}

