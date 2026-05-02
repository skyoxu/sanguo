using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task94SplitIntegrationTests
{
    private const int TaskId = 94;
    private const string ExpectedCoreRef = "Game.Core.Tests/Tasks/Task94SplitIntegrationTests.cs";
    private const string ExpectedUiRef1 = "Tests.Godot/tests/UI/test_task94_new_game_setup_constraints_and_start.gd";
    private const string ExpectedUiRef2 = "Tests.Godot/tests/UI/test_task94_new_game_setup_starts_game_with_selected_players_and_money.gd";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T94.1
    [Fact]
    [Trait("acceptance", "ACC:T94.1")]
    public void ShouldKeepTaskSpecificIntegrationClosureEvidence_WhenReadingTask94FromBothViews()
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
            acceptance[0].Should().Contain("split tasks 121 and 122");
            acceptance[0].Should().Contain(ExpectedCoreRef);
            acceptance[0].Should().Contain(ExpectedUiRef1);
            acceptance[0].Should().Contain(ExpectedUiRef2);

            testRefs.Should().Contain(ExpectedCoreRef);
            testRefs.Should().Contain(ExpectedUiRef1);
            testRefs.Should().Contain(ExpectedUiRef2);

            chapterRefs.Should().Contain(new[] { "CH04", "CH05", "CH06", "CH10" });
            adrRefs.Should().Contain(new[] { "ADR-0004", "ADR-0010", "ADR-0020" });
        }
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
        using var stream = File.OpenRead(path);
        return JsonDocument.Parse(stream);
    }
}
