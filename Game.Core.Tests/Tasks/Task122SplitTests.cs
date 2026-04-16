using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task122SplitTests
{
    private const int TaskId = 122;
    private const string ExpectedCoreRef = "Game.Core.Tests/Tasks/Task122SplitTests.cs";
    private const string ExpectedUiRef1 = "Tests.Godot/tests/UI/test_task122_new_game_setup_constraints_and_start.gd";
    private const string ExpectedUiRef2 = "Tests.Godot/tests/UI/test_task122_new_game_setup_starts_game_with_selected_players_and_money.gd";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    [Fact]
    [Trait("acceptance", "ACC:T122.1")]
    public void ShouldKeepTaskSpecificRefs_WhenReadingTask122FromBothViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");
            var chapterRefs = ReadStringArray(task, "chapter_refs");
            var adrRefs = ReadStringArray(task, "adr_refs");

            acceptance.Should().ContainSingle();
            acceptance[0].Should().Contain("active strategem and a passive strategem");
            acceptance[0].Should().Contain(ExpectedUiRef1);
            acceptance[0].Should().Contain(ExpectedUiRef2);

            testRefs.Should().Contain(ExpectedCoreRef);
            testRefs.Should().Contain(ExpectedUiRef1);
            testRefs.Should().Contain(ExpectedUiRef2);

            chapterRefs.Should().Contain(new[] { "CH04", "CH05", "CH06", "CH10" });
            adrRefs.Should().Contain(new[] { "ADR-0004", "ADR-0010", "ADR-0020" });
        }
    }

    [Fact]
    [Trait("acceptance", "ACC:T122.1")]
    public void ShouldRejectConfig_WhenActiveStrategemIsMissing()
    {
        var cfg = CreateValidConfig() with { ActiveStrategemId = "" };

        GameStartConfigValidator.TryValidate(cfg, out var errors).Should().BeFalse();
        errors.Should().Contain("active_strategem_id_empty");
    }

    [Fact]
    [Trait("acceptance", "ACC:T122.1")]
    public void ShouldRejectConfig_WhenPassiveStrategemIsMissing()
    {
        var cfg = CreateValidConfig() with { PassiveStrategemId = " " };

        GameStartConfigValidator.TryValidate(cfg, out var errors).Should().BeFalse();
        errors.Should().Contain("passive_strategem_id_empty");
    }

    [Fact]
    [Trait("acceptance", "ACC:T122.1")]
    public void ShouldAcceptConfig_WhenActiveAndPassiveStrategemsAreSelected()
    {
        var cfg = CreateValidConfig();

        GameStartConfigValidator.TryValidate(cfg, out var errors).Should().BeTrue();
        errors.Should().BeEmpty();
    }

    [Fact]
    [Trait("acceptance", "ACC:T122.1")]
    public void ShouldSerializeStrategemSelections_WhenUsingJsonSerializer()
    {
        var cfg = CreateValidConfig();

        var json = JsonSerializer.Serialize(cfg);
        var root = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(json);

        root.Should().NotBeNull();
        root!.Should().ContainKey("active_strategem_id");
        root.Should().ContainKey("passive_strategem_id");
        root["active_strategem_id"].GetString().Should().Be("strat_active_default");
        root["passive_strategem_id"].GetString().Should().Be("strat_passive_default");
        root.Should().NotContainKey("activeStrategemId");
        root.Should().NotContainKey("passiveStrategemId");
    }

    private static GameStartConfig CreateValidConfig()
    {
        return new GameStartConfig(
            MapId: "map001",
            PlayersCount: 4,
            StartingMoneyPreset: 10000,
            GlobalEventIntervalTurns: 10,
            RandomSeed: 12345,
            CharacterAssignments: new Dictionary<string, string>(StringComparer.Ordinal)
            {
                ["p1"] = "c_liu_bei",
                ["ai-1"] = "c_cao_cao",
                ["ai-2"] = "c_sun_quan",
                ["ai-3"] = "c_yuan_shao",
            },
            ActiveStrategemId: "strat_active_default",
            PassiveStrategemId: "strat_passive_default");
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

    private static JsonElement GetTaskByTaskmasterId(string repoRoot, string fileName, int taskmasterId)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", fileName);
        foreach (var task in doc.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var idProperty) &&
                idProperty.ValueKind == JsonValueKind.Number &&
                idProperty.TryGetInt32(out var idValue) &&
                idValue == taskmasterId)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException($"Task {taskmasterId} not found in {fileName}.");
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
        var text = File.ReadAllText(path);
        return JsonDocument.Parse(text);
    }
}
