using FluentAssertions;
using Game.Core.Domain;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class ScoreServiceTests
{
    [Fact]
    public void ComputeAddedScoreRespectsMultiplierAndDifficulty()
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
        added.Should().Be(150); // 100 * 1.5 * 1.0

        cfg = cfg with { Difficulty = Difficulty.Hard };
        var hardAdded = svc.ComputeAddedScore(100, cfg);
        hardAdded.Should().Be(180); // 100 * 1.5 * 1.2
    }

    [Fact]
    public void ComputeAddedScoreHandlesNegativeBasePoints()
    {
        // Arrange
        var svc = new ScoreService();
        var cfg = new GameConfig(50, 100, 1.0, false, Difficulty.Medium);

        // Act
        var result = svc.ComputeAddedScore(-50, cfg);

        // Assert
        result.Should().Be(0); // Negative clamped to 0
    }

    [Fact]
    public void ComputeAddedScoreAppliesEasyDifficultyMultiplier()
    {
        // Arrange
        var svc = new ScoreService();
        var cfg = new GameConfig(50, 100, 2.0, false, Difficulty.Easy);

        // Act
        var result = svc.ComputeAddedScore(100, cfg);

        // Assert
        result.Should().Be(180); // 100 * 2.0 * 0.9 = 180
    }

    [Fact]
    public void ComputeAddedScoreHandlesInvalidDifficulty()
    {
        // Arrange
        var svc = new ScoreService();
        var cfg = new GameConfig(50, 100, 2.0, false, (Difficulty)999); // Invalid difficulty value

        // Act
        var result = svc.ComputeAddedScore(100, cfg);

        // Assert
        result.Should().Be(200); // 100 * 2.0 * 1.0 (default multiplier)
    }
}
