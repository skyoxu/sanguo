using FluentAssertions;
using Game.Core.Domain;
using Xunit;
using System;
using System.Collections.Generic;

namespace Game.Core.Tests.Domain;

public class GameResultsTests
{
    [Fact]
    public void GameStatisticsShouldCreateWithAllProperties()
    {
        // Arrange & Act
        var stats = new GameStatistics(
            TotalMoves: 150,
            ItemsCollected: 25,
            EnemiesDefeated: 10,
            DistanceTraveled: 1500.5,
            AverageReactionTime: 0.35
        );

        // Assert
        stats.TotalMoves.Should().Be(150);
        stats.ItemsCollected.Should().Be(25);
        stats.EnemiesDefeated.Should().Be(10);
        stats.DistanceTraveled.Should().Be(1500.5);
        stats.AverageReactionTime.Should().Be(0.35);
    }

    [Fact]
    public void GameStatisticsShouldSupportValueEquality()
    {
        // Arrange
        var stats1 = new GameStatistics(100, 20, 5, 1000.0, 0.4);
        var stats2 = new GameStatistics(100, 20, 5, 1000.0, 0.4);

        // Assert
        stats1.Should().Be(stats2);
    }

    [Fact]
    public void GameResultShouldCreateWithAllProperties()
    {
        // Arrange
        var stats = new GameStatistics(150, 25, 10, 1500.5, 0.35);
        var achievements = new List<string> { "first_win", "speed_demon" };

        // Act
        var result = new GameResult(
            FinalScore: 5000,
            LevelReached: 10,
            PlayTimeSeconds: 3600.5,
            Achievements: achievements,
            Statistics: stats
        );

        // Assert
        result.FinalScore.Should().Be(5000);
        result.LevelReached.Should().Be(10);
        result.PlayTimeSeconds.Should().Be(3600.5);
        result.Achievements.Should().BeEquivalentTo(achievements);
        result.Statistics.Should().Be(stats);
    }

    [Fact]
    public void GameResultShouldSupportEmptyAchievements()
    {
        // Arrange
        var stats = new GameStatistics(0, 0, 0, 0, 0);

        // Act
        var result = new GameResult(0, 1, 10.0, Array.Empty<string>(), stats);

        // Assert
        result.Achievements.Should().BeEmpty();
    }

    [Fact]
    public void GameResultAchievementsAreReadOnly()
    {
        // Arrange
        var achievements = new List<string> { "test" };
        var stats = new GameStatistics(1, 1, 1, 1, 1);
        var result = new GameResult(100, 1, 10, achievements, stats);

        // Assert - Achievements should be readonly collection
        result.Achievements.Should().BeAssignableTo<IReadOnlyList<string>>();
        result.Achievements.Should().HaveCount(1);
        result.Achievements.Should().Contain("test");
    }
}
