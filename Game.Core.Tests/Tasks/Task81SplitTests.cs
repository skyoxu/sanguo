using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task81SplitTests
{
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

    private static JsonDocument LoadJson(string repoRoot, params string[] rel)
    {
        var path = Path.Combine(new[] { repoRoot }.Concat(rel).ToArray());
        var text = File.ReadAllText(path);
        return JsonDocument.Parse(text);
    }

    private static JsonElement GetTask81FromMaster(string repoRoot)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", "tasks.json");
        var tasks = doc.RootElement.GetProperty("master").GetProperty("tasks");
        foreach (var task in tasks.EnumerateArray())
        {
            if (task.TryGetProperty("id", out var id) && id.GetString() == "81")
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException("Task 81 not found in tasks.json");
    }

    private static JsonElement GetTask81FromView(string repoRoot, string fileName)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", fileName);
        foreach (var task in doc.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var id) && id.GetInt32() == 81)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException($"Task 81 not found in {fileName}");
    }

    [Fact]
    public void ShouldDeclareTaskScopedTestRefs_WhenTask81SplitRequiresContractEvidence()
    {
        var repoRoot = FindRepoRoot();
        var task = GetTask81FromMaster(repoRoot);

        task.TryGetProperty("testRefs", out var testRefs).Should().BeTrue("Task 81 must declare testRefs in tasks.json");
        testRefs.ValueKind.Should().Be(JsonValueKind.Array);

        var refs = testRefs.EnumerateArray().Select(static x => x.GetString() ?? string.Empty).ToList();
        refs.Should().Contain("Game.Core.Tests/Tasks/Task81SplitTests.cs");
        refs.Should().Contain("Tests.Godot/tests/UI/test_task81_event_result_popup.gd");
        refs.Should().Contain("Tests.Godot/tests/UI/test_task81_event_log_details_panel.gd");
    }

    [Fact]
    public void ShouldKeepA008SplitScopeInTaskViews_WhenValidatingTask81Acceptance()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewName in new[] { "tasks_back.json", "tasks_gameplay.json" })
        {
            var task = GetTask81FromView(repoRoot, viewName);
            task.GetProperty("acceptanceRefs").EnumerateArray().Select(static x => x.GetString()).Should().Contain("A-008");

            var acceptance = task.GetProperty("acceptance").EnumerateArray().Select(static x => x.GetString() ?? string.Empty).ToList();
            acceptance.Should().ContainSingle();
            acceptance[0].Should().Contain("test_task81_event_result_popup.gd");
            acceptance[0].Should().Contain("test_task81_event_log_details_panel.gd");
        }
    }
}
