using FluentAssertions;
using Game.Core.Domain;
using Game.Core.State;
using Game.Core.Tests.Fakes;
using Xunit;

namespace Game.Core.Tests.State;

public class GameStateManagerDeletionTests
{
    private static GameState S() => new("id", 1, 0, 100, new List<string>(), new Game.Core.Domain.ValueObjects.Position(0, 0), DateTime.UtcNow);
    private static GameConfig C() => new(10, 100, 1.0, false, Difficulty.Medium);

    [Fact]
    public async Task Delete_RemovesFromIndex()
    {
        var store = new FakeDataStore();
        var mgr = new GameStateManager(store);
        mgr.SetState(S(), C());
        var a = await mgr.SaveGameAsync();
        var b = await mgr.SaveGameAsync();
        (await mgr.GetSaveListAsync()).Count.Should().Be(2);
        await mgr.DeleteSaveAsync(a);
        var list = await mgr.GetSaveListAsync();
        list.Select(x => x.Id).Should().Equal(new[] { b });
    }

    [Fact]
    public async Task Save_WithTitle_ShouldStoreTitle()
    {
        var mgr = new GameStateManager(new FakeDataStore());
        mgr.SetState(S(), C());
        var id = await mgr.SaveGameAsync(name: "Chapter 1");
        var list = await mgr.GetSaveListAsync();
        list.Should().ContainSingle(x => x.Id == id && x.Title == "Chapter 1");
    }
}

