using FluentAssertions;
using Game.Core.Domain;
using Xunit;

namespace Game.Core.Tests.Domain;

public class GameConfigTests
{
    [Fact]
    public void Ctor_sets_properties_as_expected()
    {
        // Arrange
        var config = new GameConfig(
            MaxLevel: 10,
            InitialHealth: 100,
            ScoreMultiplier: 2.5,
            AutoSave: true,
            Difficulty: Difficulty.Hard
        );

        // Act & Assert
        config.MaxLevel.Should().Be(10);
        config.InitialHealth.Should().Be(100);
        config.ScoreMultiplier.Should().Be(2.5);
        config.AutoSave.Should().BeTrue();
        config.Difficulty.Should().Be(Difficulty.Hard);
    }
}

