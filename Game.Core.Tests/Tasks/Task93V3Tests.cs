using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task93V3Tests
{
    private const int TaskId = 93;
    private const string ExpectedXUnitRef = "Game.Core.Tests/Tasks/Task93V3Tests.cs";
    private const string ExpectedGdUnitRef = "Tests.Godot/tests/UI/test_task93_campaign_ui_visibility.gd";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T93.1
    [Fact]
    [Trait("acceptance", "ACC:T93.1")]
    public void ShouldIncludeCampaignIdentityDefaults_WhenSerializingCampaignStartConfig()
    {
        var cfg = CreateValidStartConfig();

        var json = JsonSerializer.Serialize(cfg);
        var root = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(json);

        root.Should().NotBeNull();
        root!.Should().ContainKey("map_id");
        root.Should().ContainKey("random_seed");
        root.Should().ContainKey("active_strategem_id");
        root.Should().ContainKey("passive_strategem_id");

        root.Should().ContainKey("run_mode");
        root["run_mode"].GetString().Should().Be("campaign");

        root.Should().ContainKey("commander_id");
        root["commander_id"].GetString().Should().Be("c_liu_bei");

        root.Should().ContainKey("difficulty");
        root["difficulty"].GetString().Should().Be("normal");
    }

    [Fact]
    public void ShouldNotRequireTransientUiState_WhenValidatingCampaignStartConfig()
    {
        var cfg = CreateValidStartConfig();

        var isValid = GameStartConfigValidator.TryValidate(cfg, out var errors);

        isValid.Should().BeTrue();
        errors.Should().BeEmpty();
    }

    // ACC:T93.2
    [Fact]
    [Trait("acceptance", "ACC:T93.2")]
    public void ShouldIgnoreUnknownFutureFields_WhenDeserializingCampaignStartConfig()
    {
        var payload = new Dictionary<string, object?>(StringComparer.Ordinal)
        {
            ["map_id"] = "map001",
            ["players_count"] = 4,
            ["starting_money_preset"] = 10000,
            ["global_event_interval_turns"] = 10,
            ["random_seed"] = 24680,
            ["character_assignments"] = CreateValidCharacterAssignments(),
            ["active_strategem_id"] = "strat_active_default",
            ["passive_strategem_id"] = "strat_passive_default",
            ["campaign_only_future_field"] = "future-ready",
            ["campaign_rule_set_version"] = 3,
        };

        var json = JsonSerializer.Serialize(payload);
        var cfg = JsonSerializer.Deserialize<GameStartConfig>(json);

        cfg.Should().NotBeNull();
        cfg!.MapId.Should().Be("map001");
        cfg.RandomSeed.Should().Be(24680);
        cfg.ActiveStrategemId.Should().Be("strat_active_default");
        cfg.PassiveStrategemId.Should().Be("strat_passive_default");

        GameStartConfigValidator.TryValidate(cfg, out var errors).Should().BeTrue();
        errors.Should().BeEmpty();
    }

    // ACC:T93.3
    [Fact]
    [Trait("acceptance", "ACC:T93.3")]
    public void ShouldContainCampaignBootstrapFields_WhenSerializingGameStartedPayload()
    {
        var cfg = CreateValidStartConfig();
        var payload = CreateGameStartedPayload(cfg);

        var json = JsonSerializer.Serialize(payload);
        var root = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(json);

        root.Should().NotBeNull();
        root!.Should().ContainKey("MapId");
        root.Should().ContainKey("RandomSeed");
        root.Should().ContainKey("ActiveStrategemId");
        root.Should().ContainKey("PassiveStrategemId");

        root.Should().ContainKey("RunMode");
        root["RunMode"].GetString().Should().Be("campaign");

        root.Should().ContainKey("CommanderId");
        root["CommanderId"].GetString().Should().Be("c_liu_bei");

        root.Should().ContainKey("Difficulty");
        root["Difficulty"].GetString().Should().Be("normal");
    }

    // ACC:T93.4
    [Fact]
    [Trait("acceptance", "ACC:T93.4")]
    public void ShouldContainReproducibleRunContext_WhenSerializingSaveSnapshotForHeaderUse()
    {
        var snapshot = CreateValidSaveSnapshot();

        var json = JsonSerializer.Serialize(snapshot);
        var root = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(json);

        root.Should().NotBeNull();
        root!.Should().ContainKey("GameId");
        root.Should().ContainKey("ContentPackId");
        root.Should().ContainKey("ContentPackVersion");

        root.Should().ContainKey("RunMode");
        root["RunMode"].GetString().Should().Be("campaign");

        root.Should().ContainKey("CommanderId");
        root["CommanderId"].GetString().Should().Be("c_liu_bei");

        root.Should().ContainKey("RandomSeed");
        root["RandomSeed"].GetInt32().Should().Be(24680);
    }

    // ACC:T93.5
    [Fact]
    [Trait("acceptance", "ACC:T93.5")]
    public void ShouldPreserveCampaignIdentityFields_WhenRoundTrippingSaveSnapshot()
    {
        var snapshot = CreateValidSaveSnapshot();

        var savedJson = JsonSerializer.Serialize(snapshot);
        var restored = JsonSerializer.Deserialize<SanguoSaveSnapshot>(savedJson);
        var restoredJson = JsonSerializer.Serialize(restored);
        var restoredRoot = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(restoredJson);

        restored.Should().NotBeNull();
        restoredRoot.Should().NotBeNull();

        restoredRoot!.Should().ContainKey("RunMode");
        restoredRoot["RunMode"].GetString().Should().Be("campaign");

        restoredRoot.Should().ContainKey("CommanderId");
        restoredRoot["CommanderId"].GetString().Should().Be("c_liu_bei");

        restoredRoot.Should().ContainKey("RandomSeed");
        restoredRoot["RandomSeed"].GetInt32().Should().Be(24680);
    }

    // ACC:T93.6
    [Fact]
    [Trait("acceptance", "ACC:T93.6")]
    public void ShouldReferenceXUnitAndGdUnitEvidence_WhenReadingTask93AcceptanceItems()
    {
        var repoRoot = FindRepoRoot();
        var taskViews = new List<JsonElement>();

        foreach (var viewFile in ViewFiles)
        {
            if (TryGetTaskByTaskmasterId(repoRoot, viewFile, TaskId, out var task))
            {
                taskViews.Add(task);
            }
        }

        taskViews.Should().NotBeEmpty("task 93 must exist in at least one task view.");

        var acceptanceItems = taskViews
            .SelectMany(static task => ReadStringArray(task, "acceptance"))
            .ToArray();

        acceptanceItems.Should().Contain(item =>
            item.Contains(ExpectedXUnitRef, StringComparison.Ordinal));
        acceptanceItems.Should().Contain(item =>
            item.Contains(ExpectedGdUnitRef, StringComparison.Ordinal));

        var testRefs = taskViews
            .SelectMany(static task => ReadStringArray(task, "test_refs"))
            .Distinct(StringComparer.Ordinal)
            .ToArray();

        testRefs.Should().Contain(ExpectedXUnitRef);
    }

    private static GameStartConfig CreateValidStartConfig()
    {
        return new GameStartConfig(
            MapId: "map001",
            PlayersCount: 4,
            StartingMoneyPreset: 10000,
            GlobalEventIntervalTurns: 10,
            RandomSeed: 24680,
            CharacterAssignments: CreateValidCharacterAssignments());
    }

    private static IReadOnlyDictionary<string, string> CreateValidCharacterAssignments()
    {
        return new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["p1"] = "c_liu_bei",
            ["ai-1"] = "c_cao_cao",
            ["ai-2"] = "c_sun_quan",
            ["ai-3"] = "c_yuan_shao",
        };
    }

    private static SanguoGameStarted CreateGameStartedPayload(GameStartConfig cfg)
    {
        var playerOrder = cfg.CharacterAssignments.Keys
            .OrderBy(static id => id, StringComparer.Ordinal)
            .ToArray();

        return new SanguoGameStarted(
            GameId: "g-task93",
            MapId: cfg.MapId,
            PlayersCount: cfg.PlayersCount,
            StartingMoneyPreset: cfg.StartingMoneyPreset,
            GlobalEventIntervalTurns: cfg.GlobalEventIntervalTurns,
            RandomSeed: cfg.RandomSeed,
            RunMode: cfg.RunMode,
            CommanderId: cfg.CommanderId,
            Difficulty: cfg.Difficulty,
            PlayerOrder: playerOrder,
            CharacterAssignments: cfg.CharacterAssignments,
            ActiveStrategemId: cfg.ActiveStrategemId,
            PassiveStrategemId: cfg.PassiveStrategemId,
            OccurredAt: new DateTimeOffset(2026, 1, 1, 0, 0, 0, TimeSpan.Zero),
            CorrelationId: "corr-task93",
            CausationId: "ui.main_menu.start");
    }

    private static SanguoSaveSnapshot CreateValidSaveSnapshot()
    {
        return new SanguoSaveSnapshot(
            GameId: "g-task93",
            TurnNumber: 1,
            ActivePlayerIndex: 0,
            Year: 1,
            Month: 1,
            Day: 1,
            PlayerOrder: new[] { "p1", "ai-1", "ai-2", "ai-3" },
            Players: new[]
            {
                new SanguoSavePlayer("p1", 1000m, 0, false, new[] { "city_1" }),
                new SanguoSavePlayer("ai-1", 1000m, 1, false, Array.Empty<string>()),
                new SanguoSavePlayer("ai-2", 1000m, 2, false, Array.Empty<string>()),
                new SanguoSavePlayer("ai-3", 1000m, 3, false, Array.Empty<string>()),
            },
            CityEconomy: new[]
            {
                new SanguoSaveCityEconomy("city_1", 50m, 20m),
                new SanguoSaveCityEconomy("city_2", 50m, 20m),
            },
            TreasuryMinorUnits: 0,
            ContentPackId: "core_t2",
            ContentPackVersion: 1,
            RunMode: "campaign",
            CommanderId: "c_liu_bei",
            RandomSeed: 24680);
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var marker = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(marker))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }

    private static bool TryGetTaskByTaskmasterId(string repoRoot, string fileName, int taskmasterId, out JsonElement task)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", fileName);
        foreach (var candidate in doc.RootElement.EnumerateArray())
        {
            if (candidate.TryGetProperty("taskmaster_id", out var idProperty) &&
                idProperty.ValueKind == JsonValueKind.Number &&
                idProperty.TryGetInt32(out var idValue) &&
                idValue == taskmasterId)
            {
                task = candidate.Clone();
                return true;
            }
        }

        task = default;
        return false;
    }

    private static string[] ReadStringArray(JsonElement task, string propertyName)
    {
        task.TryGetProperty(propertyName, out var property)
            .Should().BeTrue($"Task {TaskId} must contain '{propertyName}'.");

        property.ValueKind.Should().Be(JsonValueKind.Array);

        return property
            .EnumerateArray()
            .Select(static item => item.GetString() ?? string.Empty)
            .ToArray();
    }

    private static JsonDocument LoadJson(string repoRoot, params string[] relativeParts)
    {
        var path = Path.Combine(new[] { repoRoot }.Concat(relativeParts).ToArray());
        using var stream = File.OpenRead(path);
        return JsonDocument.Parse(stream);
    }
}
