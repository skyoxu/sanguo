using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Domain;
using Game.Core.Ports;
using Game.Core.State;
using Xunit;

using static Game.Core.Contracts.CoreGameEvents;

namespace Game.Core.Tests.State;

internal sealed class InMemoryDataStore : IDataStore
{
    private readonly Dictionary<string,string> _dict = new();
    public Task SaveAsync(string key, string json) { _dict[key] = json; return Task.CompletedTask; }
    public Task<string?> LoadAsync(string key) { _dict.TryGetValue(key, out var v); return Task.FromResult(v); }
    public Task DeleteAsync(string key) { _dict.Remove(key); return Task.CompletedTask; }
    public IReadOnlyDictionary<string,string> Snapshot => _dict;
}

public class GameStateManagerTests
{
    private static GameState MakeState(int level=1, int score=0)
        => new(
            Id: Guid.NewGuid().ToString(),
            Level: level,
            Score: score,
            Health: 100,
            Inventory: Array.Empty<string>(),
            Position: new Game.Core.Domain.ValueObjects.Position(0,0),
            Timestamp: DateTime.UtcNow
        );

    private static GameConfig MakeConfig()
        => new(
            MaxLevel: 50,
            InitialHealth: 100,
            ScoreMultiplier: 1.0,
            AutoSave: false,
            Difficulty: Difficulty.Medium
        );

    private sealed class CapturingErrorReporter : IErrorReporter
    {
        public List<(string Message, Exception Ex, IReadOnlyDictionary<string, string>? Context)> Exceptions { get; } = new();

        public void CaptureMessage(string level, string message, IReadOnlyDictionary<string, string>? context = null)
        {
        }

        public void CaptureException(string message, Exception ex, IReadOnlyDictionary<string, string>? context = null)
            => Exceptions.Add((message, ex, context));
    }

    [Fact]
    public async Task SaveLoadDeleteAndIndexWithCompressionWorksCorrectly()
    {
        var store = new InMemoryDataStore();
        var opts = new GameStateManagerOptions(MaxSaves: 2, EnableCompression: true);
        var mgr = new GameStateManager(store, opts);

        var seen = new List<string>();
        mgr.OnEvent(e => seen.Add(e.Type));

        mgr.SetState(MakeState(level:2), MakeConfig());
        var id1 = await mgr.SaveGameAsync("slot1");
        seen.Should().Contain(GameSaveCreated);
        store.Snapshot.ContainsKey(id1).Should().BeTrue();
        store.Snapshot[id1].Should().StartWith("gz:");

        mgr.SetState(MakeState(level:3), MakeConfig());
        var id2 = await mgr.SaveGameAsync("slot2");
        var list = await mgr.GetSaveListAsync();
        list.Count.Should().BeGreaterThanOrEqualTo(2);

        // Trigger cleanup by saving third; MaxSaves=2 => first gets deleted from store
        mgr.SetState(MakeState(level:4), MakeConfig());
        var id3 = await mgr.SaveGameAsync("slot3");

        var saveIndexKey = opts.StorageKey + ":index";
        var indexJson = await store.LoadAsync(saveIndexKey);
        indexJson.Should().NotBeNull();
        var ids = JsonSerializer.Deserialize<List<string>>(indexJson!)!;
        ids.Count.Should().Be(2);
        ids.Should().NotContain(id1);

        // load latest
        var (state, cfg) = await mgr.LoadGameAsync(id3);
        state.Level.Should().Be(4);
        cfg.InitialHealth.Should().Be(100);

        // delete second
        await mgr.DeleteSaveAsync(id2);
        indexJson = await store.LoadAsync(saveIndexKey);
        ids = JsonSerializer.Deserialize<List<string>>(indexJson!)!;
        ids.Should().NotContain(id2);
    }

