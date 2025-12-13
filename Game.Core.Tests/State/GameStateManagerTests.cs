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

    [Fact]
    public async Task SaveLoadDeleteAndIndex_WithCompression_WorksCorrectly()
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
    public async Task AutoSave_ToggleAndTick_WorksCorrectly()
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
    public async Task Save_throws_when_state_missing_or_title_too_long()
    {
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);
        await Assert.ThrowsAsync<InvalidOperationException>(async () => await mgr.SaveGameAsync());

        mgr.SetState(MakeState(), MakeConfig());
        var tooLong = new string('x', 101);
        await Assert.ThrowsAsync<ArgumentOutOfRangeException>(async () => await mgr.SaveGameAsync(tooLong));
    }

    [Fact]
    public async Task Save_and_load_without_compression_works()
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
    public async Task Load_throws_when_checksum_mismatch()
    {
        // Arrange - save a valid state first
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);
        mgr.SetState(MakeState(level: 7, score: 300), MakeConfig());
        var saveId = await mgr.SaveGameAsync("corrupted-save");

        // Act - manually corrupt the stored data to cause checksum mismatch
        var corruptedData = await store.LoadAsync(saveId);
        corruptedData.Should().NotBeNull();

        // Deserialize, modify the state (change level), but keep the old checksum
        var saveData = JsonSerializer.Deserialize<SaveData>(corruptedData!)!;
        var corruptedState = saveData.State with { Level = 999 }; // Change level to cause checksum mismatch
        var corruptedSave = saveData with { State = corruptedState }; // Keep original metadata with old checksum
        await store.SaveAsync(saveId, JsonSerializer.Serialize(corruptedSave));

        // Assert - loading should throw due to checksum mismatch
        await Assert.ThrowsAsync<InvalidOperationException>(async () => await mgr.LoadGameAsync(saveId));
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
}

