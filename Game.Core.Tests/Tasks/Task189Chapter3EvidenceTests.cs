using System;
using System.IO;
using System.Linq;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task189Chapter3EvidenceTests
{
    private const string TaskScopedTag = "task-189";

    // ACC:T189.12
    // ACC:T189.13
    [Fact]
    public void ShouldHaveCoverageAuditEvidence_WhenValidatingObligationO9()
    {
        var reportPath = ResolveNewestTaskScopedFileOrThrow("logs/ci", "check_tasks_all_refs-task-189.report.md");
        var report = File.ReadAllText(reportPath);

        reportPath.Should().Contain(TaskScopedTag);
        report.Should().Contain("Summary for tasks_back.json:");
        report.Should().Contain("Summary for tasks_gameplay.json:");
        report.Should().Contain("errors=0");
    }

    // ACC:T189.14
    // ACC:T189.15
    [Fact]
    public void ShouldHaveTripletBaselineEvidence_WhenValidatingObligationO10()
    {
        var reportPath = ResolveNewestTaskScopedFileOrThrow("logs/ci", "validate_task_master_triplet-task-189.report.md");
        var report = File.ReadAllText(reportPath);

        reportPath.Should().Contain(TaskScopedTag);
        report.Should().Contain("=== Taskmaster Triplet Validation ===");
        report.Should().Contain("Overall result: OK");
        report.Should().Contain("[Mapping] Validating mapping from tasks_back/tasks_gameplay to tasks.json (master)");
    }

    private static string ResolveNewestTaskScopedFileOrThrow(string rootRelativeDir, string fileName)
    {
        var root = FindRepoRoot();
        var scanRoot = Path.Combine(root, rootRelativeDir.Replace('/', Path.DirectorySeparatorChar));
        if (!Directory.Exists(scanRoot))
        {
            throw new DirectoryNotFoundException($"Scan root not found: {scanRoot}");
        }

        var normalizedName = fileName.Replace('/', Path.DirectorySeparatorChar);
        var candidate = Directory
            .EnumerateFiles(scanRoot, "*", SearchOption.AllDirectories)
            .Where(path => path.EndsWith(normalizedName, StringComparison.OrdinalIgnoreCase))
            .Select(path => new FileInfo(path))
            .OrderByDescending(info => info.LastWriteTimeUtc)
            .FirstOrDefault();

        if (candidate is null)
        {
            throw new FileNotFoundException($"Task-scoped evidence file not found: {fileName}");
        }

        return candidate.FullName;
    }

    private static string FindRepoRoot()
    {
        var cursor = new DirectoryInfo(AppContext.BaseDirectory);
        while (cursor is not null)
        {
            if (File.Exists(Path.Combine(cursor.FullName, "AGENTS.md")) &&
                Directory.Exists(Path.Combine(cursor.FullName, ".taskmaster", "tasks")))
            {
                return cursor.FullName;
            }

            cursor = cursor.Parent;
        }

        throw new DirectoryNotFoundException("Repository root not found from test base directory.");
    }
}