    [Fact]
    public async Task AutoSaveToggleAndTickWorksCorrectly()
    {
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);
        mgr.SetState(MakeState(level:5), MakeConfig());
        mgr.EnableAutoSave();
        await mgr.AutoSaveTickAsync();
        mgr.DisableAutoSave();
        var idx = await store.LoadAsync("guild-manager-game:index");
        idx.Should().NotBeNull();
    }

    [Fact]
    public async Task SaveThrowsWhenStateMissingOrTitleTooLong()
    {
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);
        Func<Task> actMissingState = async () => await mgr.SaveGameAsync();
        await actMissingState.Should().ThrowAsync<InvalidOperationException>();

        mgr.SetState(MakeState(), MakeConfig());
        var tooLong = new string('x', 101);
        Func<Task> actTooLong = async () => await mgr.SaveGameAsync(tooLong);
        await actTooLong.Should().ThrowAsync<ArgumentOutOfRangeException>();
    }

    [Fact]
    public async Task SaveAndLoadWithoutCompressionWorks()
    {
        // Arrange - use EnableCompression: false to test non-compressed path
        var store = new InMemoryDataStore();
        var opts = new GameStateManagerOptions(EnableCompression: false);
        var mgr = new GameStateManager(store, opts);
        mgr.SetState(MakeState(level: 10, score: 500), MakeConfig());

        // Act
        var saveId = await mgr.SaveGameAsync("uncompressed-save");

        // Assert - verify non-compressed storage (should NOT start with "gz:")
        store.Snapshot.ContainsKey(saveId).Should().BeTrue();
        store.Snapshot[saveId].Should().NotContain("gz:");

        // Verify can load back
        var (state, config) = await mgr.LoadGameAsync(saveId);
        state.Level.Should().Be(10);
        state.Score.Should().Be(500);
    }

    [Fact]
    public void GetStateReturnsNullWhenNoStateSet()
    {
        // Arrange - create manager without setting state
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);

        // Act
        var state = mgr.GetState();

        // Assert - should return null
        state.Should().BeNull();
    }

    [Fact]
    public void GetConfigReturnsNullWhenNoConfigSet()
    {
        // Arrange - create manager without setting config
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);

        // Act
        var config = mgr.GetConfig();

        // Assert - should return null
        config.Should().BeNull();
    }

    [Fact]
    public void GetStateReturnsCopyWhenStateExists()
    {
        // Arrange - set state
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);
        var originalState = MakeState(level: 5, score: 1000);
        mgr.SetState(originalState, MakeConfig());

        // Act
        var retrievedState = mgr.GetState();

        // Assert - should return a copy with same values
        retrievedState.Should().NotBeNull();
        retrievedState!.Level.Should().Be(5);
        retrievedState.Score.Should().Be(1000);
    }

    [Fact]
    public void GetConfigReturnsCopyWhenConfigExists()
    {
        // Arrange - set config
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);
        var originalConfig = MakeConfig();
        mgr.SetState(MakeState(), originalConfig);

        // Act
        var retrievedConfig = mgr.GetConfig();

        // Assert - should return a copy with same values
        retrievedConfig.Should().NotBeNull();
        retrievedConfig!.InitialHealth.Should().Be(100);
        retrievedConfig.MaxLevel.Should().Be(50);
    }

    [Fact]
    public void CallbackExceptionIsReportedAndDoesNotThrow()
    {
        var store = new InMemoryDataStore();
        var reporter = new CapturingErrorReporter();
        var mgr = new GameStateManager(store, reporter: reporter);

        mgr.OnEvent(_ => throw new InvalidOperationException("boom"));

        Action act = () => mgr.SetState(MakeState(level: 2), MakeConfig());
        act.Should().NotThrow();

        reporter.Exceptions.Should().ContainSingle();
        reporter.Exceptions[0].Message.Should().Be("gamestatemanager.callback.exception");
        reporter.Exceptions[0].Context.Should().NotBeNull();
        reporter.Exceptions[0].Context!["event_type"].Should().Be(GameStateManagerUpdated);
    }

}
