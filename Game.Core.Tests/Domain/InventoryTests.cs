using Game.Core.Domain;
using Xunit;

namespace Game.Core.Tests.Domain;

public class InventoryTests
{
    [Fact]
    public void Add_and_Remove_respect_max_stack_and_counts()
    {
        var inv = new Inventory();
        Assert.Equal(0, inv.CountItem("potion"));
        var added = inv.Add("potion", count: 120, maxStack: 99);
        Assert.Equal(99, added);
        Assert.True(inv.HasItem("potion", atLeast: 50));

        var removed = inv.Remove("potion", count: 60);
        Assert.Equal(60, removed);
        Assert.Equal(39, inv.CountItem("potion"));

        removed = inv.Remove("potion", count: 100);
        Assert.Equal(39, removed);
        Assert.Equal(0, inv.CountItem("potion"));
    }

    [Fact]
    public void Add_with_zero_or_negative_count_returns_zero_and_does_not_add()
    {
        // Arrange
        var inv = new Inventory();

        // Act
        var added1 = inv.Add("sword", count: 0);
        var added2 = inv.Add("shield", count: -5);

        // Assert
        Assert.Equal(0, added1);
        Assert.Equal(0, added2);
        Assert.Equal(0, inv.CountItem("sword"));
        Assert.Equal(0, inv.CountItem("shield"));
    }

    [Fact]
    public void Add_when_at_max_stack_returns_zero_and_does_not_add_more()
    {
        // Arrange
        var inv = new Inventory();
        inv.Add("gold", count: 99, maxStack: 99);

        // Act - trying to add more when already at maxStack
        var added = inv.Add("gold", count: 50, maxStack: 99);

        // Assert
        Assert.Equal(0, added);
        Assert.Equal(99, inv.CountItem("gold"));
    }

    [Fact]
    public void Remove_with_zero_or_negative_count_returns_zero_and_does_not_remove()
    {
        // Arrange
        var inv = new Inventory();
        inv.Add("arrow", count: 50);

        // Act
        var removed1 = inv.Remove("arrow", count: 0);
        var removed2 = inv.Remove("arrow", count: -10);

        // Assert
        Assert.Equal(0, removed1);
        Assert.Equal(0, removed2);
        Assert.Equal(50, inv.CountItem("arrow"));
    }

    [Fact]
    public void Remove_from_nonexistent_item_returns_zero()
    {
        // Arrange
        var inv = new Inventory();

        // Act
        var removed = inv.Remove("nonexistent", count: 10);

        // Assert
        Assert.Equal(0, removed);
        Assert.Equal(0, inv.CountItem("nonexistent"));
    }
}

