using System;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Domain;
using Game.Core.State;
using Xunit;

namespace Game.Core.Tests.State;

public class GameStateManagerSecurityTests
{
    private static GameState MakeState(int level = 1, int score = 0)
        => new(
            Id: Guid.NewGuid().ToString("N"),
            Level: level,
            Score: score,
            Health: 100,
            Inventory: Array.Empty<string>(),
            Position: new Game.Core.Domain.ValueObjects.Position(0, 0),
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
    public async Task LoadGameWithDeeplyNestedJsonShouldThrowJsonException()
    {
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);

        var now = DateTime.UtcNow;
        var save = new SaveData(
            Id: "deep-save",
            State: MakeState(level: 1, score: 0),
            Config: MakeConfig(),
            Metadata: new SaveMetadata(now, now, "1.0.0", Checksum: "unused")
        );

        var json = JsonSerializer.Serialize(save);
        var deepJson = json.TrimEnd('}') + ",\"extra\":" + GenerateNestedJson(depth: 50) + "}";
        await store.SaveAsync(save.Id, deepJson);

        Func<Task> act = async () => await mgr.LoadGameAsync(save.Id);
        await act.Should().ThrowAsync<JsonException>();
    }

    [Fact]
    public async Task SaveGameWithOversizedScreenshotShouldThrowArgumentOutOfRangeException()
    {
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);
        mgr.SetState(MakeState(), MakeConfig());

        var hugeScreenshot = new string('x', 2_000_001);

        Func<Task> act = async () => await mgr.SaveGameAsync(name: "slot", screenshot: hugeScreenshot);
        var ex = await act.Should().ThrowAsync<ArgumentOutOfRangeException>();
        ex.Which.ParamName.Should().Be("screenshot");
    }

    [Fact]
    public async Task SaveGameWithOversizedTitleShouldThrowArgumentOutOfRangeException()
    {
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);
        mgr.SetState(MakeState(), MakeConfig());

        var longTitle = new string('x', 101);

        Func<Task> act = async () => await mgr.SaveGameAsync(name: longTitle);
        var ex = await act.Should().ThrowAsync<ArgumentOutOfRangeException>();
        ex.Which.ParamName.Should().Be("name");
    }

    [Fact]
    public async Task LoadGameWithCorruptedChecksumShouldThrowInvalidOperationException()
    {
        var store = new InMemoryDataStore();
        var mgr = new GameStateManager(store);
        mgr.SetState(MakeState(level: 7, score: 300), MakeConfig());
        var saveId = await mgr.SaveGameAsync("corrupted-save");

        var stored = await store.LoadAsync(saveId);
        stored.Should().NotBeNull();

        var saveData = JsonSerializer.Deserialize<SaveData>(stored!)!;
        var corruptedState = saveData.State with { Level = 999 };
        var corruptedSave = saveData with { State = corruptedState };
        await store.SaveAsync(saveId, JsonSerializer.Serialize(corruptedSave));

        Func<Task> act = async () => await mgr.LoadGameAsync(saveId);
        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("Save file is corrupted");
    }

    private static string GenerateNestedJson(int depth)
    {
        var sb = new StringBuilder();
        for (int i = 0; i < depth; i++)
        {
            sb.Append("{\"a\":");
        }
        sb.Append("\"x\"");
        for (int i = 0; i < depth; i++)
        {
            sb.Append("}");
        }
        return sb.ToString();
    }
}

