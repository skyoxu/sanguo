using FluentAssertions;
using Game.Core.Domain;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class InventoryServiceTests
{
    [Fact]
    public void Add_WhenNewItemAndAtCapacity_ReturnsZeroAndDoesNotAdd()
    {
        var inventory = new Inventory();
        var svc = new InventoryService(inventory, maxSlots: 1);

        svc.Add("a", count: 1).Should().Be(1);
        svc.Add("b", count: 1).Should().Be(0);

        svc.CountDistinct().Should().Be(1);
        svc.HasItem("b").Should().BeFalse();
    }

    [Fact]
    public void Add_WhenExistingItemAndAtCapacity_AllowsStackingInSameSlot()
    {
        var inventory = new Inventory();
        var svc = new InventoryService(inventory, maxSlots: 1);

        svc.Add("a", count: 1).Should().Be(1);
        svc.Add("a", count: 2).Should().Be(2);

        svc.CountDistinct().Should().Be(1);
        svc.CountItem("a").Should().Be(3);
    }

    [Fact]
    public void Remove_UpdatesCountsAndRemovesEmptyStack()
    {
        var inventory = new Inventory();
        var svc = new InventoryService(inventory);

        svc.Add("potion", count: 5).Should().Be(5);
        svc.Remove("potion", count: 2).Should().Be(2);
        svc.CountItem("potion").Should().Be(3);

        svc.Remove("potion", count: 10).Should().Be(3);
        svc.HasItem("potion").Should().BeFalse();
    }

    [Fact]
    public void CountDistinct_WhenInventoryIsEmpty_ReturnsZero()
    {
        var inventory = new Inventory();
        var svc = new InventoryService(inventory);

        svc.CountDistinct().Should().Be(0);
    }

    [Fact]
    public void CountItem_WhenItemDoesNotExist_ReturnsZero()
    {
        var inventory = new Inventory();
        var svc = new InventoryService(inventory);

        svc.CountItem("missing").Should().Be(0);
    }

    [Fact]
    public void HasItem_WhenCountIsLessThanAtLeast_ReturnsFalse()
    {
        var inventory = new Inventory();
        var svc = new InventoryService(inventory);

        svc.Add("potion", count: 2).Should().Be(2);

        svc.HasItem("potion", atLeast: 3).Should().BeFalse();
        svc.HasItem("potion", atLeast: 2).Should().BeTrue();
    }

    [Fact]
    public void Add_WhenAddingBeyondMaxStack_CapsAtMaxStack()
    {
        var inventory = new Inventory();
        var svc = new InventoryService(inventory);

        svc.Add("potion", count: 2, maxStack: 3).Should().Be(2);
        svc.Add("potion", count: 10, maxStack: 3).Should().Be(1);

        svc.CountItem("potion").Should().Be(3);
    }

    [Fact]
    public void Remove_WhenItemDoesNotExist_ReturnsZero()
    {
        var inventory = new Inventory();
        var svc = new InventoryService(inventory);

        svc.Remove("missing", count: 1).Should().Be(0);
        svc.CountDistinct().Should().Be(0);
    }
}
