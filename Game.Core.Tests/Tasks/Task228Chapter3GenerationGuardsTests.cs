using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task228Chapter3GenerationGuardsTests
{
    // ACC:T228.10
    [Fact]
    public void ShouldExcludeChapter4AndChapter5DerivedFields_WhenReadingRealTaskViewPayload()
    {
        var backTask = LoadBackTask(taskmasterId: 228);
        var masterTask = LoadMasterTask(taskId: 228);

        backTask.Should().ContainKey("taskmaster_id");
        backTask.Should().ContainKey("title");
        backTask.Should().NotContainKey("chapter4_overlay_refs");
        backTask.Should().NotContainKey("chapter5_semantic_review_tier");

        masterTask.Should().ContainKey("id");
        masterTask.Should().ContainKey("title");
        masterTask.Should().NotContainKey("chapter4_overlay_refs");
        masterTask.Should().NotContainKey("chapter5_semantic_review_tier");
    }

    // ACC:T228.11
    [Fact]
    public void ShouldKeepPersistedRecordUnchanged_WhenTripletBaselineValidatorsRunAfterTaskWrite()
    {
        var before = LoadBackTask(taskmasterId: 228);
        var outPath = CreateTempSummaryPath("task228-triplet-baseline");
        var scriptResult = RunTripletBaseline(outPath);

        scriptResult.ExitCode.Should().Be(0);
        File.Exists(outPath).Should().BeTrue("triplet baseline summary should be produced");

        var after = LoadBackTask(taskmasterId: 228);
        after.Keys.Should().Contain(before.Keys);
        after.Should().NotContainKey("chapter4_overlay_refs");
        after.Should().NotContainKey("chapter5_semantic_review_tier");
    }

    private static Dictionary<string, object?> LoadBackTask(int taskmasterId)
    {
        var repoRoot = FindRepoRoot();
        var path = Path.Combine(repoRoot, ".taskmaster", "tasks", "tasks_back.json");
        using var stream = File.OpenRead(path);
        using var document = JsonDocument.Parse(stream);
        foreach (var item in document.RootElement.EnumerateArray())
        {
            if (!item.TryGetProperty("taskmaster_id", out var id) || id.ValueKind != JsonValueKind.Number)
            {
                continue;
            }

            if (id.GetInt32() == taskmasterId)
            {
                return JsonSerializer.Deserialize<Dictionary<string, object?>>(item.GetRawText())!;
            }
        }

        throw new InvalidOperationException($"taskmaster_id={taskmasterId} not found in tasks_back.json");
    }

    private static Dictionary<string, object?> LoadMasterTask(int taskId)
    {
        var repoRoot = FindRepoRoot();
        var path = Path.Combine(repoRoot, ".taskmaster", "tasks", "tasks.json");
        using var stream = File.OpenRead(path);
        using var document = JsonDocument.Parse(stream);
        var tasks = document.RootElement.GetProperty("master").GetProperty("tasks");
        foreach (var item in tasks.EnumerateArray())
        {
            if (!item.TryGetProperty("id", out var id) || id.ValueKind != JsonValueKind.Number)
            {
                continue;
            }

            if (id.GetInt32() == taskId)
            {
                return JsonSerializer.Deserialize<Dictionary<string, object?>>(item.GetRawText())!;
            }
        }

        throw new InvalidOperationException($"id={taskId} not found in tasks.json master.tasks");
    }

    private static string CreateTempSummaryPath(string prefix)
    {
        var path = Path.Combine(Path.GetTempPath(), $"{prefix}-{Guid.NewGuid():N}", "summary.json");
        var directory = Path.GetDirectoryName(path) ?? throw new InvalidOperationException("Invalid summary path.");
        Directory.CreateDirectory(directory);
        return path;
    }

    private static ScriptRunResult RunTripletBaseline(string outPath)
    {
        var repoRoot = FindRepoRoot();
        var scriptPath = Path.Combine(repoRoot, "scripts", "python", "run_task_triplet_baseline.py");
        var psi = new ProcessStartInfo
        {
            FileName = "py",
            Arguments = $"-3 \"{scriptPath}\" --out \"{outPath}\"",
            WorkingDirectory = repoRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        using var process = Process.Start(psi) ?? throw new InvalidOperationException("Failed to start run_task_triplet_baseline.py");
        var stdout = process.StandardOutput.ReadToEnd();
        var stderr = process.StandardError.ReadToEnd();
        if (!process.WaitForExit(120_000))
        {
            try
            {
                process.Kill(entireProcessTree: true);
            }
            catch
            {
            }

            throw new TimeoutException("run_task_triplet_baseline.py timed out.");
        }

        return new ScriptRunResult(process.ExitCode, stdout, stderr);
    }

    private static string FindRepoRoot()
    {
        var cursor = new DirectoryInfo(AppContext.BaseDirectory);
        while (cursor is not null)
        {
            var agentsPath = Path.Combine(cursor.FullName, "AGENTS.md");
            var taskBackPath = Path.Combine(cursor.FullName, ".taskmaster", "tasks", "tasks_back.json");
            if (File.Exists(agentsPath) && File.Exists(taskBackPath))
            {
                return cursor.FullName;
            }

            cursor = cursor.Parent;
        }

        throw new DirectoryNotFoundException("Repository root not found from test base directory.");
    }

    private sealed record ScriptRunResult(
        int ExitCode,
        string Stdout,
        string Stderr);
}
