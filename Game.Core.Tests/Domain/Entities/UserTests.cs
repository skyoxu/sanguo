using FluentAssertions;
using Game.Core.Domain.Entities;
using Xunit;

namespace Game.Core.Tests.Domain.Entities;

public class UserTests
{
    [Fact]
    public void UserShouldInitializeWithDefaults()
    {
        // Arrange & Act
        var user = new User();

        // Assert
        user.Id.Should().BeEmpty();
        user.Username.Should().BeEmpty();
        user.CreatedAt.Should().Be(0);
        user.LastLogin.Should().BeNull();
    }

    [Fact]
    public void UserShouldSetAllProperties()
    {
        // Arrange
        var user = new User
        {
            Id = "user_001",
            Username = "player1",
            CreatedAt = 1638360000,
            LastLogin = 1638363600
        };

        // Assert
        user.Id.Should().Be("user_001");
        user.Username.Should().Be("player1");
        user.CreatedAt.Should().Be(1638360000);
        user.LastLogin.Should().Be(1638363600);
    }

    [Fact]
    public void UserShouldAllowNullLastLogin()
    {
        // Arrange & Act
        var user = new User
        {
            Id = "user_002",
            LastLogin = null
        };

        // Assert
        user.LastLogin.Should().BeNull();
    }
}
