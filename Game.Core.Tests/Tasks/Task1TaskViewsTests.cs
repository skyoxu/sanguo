using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task1TaskViewsTests
{
    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var tm = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(tm))
                return dir.FullName;
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

    private static JsonElement GetTasksArrayFromTasksJson(string repoRoot)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", "tasks.json");
        doc.RootElement.TryGetProperty("master", out var master).Should().BeTrue("tasks.json must have master");
        master.TryGetProperty("tasks", out var tasks).Should().BeTrue("tasks.json master must have tasks");
        tasks.ValueKind.Should().Be(JsonValueKind.Array);
        return tasks.Clone();
    }

    private static List<int> LoadTasksJsonIds(string repoRoot)
    {
        var tasks = GetTasksArrayFromTasksJson(repoRoot);
        var ids = new List<int>(tasks.GetArrayLength());

        foreach (var t in tasks.EnumerateArray())
        {
            var idText = t.GetProperty("id").GetString();
            int.TryParse(idText, out var id).Should().BeTrue($"tasks.json id must be an int-like string (id={idText})");
            ids.Add(id);
        }

        ids.Distinct().Count().Should().Be(ids.Count, "tasks.json must not contain duplicate task ids");
        return ids;
    }

    private static HashSet<int> LoadViewTaskmasterIds(string repoRoot, string fileName)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", fileName);
        doc.RootElement.ValueKind.Should().Be(JsonValueKind.Array);

        var ids = new List<int>();
        foreach (var t in doc.RootElement.EnumerateArray())
        {
            t.TryGetProperty("taskmaster_id", out var tidProp).Should().BeTrue($"{fileName} entries must contain taskmaster_id");
            tidProp.ValueKind.Should().Be(JsonValueKind.Number);
            ids.Add(tidProp.GetInt32());
        }

        ids.Distinct().Count().Should().Be(ids.Count, $"{fileName} must not contain duplicate taskmaster_id values");
        return ids.ToHashSet();
    }

    // ACC:T1.1
    [Fact]
    public void ShouldParseTaskTripletFilesAndBasicFields_WhenValidatingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        var tasks = GetTasksArrayFromTasksJson(repoRoot);
        tasks.GetArrayLength().Should().BeGreaterThan(0);
        foreach (var t in tasks.EnumerateArray())
        {
            t.TryGetProperty("id", out var idProp).Should().BeTrue("tasks.json tasks entries must contain id");
            idProp.ValueKind.Should().Be(JsonValueKind.String);

            t.TryGetProperty("status", out var statusProp).Should().BeTrue("tasks.json tasks entries must contain status");
            statusProp.ValueKind.Should().Be(JsonValueKind.String);
            statusProp.GetString().Should().NotBeNullOrWhiteSpace();
        }

        using var back = LoadJson(repoRoot, ".taskmaster", "tasks", "tasks_back.json");
        back.RootElement.ValueKind.Should().Be(JsonValueKind.Array);
        foreach (var t in back.RootElement.EnumerateArray())
        {
            t.TryGetProperty("id", out var idProp).Should().BeTrue("tasks_back.json entries must contain id");
            idProp.ValueKind.Should().Be(JsonValueKind.String);
            idProp.GetString().Should().NotBeNullOrWhiteSpace();

            t.TryGetProperty("status", out var statusProp).Should().BeTrue("tasks_back.json entries must contain status");
            statusProp.ValueKind.Should().Be(JsonValueKind.String);
            statusProp.GetString().Should().NotBeNullOrWhiteSpace();

            t.TryGetProperty("taskmaster_id", out var tidProp).Should().BeTrue("tasks_back.json entries must contain taskmaster_id");
            tidProp.ValueKind.Should().Be(JsonValueKind.Number);
        }

        using var gameplay = LoadJson(repoRoot, ".taskmaster", "tasks", "tasks_gameplay.json");
        gameplay.RootElement.ValueKind.Should().Be(JsonValueKind.Array);
        foreach (var t in gameplay.RootElement.EnumerateArray())
        {
            t.TryGetProperty("id", out var idProp).Should().BeTrue("tasks_gameplay.json entries must contain id");
            idProp.ValueKind.Should().Be(JsonValueKind.String);
            idProp.GetString().Should().NotBeNullOrWhiteSpace();

            t.TryGetProperty("status", out var statusProp).Should().BeTrue("tasks_gameplay.json entries must contain status");
            statusProp.ValueKind.Should().Be(JsonValueKind.String);
            statusProp.GetString().Should().NotBeNullOrWhiteSpace();

            t.TryGetProperty("taskmaster_id", out var tidProp).Should().BeTrue("tasks_gameplay.json entries must contain taskmaster_id");
            tidProp.ValueKind.Should().Be(JsonValueKind.Number);
        }
    }

    // ACC:T1.2
    // ACC:T1.3
    [Fact]
    public void ShouldHaveOneToOneTaskIdMappingAcrossViews_WhenValidatingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        var masterIds = LoadTasksJsonIds(repoRoot);
        var masterIdSet = masterIds.ToHashSet();
        var backIds = LoadViewTaskmasterIds(repoRoot, "tasks_back.json");
        var gameplayIds = LoadViewTaskmasterIds(repoRoot, "tasks_gameplay.json");

        (backIds.Count > 0 || gameplayIds.Count > 0).Should().BeTrue("at least one task view must exist (back or gameplay)");

        foreach (var id in backIds)
            masterIdSet.Contains(id).Should().BeTrue($"each view taskmaster_id must exist in tasks.json (id={id})");
        foreach (var id in gameplayIds)
            masterIdSet.Contains(id).Should().BeTrue($"each view taskmaster_id must exist in tasks.json (id={id})");

        foreach (var id in masterIds)
        {
            (backIds.Contains(id) || gameplayIds.Contains(id)).Should().BeTrue(
                $"each tasks.json id must exist in at least one view (id={id})");
        }
    }
}
