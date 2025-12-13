using System.Linq;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Repositories;
using Xunit;

namespace Game.Core.Tests.Repositories;

public class InMemoryInventoryRepositoryTests
{
    [Fact]
    public async Task AddGetAllBasicFlowWorksCorrectly()
    {
        var repo = new InMemoryInventoryRepository();
        var i1 = await repo.AddAsync("iron", 3);
        i1.Qty.Should().Be(3);
        var i2 = await repo.AddAsync("iron", 2);
        i2.Qty.Should().Be(5);

        var one = await repo.GetAsync("iron");
        one.Should().NotBeNull();
        one!.Qty.Should().Be(5);

        var all = await repo.AllAsync();
        all.Should().ContainSingle(x => x.ItemId == "iron" && x.Qty == 5);
    }

    [Fact]
    public async Task GetAsyncReturnsNullWhenItemDoesNotExist()
    {
        // Arrange
        var repo = new InMemoryInventoryRepository();

        // Act
        var result = await repo.GetAsync("nonexistent");

        // Assert
        result.Should().BeNull();
    }
}
