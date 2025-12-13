using FluentAssertions;
using Game.Core.Domain;
using Xunit;

namespace Game.Core.Tests.Domain;

public class InventoryTests
{
    [Fact]
    public void AddAndRemoveRespectMaxStackAndCounts()
    {
        var inv = new Inventory();
        inv.CountItem("potion").Should().Be(0);
        var added = inv.Add("potion", count: 120, maxStack: 99);
        added.Should().Be(99);
        inv.HasItem("potion", atLeast: 50).Should().BeTrue();

        var removed = inv.Remove("potion", count: 60);
        removed.Should().Be(60);
        inv.CountItem("potion").Should().Be(39);

        removed = inv.Remove("potion", count: 100);
        removed.Should().Be(39);
        inv.CountItem("potion").Should().Be(0);
    }

    [Fact]
    public void AddWithZeroOrNegativeCountReturnsZeroAndDoesNotAdd()
    {
        // Arrange
        var inv = new Inventory();

        // Act
        var added1 = inv.Add("sword", count: 0);
        var added2 = inv.Add("shield", count: -5);

        // Assert
        added1.Should().Be(0);
        added2.Should().Be(0);
        inv.CountItem("sword").Should().Be(0);
        inv.CountItem("shield").Should().Be(0);
    }

    [Fact]
    public void AddWhenAtMaxStackReturnsZeroAndDoesNotAddMore()
    {
        // Arrange
        var inv = new Inventory();
        inv.Add("gold", count: 99, maxStack: 99);

        // Act - trying to add more when already at maxStack
        var added = inv.Add("gold", count: 50, maxStack: 99);

        // Assert
        added.Should().Be(0);
        inv.CountItem("gold").Should().Be(99);
    }

    [Fact]
    public void RemoveWithZeroOrNegativeCountReturnsZeroAndDoesNotRemove()
    {
        // Arrange
        var inv = new Inventory();
        inv.Add("arrow", count: 50);

        // Act
        var removed1 = inv.Remove("arrow", count: 0);
        var removed2 = inv.Remove("arrow", count: -10);

        // Assert
        removed1.Should().Be(0);
        removed2.Should().Be(0);
        inv.CountItem("arrow").Should().Be(50);
    }

    [Fact]
    public void RemoveFromNonexistentItemReturnsZero()
    {
        // Arrange
        var inv = new Inventory();

        // Act
        var removed = inv.Remove("nonexistent", count: 10);

        // Assert
        removed.Should().Be(0);
        inv.CountItem("nonexistent").Should().Be(0);
    }
}

