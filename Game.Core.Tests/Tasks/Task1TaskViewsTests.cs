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

    private static List<int> LoadTasksJsonIds(string repoRoot)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", "tasks.json");
        var tasks = doc.RootElement.GetProperty("master").GetProperty("tasks");
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

        using var tasks = LoadJson(repoRoot, ".taskmaster", "tasks", "tasks.json");
        tasks.RootElement.TryGetProperty("master", out _).Should().BeTrue("tasks.json must have master");

        using var back = LoadJson(repoRoot, ".taskmaster", "tasks", "tasks_back.json");
        back.RootElement.ValueKind.Should().Be(JsonValueKind.Array);

        using var gameplay = LoadJson(repoRoot, ".taskmaster", "tasks", "tasks_gameplay.json");
        gameplay.RootElement.ValueKind.Should().Be(JsonValueKind.Array);
    }

    // ACC:T1.2
    [Fact]
    public void ShouldHaveOneToOneTaskIdMappingAcrossViews_WhenValidatingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        var masterIds = LoadTasksJsonIds(repoRoot);
        var backIds = LoadViewTaskmasterIds(repoRoot, "tasks_back.json");
        var gameplayIds = LoadViewTaskmasterIds(repoRoot, "tasks_gameplay.json");

        backIds.Count.Should().BeGreaterThan(0);
        gameplayIds.Count.Should().BeGreaterThan(0);

        foreach (var id in masterIds)
        {
            (backIds.Contains(id) || gameplayIds.Contains(id)).Should().BeTrue(
                $"each tasks.json id must exist in at least one view (id={id})");
        }
    }
}

