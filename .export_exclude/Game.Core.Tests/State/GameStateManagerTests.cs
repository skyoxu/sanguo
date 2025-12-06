using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.State;
using Game.Core.Tests.Fakes;
using Xunit;

namespace Game.Core.Tests.State;

public class GameStateManagerTests
{
    private static GameState SampleState() => new(
        Id: "state-1",
        Level: 1,
        Score: 0,
        Health: 100,
        Inventory: new List<string>(),
        Position: new Position(0, 0),
        Timestamp: DateTime.UtcNow
    );

    private static GameConfig SampleConfig() => new(
        MaxLevel: 10,
        InitialHealth: 100,
        ScoreMultiplier: 1.0,
        AutoSave: false,
        Difficulty: Difficulty.Medium
    );

    [Fact]
    public async Task Save_Then_Load_ShouldRoundtrip()
    {
        var store = new FakeDataStore();
        var mgr = new GameStateManager(store);
        mgr.SetState(SampleState(), SampleConfig());

        var saveId = await mgr.SaveGameAsync();
        saveId.Should().StartWith("guild-manager-game-");

        var (state, config) = await mgr.LoadGameAsync(saveId);
        state.Id.Should().Be("state-1");
        config.MaxLevel.Should().Be(10);
    }

    [Fact]
    public async Task GetSaveList_ShouldReturnNewestFirst()
    {
        var store = new FakeDataStore();
        var mgr = new GameStateManager(store, GameStateManagerOptions.Default with { MaxSaves = 2 });
        mgr.SetState(SampleState(), SampleConfig());
        var a = await mgr.SaveGameAsync();
        await Task.Delay(1);
        var b = await mgr.SaveGameAsync();
        var list = await mgr.GetSaveListAsync();
        list.Select(s => s.Id).Should().Contain(new[] { a, b });
    }

    [Fact]
    public async Task AutoSaveTick_ShouldCreateSave_WhenEnabled()
    {
        var store = new FakeDataStore();
        var mgr = new GameStateManager(store);
        mgr.SetState(SampleState(), SampleConfig());
        mgr.EnableAutoSave();
        await mgr.AutoSaveTickAsync();
        var list = await mgr.GetSaveListAsync();
        list.Should().NotBeEmpty();
    }

    [Fact]
    public void OnEvent_ShouldNotify()
    {
        var store = new FakeDataStore();
        var mgr = new GameStateManager(store);
        DomainEvent? received = null;
        mgr.OnEvent(e => received = e);
        mgr.SetState(SampleState(), SampleConfig());
        received.Should().NotBeNull();
        received!.Type.Should().Be("game.state.manager.updated");
    }
}

