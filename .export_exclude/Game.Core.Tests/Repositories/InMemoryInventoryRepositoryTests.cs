using FluentAssertions;
using Game.Core.Repositories;
using Xunit;

namespace Game.Core.Tests.Repositories;

public class InMemoryInventoryRepositoryTests
{
    [Fact]
    public async Task Add_Get_All_ShouldWork()
    {
        var repo = new InMemoryInventoryRepository();
        (await repo.AddAsync("potion", 2)).Qty.Should().Be(2);
        (await repo.AddAsync("potion", 3)).Qty.Should().Be(5);
        var got = await repo.GetAsync("potion");
        got!.Qty.Should().Be(5);
        var all = await repo.AllAsync();
        all.Should().ContainSingle(i => i.ItemId == "potion" && i.Qty == 5);
    }
}

