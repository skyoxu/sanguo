using FluentAssertions;
using Game.Core.Domain.Entities;
using Xunit;

namespace Game.Core.Tests.Domain.Entities;

public class SaveGameTests
{
    [Fact]
    public void SaveGameShouldInitializeWithDefaults()
    {
        // Arrange & Act
        var saveGame = new SaveGame();

        // Assert
        saveGame.Id.Should().BeEmpty();
        saveGame.UserId.Should().BeEmpty();
        saveGame.SlotNumber.Should().Be(0);
        saveGame.Data.Should().BeEmpty();
        saveGame.CreatedAt.Should().Be(0);
        saveGame.UpdatedAt.Should().Be(0);
    }

    [Fact]
    public void SaveGameShouldSetAllProperties()
    {
        // Arrange
        var jsonData = "{\"level\":5,\"score\":1000}";
        var saveGame = new SaveGame
        {
            Id = "save_001",
            UserId = "user_123",
            SlotNumber = 1,
            Data = jsonData,
            CreatedAt = 1638360000,
            UpdatedAt = 1638363600
        };

        // Assert
        saveGame.Id.Should().Be("save_001");
        saveGame.UserId.Should().Be("user_123");
        saveGame.SlotNumber.Should().Be(1);
        saveGame.Data.Should().Be(jsonData);
        saveGame.CreatedAt.Should().Be(1638360000);
        saveGame.UpdatedAt.Should().Be(1638363600);
    }

    [Fact]
    public void SaveGameShouldSupportMultipleSlots()
    {
        // Arrange & Act
        var saves = new[]
        {
            new SaveGame { SlotNumber = 1 },
            new SaveGame { SlotNumber = 2 },
            new SaveGame { SlotNumber = 3 }
        };

        // Assert
        saves[0].SlotNumber.Should().Be(1);
        saves[1].SlotNumber.Should().Be(2);
        saves[2].SlotNumber.Should().Be(3);
    }
}
