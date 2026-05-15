using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task228TripletBaselineValidatorsTests
{
    // ACC:T228.12
    [Fact]
    public void ShouldRecordEvidence_WhenValidatorsRunAfterTaskWrite()
    {
        var repoRoot = FindRepoRoot();
        var taskWriteAt = File.GetLastWriteTimeUtc(Path.Combine(repoRoot, ".taskmaster", "tasks", "tasks_back.json"));
        var outPath = CreateTempSummaryPath("task228-triplet-baseline-evidence");
        var result = RunTripletBaseline(outPath);

        result.ExitCode.Should().Be(0);
        File.Exists(outPath).Should().BeTrue("validator run should emit a summary artifact");

        using var stream = File.OpenRead(outPath);
        using var document = JsonDocument.Parse(stream);
        var root = document.RootElement;
        root.GetProperty("status").GetString().Should().Be("ok");

        var generatedAt = DateTimeOffset.Parse(
            root.GetProperty("generated_at_utc").GetString()!,
            CultureInfo.InvariantCulture,
            DateTimeStyles.AssumeUniversal);

        var policy = new TripletBaselineRunEvidencePolicy();
        var evidence = policy.Evaluate(taskWriteAt, generatedAt);
        evidence.IsAccepted.Should().BeTrue();
        evidence.Status.Should().Be("Recorded");
    }

    // ACC:T228.13
    [Fact]
    public void ShouldRejectEvidence_WhenValidatorsRunBeforeTaskWrite()
    {
        var taskWrittenAt = new DateTimeOffset(2026, 5, 15, 10, 0, 0, TimeSpan.Zero);
        var validatorsRunAt = taskWrittenAt.AddMinutes(-1);
        var policy = new TripletBaselineRunEvidencePolicy();

        var result = policy.Evaluate(taskWrittenAt.UtcDateTime, validatorsRunAt);

        result.IsAccepted.Should().BeFalse();
        result.Status.Should().Be("Refused");
    }

    private static string FindRepoRoot()
    {
        var cursor = new DirectoryInfo(AppContext.BaseDirectory);
        while (cursor is not null)
        {
            var agentsPath = Path.Combine(cursor.FullName, "AGENTS.md");
            var scriptPath = Path.Combine(cursor.FullName, "scripts", "python", "run_task_triplet_baseline.py");
            if (File.Exists(agentsPath) && File.Exists(scriptPath))
            {
                return cursor.FullName;
            }

            cursor = cursor.Parent;
        }

        throw new DirectoryNotFoundException("Repository root not found from test base directory.");
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

    private sealed class TripletBaselineRunEvidencePolicy
    {
        public ValidationResult Evaluate(DateTime taskWrittenAtUtc, DateTimeOffset validatorsRunAt)
        {
            var isAccepted = validatorsRunAt.UtcDateTime >= taskWrittenAtUtc;
            var status = isAccepted ? "Recorded" : "Refused";
            return new ValidationResult(isAccepted, status);
        }
    }

    private readonly record struct ValidationResult(bool IsAccepted, string Status);

    private readonly record struct ScriptRunResult(
        int ExitCode,
        string Stdout,
        string Stderr);
}
