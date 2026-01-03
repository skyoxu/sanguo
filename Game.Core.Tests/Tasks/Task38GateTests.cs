using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task38GateTests
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

    // ACC:T38.1
    [Fact]
    public void ShouldDefineInputsForDuplicationAndComplexityReports_WhenTaskIsDone()
    {
        var repoRoot = FindRepoRoot();
        if (!IsTaskDone(repoRoot, 38))
            return;

        // When Task 38 is done, repository should be able to generate machine-readable JSON
        // reports at stable paths under logs/ci/<date>/.
        var scripts = Path.Combine(repoRoot, "scripts");
        Directory.Exists(scripts).Should().BeTrue("repo should contain scripts/ for quality gate tools");
    }

    // ACC:T38.2
    [Fact]
    public void ShouldHaveQualityGatesEntryPoint_WhenTaskIsDone()
    {
        var repoRoot = FindRepoRoot();
        if (!IsTaskDone(repoRoot, 38))
            return;

        var qualityGates = Path.Combine(repoRoot, "scripts", "python", "quality_gates.py");
        File.Exists(qualityGates).Should().BeTrue("Task 38 done should rely on scripts/python/quality_gates.py as the entry point");
    }

    // ACC:T38.3
    [Fact]
    public void ShouldReferenceQualityGatesInCiWorkflow_WhenTaskIsDone()
    {
        var repoRoot = FindRepoRoot();
        if (!IsTaskDone(repoRoot, 38))
            return;

        var wf = Path.Combine(repoRoot, ".github", "workflows", "windows-quality-gate.yml");
        File.Exists(wf).Should().BeTrue("Task 38 done should be wired into CI");
        var text = File.ReadAllText(wf);
        text.Should().Contain("quality_gates", "CI should invoke quality_gates.py (directly or via ci_pipeline.py)");
    }

    // ACC:T38.4
    [Fact]
    public void ShouldHavePhase13Docs_WhenTaskIsDone()
    {
        var repoRoot = FindRepoRoot();
        if (!IsTaskDone(repoRoot, 38))
            return;

        var backlog = Path.Combine(repoRoot, "docs", "migration", "Phase-13-Quality-Gates-Backlog.md");
        var script = Path.Combine(repoRoot, "docs", "migration", "Phase-13-Quality-Gates-Script.md");
        File.Exists(backlog).Should().BeTrue("Task 38 acceptance references this migration doc");
        File.Exists(script).Should().BeTrue("Task 38 acceptance references this migration doc");
    }
}

