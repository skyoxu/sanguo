using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;
using Game.Core.Contracts;
using Game.Core.Domain;
using Game.Core.Ports;
using Game.Core.State;
using Xunit;

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
    public async Task Save_load_delete_and_index_flow_works_with_compression()
    {
        var store = new InMemoryDataStore();
        var opts = new GameStateManagerOptions(MaxSaves: 2, EnableCompression: true);
        var mgr = new GameStateManager(store, opts);

        var seen = new List<string>();
        mgr.OnEvent(e => seen.Add(e.Type));

        mgr.SetState(MakeState(level:2), MakeConfig());
        var id1 = await mgr.SaveGameAsync("slot1");
        Assert.Contains("game.save.created", seen);
        Assert.True(store.Snapshot.ContainsKey(id1));
        Assert.StartsWith("gz:", store.Snapshot[id1]);

        mgr.SetState(MakeState(level:3), MakeConfig());
        var id2 = await mgr.SaveGameAsync("slot2");
        var list = await mgr.GetSaveListAsync();
        Assert.True(list.Count >= 2);

        // Trigger cleanup by saving third; MaxSaves=2 => first gets deleted from store
        mgr.SetState(MakeState(level:4), MakeConfig());
        var id3 = await mgr.SaveGameAsync("slot3");

        var saveIndexKey = opts.StorageKey + ":index";
        var indexJson = await store.LoadAsync(saveIndexKey);
        Assert.NotNull(indexJson);
        var ids = JsonSerializer.Deserialize<List<string>>(indexJson!)!;
        Assert.Equal(2, ids.Count);
        Assert.DoesNotContain(id1, ids);

        // load latest
        var (state, cfg) = await mgr.LoadGameAsync(id3);
        Assert.Equal(4, state.Level);
        Assert.Equal(100, cfg.InitialHealth);

        // delete second
        await mgr.DeleteSaveAsync(id2);
        indexJson = await store.LoadAsync(saveIndexKey);
        ids = JsonSerializer.Deserialize<List<string>>(indexJson!)!;
        Assert.DoesNotContain(id2, ids);
    }

    [Fact]
    public async Task AutoSave_toggle_and_tick()
    {
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);
        mgr.SetState(MakeState(level:5), MakeConfig());
        mgr.EnableAutoSave();
        await mgr.AutoSaveTickAsync();
        mgr.DisableAutoSave();
        var idx = await store.LoadAsync("guild-manager-game:index");
        Assert.NotNull(idx);
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
        Assert.True(store.Snapshot.ContainsKey(saveId));
        Assert.DoesNotContain("gz:", store.Snapshot[saveId]);

        // Verify can load back
        var (state, config) = await mgr.LoadGameAsync(saveId);
        Assert.Equal(10, state.Level);
        Assert.Equal(500, state.Score);
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
        Assert.NotNull(corruptedData);

        // Deserialize, modify the state (change level), but keep the old checksum
        var saveData = JsonSerializer.Deserialize<SaveData>(corruptedData!)!;
        var corruptedState = saveData.State with { Level = 999 }; // Change level to cause checksum mismatch
        var corruptedSave = saveData with { State = corruptedState }; // Keep original metadata with old checksum
        await store.SaveAsync(saveId, JsonSerializer.Serialize(corruptedSave));

        // Assert - loading should throw due to checksum mismatch
        await Assert.ThrowsAsync<InvalidOperationException>(async () => await mgr.LoadGameAsync(saveId));
    }

    [Fact]
    public void GetState_returns_null_when_no_state_set()
    {
        // Arrange - create manager without setting state
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);

        // Act
        var state = mgr.GetState();

        // Assert - should return null
        Assert.Null(state);
    }

    [Fact]
    public void GetConfig_returns_null_when_no_config_set()
    {
        // Arrange - create manager without setting config
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);

        // Act
        var config = mgr.GetConfig();

        // Assert - should return null
        Assert.Null(config);
    }

    [Fact]
    public void GetState_returns_copy_when_state_exists()
    {
        // Arrange - set state
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);
        var originalState = MakeState(level: 5, score: 1000);
        mgr.SetState(originalState, MakeConfig());

        // Act
        var retrievedState = mgr.GetState();

        // Assert - should return a copy with same values
        Assert.NotNull(retrievedState);
        Assert.Equal(5, retrievedState!.Level);
        Assert.Equal(1000, retrievedState.Score);
    }

    [Fact]
    public void GetConfig_returns_copy_when_config_exists()
    {
        // Arrange - set config
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);
        var originalConfig = MakeConfig();
        mgr.SetState(MakeState(), originalConfig);

        // Act
        var retrievedConfig = mgr.GetConfig();

        // Assert - should return a copy with same values
        Assert.NotNull(retrievedConfig);
        Assert.Equal(100, retrievedConfig!.InitialHealth);
        Assert.Equal(50, retrievedConfig.MaxLevel);
    }
}

