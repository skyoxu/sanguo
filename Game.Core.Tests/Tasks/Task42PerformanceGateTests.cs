using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task42PerformanceGateTests
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

    private static bool IsTaskDone(string repoRoot, int taskId)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", "tasks.json");
        doc.RootElement.TryGetProperty("master", out var master).Should().BeTrue("tasks.json must have master");
        master.TryGetProperty("tasks", out var tasks).Should().BeTrue("tasks.json master must have tasks");
        tasks.ValueKind.Should().Be(JsonValueKind.Array);

        foreach (var t in tasks.EnumerateArray())
        {
            var idText = t.GetProperty("id").GetString() ?? string.Empty;
            if (!int.TryParse(idText, out var id))
                continue;
            if (id != taskId)
                continue;

            var status = t.GetProperty("status").GetString() ?? string.Empty;
            return string.Equals(status, "done", StringComparison.OrdinalIgnoreCase);
        }

        return false;
    }

    private static string ReadAllTextIfExists(string path)
    {
        return File.Exists(path) ? File.ReadAllText(path) : string.Empty;
    }

    // ACC:T42.1
    [Fact]
    public void ShouldHaveIndependentPerformanceGatesWorkflow_WhenTaskIsDone()
    {
        var repoRoot = FindRepoRoot();
        if (!IsTaskDone(repoRoot, 42))
        {
            return;
        }

        var wf = Path.Combine(repoRoot, ".github", "workflows", "performance-gates.yml");
        File.Exists(wf).Should().BeTrue("Task 42 done requires an independent performance-gates.yml workflow");
    }

    // ACC:T42.2
    [Fact]
    public void ShouldNotRunBuildOrTestSteps_InPerformanceGatesWorkflow_WhenTaskIsDone()
    {
        var repoRoot = FindRepoRoot();
        if (!IsTaskDone(repoRoot, 42))
        {
            return;
        }

        var wf = Path.Combine(repoRoot, ".github", "workflows", "performance-gates.yml");
        var text = ReadAllTextIfExists(wf);
        text.Should().NotBeNullOrWhiteSpace("Task 42 done requires performance-gates.yml content");
        text.Should().NotContain("dotnet test", "performance-gates workflow should not run unit tests");
        text.Should().NotContain("dotnet build", "performance-gates workflow should not duplicate build steps");
    }

    // ACC:T42.3
    [Fact]
    public void ShouldEmitPerformanceGatesSummaryJson_WhenTaskIsDone()
    {
        var repoRoot = FindRepoRoot();
        if (!IsTaskDone(repoRoot, 42))
        {
            return;
        }

        var wf = Path.Combine(repoRoot, ".github", "workflows", "performance-gates.yml");
        var text = ReadAllTextIfExists(wf);
        text.Should().Contain("performance-gates-summary.json", "workflow should reference a summary json output path");
    }

    // ACC:T42.4
    [Fact]
    public void ShouldHaveMigrationDocReference_WhenTaskIsDone()
    {
        var repoRoot = FindRepoRoot();
        if (!IsTaskDone(repoRoot, 42))
        {
            return;
        }

        var doc = Path.Combine(repoRoot, "docs", "migration", "Phase-15-Performance-Budgets-Backlog.md");
        File.Exists(doc).Should().BeTrue("Task 42 acceptance references this migration doc");
    }
}
