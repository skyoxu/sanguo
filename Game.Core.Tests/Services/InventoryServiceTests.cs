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
}

