using FluentAssertions;
using Game.Core.Domain.Entities;
using Xunit;

namespace Game.Core.Tests.Domain.Entities;

public class AchievementTests
{
    [Fact]
    public void AchievementShouldInitializeWithDefaults()
    {
        // Arrange & Act
        var achievement = new Achievement();

        // Assert
        achievement.Id.Should().BeEmpty();
        achievement.UserId.Should().BeEmpty();
        achievement.AchievementKey.Should().BeEmpty();
        achievement.UnlockedAt.Should().Be(0);
        achievement.Progress.Should().Be(0.0);
    }

    [Fact]
    public void AchievementShouldSetAllProperties()
    {
        // Arrange
        var achievement = new Achievement
        {
            Id = "ach_001",
            UserId = "user_123",
            AchievementKey = "first_victory",
            UnlockedAt = 1638360000,
            Progress = 100.0
        };

        // Assert
        achievement.Id.Should().Be("ach_001");
        achievement.UserId.Should().Be("user_123");
        achievement.AchievementKey.Should().Be("first_victory");
        achievement.UnlockedAt.Should().Be(1638360000);
        achievement.Progress.Should().Be(100.0);
    }

    [Fact]
    public void AchievementShouldAllowPartialProgress()
    {
        // Arrange & Act
        var achievement = new Achievement
        {
            Progress = 45.5
        };

        // Assert
        achievement.Progress.Should().Be(45.5);
    }
}
