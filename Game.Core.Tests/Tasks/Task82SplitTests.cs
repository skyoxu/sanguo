using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task82SplitTests
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
        using var stream = File.OpenRead(path);
        return JsonDocument.Parse(stream);
    }

    private static JsonElement GetTask82FromMaster(string repoRoot)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", "tasks.json");
        var tasks = doc.RootElement.GetProperty("master").GetProperty("tasks");
        foreach (var task in tasks.EnumerateArray())
        {
            if (task.TryGetProperty("id", out var id) && id.GetString() == "82")
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException("Task 82 not found in tasks.json");
    }

    private static JsonElement GetTask82FromView(string repoRoot, string fileName)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", fileName);
        foreach (var task in doc.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var id) && id.GetInt32() == 82)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException($"Task 82 not found in {fileName}");
    }

    [Fact]
    public void ShouldDeclareTaskScopedTestRefs_WhenTask82SplitRequiresWindowingEvidence()
    {
        var repoRoot = FindRepoRoot();
        var task = GetTask82FromMaster(repoRoot);

        task.TryGetProperty("testRefs", out var testRefs).Should().BeTrue("Task 82 must declare testRefs in tasks.json");
        testRefs.ValueKind.Should().Be(JsonValueKind.Array);

        var refs = testRefs.EnumerateArray().Select(static x => x.GetString() ?? string.Empty).ToList();
        refs.Should().Contain("Game.Core.Tests/Tasks/Task82SplitTests.cs");
        refs.Should().Contain("Tests.Godot/tests/UI/test_task82_event_log_windowing.gd");
        refs.Should().Contain("Tests.Godot/tests/UI/test_task82_event_log_windowing_details.gd");
    }

    // ACC:T82.2
    [Fact]
    public void ShouldKeepA009A010ScopeInTaskViews_WhenValidatingTask82Acceptance()
    {
        var repoRoot = FindRepoRoot();
        var legacyRefs = new[]
        {
            "test_event_log_details_panel.gd",
            "test_event_log_additional_details.gd",
        };

        foreach (var viewName in new[] { "tasks_back.json", "tasks_gameplay.json" })
        {
            var task = GetTask82FromView(repoRoot, viewName);

            task.GetProperty("acceptanceRefs").EnumerateArray().Select(static x => x.GetString()).Should().Contain("A-009~A-010");

            var acceptance = task.GetProperty("acceptance").EnumerateArray().Select(static x => x.GetString() ?? string.Empty).ToList();
            acceptance.Should().HaveCount(2);
            acceptance[0].Should().Contain("overflow/windowing behavior");
            acceptance[0].Should().Contain("test_task82_event_log_windowing.gd");
            acceptance[0].Should().Contain("test_task82_event_log_windowing_details.gd");
            acceptance[1].Should().Contain("Task82SplitTests.cs");

            acceptance.Should().OnlyContain(item => legacyRefs.All(legacy => !item.Contains(legacy, StringComparison.Ordinal)));

            var testRefs = task.GetProperty("test_refs").EnumerateArray().Select(static x => x.GetString() ?? string.Empty).ToList();
            testRefs.Should().Contain("Game.Core.Tests/Tasks/Task82SplitTests.cs");
            testRefs.Should().Contain("Tests.Godot/tests/UI/test_task82_event_log_windowing.gd");
            testRefs.Should().Contain("Tests.Godot/tests/UI/test_task82_event_log_windowing_details.gd");
            testRefs.Should().OnlyContain(item => legacyRefs.All(legacy => !item.Contains(legacy, StringComparison.Ordinal)));
        }
    }
}
