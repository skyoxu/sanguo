using FluentAssertions;
using Game.Core.Domain;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Domain;

public class InventoryTests
{
    [Fact]
    public void Add_StacksUpToMaxStack()
    {
        var inv = new Inventory();
        var svc = new InventoryService(inv, maxSlots: 5);
        svc.Add("potion", 50, maxStack: 20).Should().Be(20);
        svc.Add("potion", 50, maxStack: 20).Should().Be(0);
        svc.CountItem("potion").Should().Be(20);
    }

    [Fact]
    public void Capacity_LimitsDistinctItems()
    {
        var inv = new Inventory();
        var svc = new InventoryService(inv, maxSlots: 2);
        svc.Add("a", 1).Should().Be(1);
        svc.Add("b", 1).Should().Be(1);
        svc.Add("c", 1).Should().Be(0); // capacity reached
        svc.CountDistinct().Should().Be(2);
    }

    [Fact]
    public void Remove_RemovesAndDeletesWhenZero()
    {
        var inv = new Inventory();
        var svc = new InventoryService(inv);
        svc.Add("coin", 10).Should().Be(10);
        svc.Remove("coin", 7).Should().Be(7);
        svc.CountItem("coin").Should().Be(3);
        svc.Remove("coin", 5).Should().Be(3);
        svc.CountDistinct().Should().Be(0);
    }
}

