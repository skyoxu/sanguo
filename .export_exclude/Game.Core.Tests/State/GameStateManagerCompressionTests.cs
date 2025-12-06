using FluentAssertions;
using Game.Core.Domain;
using Game.Core.State;
using Game.Core.Tests.Fakes;
using Xunit;

namespace Game.Core.Tests.State;

public class GameStateManagerCompressionTests
{
    [Fact]
    public async Task Save_UsesCompression_WhenEnabled()
    {
        var store = new FakeDataStore();
        var opts = GameStateManagerOptions.Default with { EnableCompression = true };
        var mgr = new GameStateManager(store, opts);
        var state = new GameState("id", 1, 0, 100, new List<string>(), new Game.Core.Domain.ValueObjects.Position(0, 0), DateTime.UtcNow);
        var config = new GameConfig(10, 100, 1.0, false, Difficulty.Easy);
        mgr.SetState(state, config);
        var id = await mgr.SaveGameAsync();
        var raw = store.Peek(id);
        raw.Should().NotBeNull();
        raw!.StartsWith("gz:").Should().BeTrue();
        var (loaded, _) = await mgr.LoadGameAsync(id);
        loaded.Id.Should().Be("id");
    }
}

