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
}

