#nullable enable

using System;
using System.IO;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task33MigrationDocsPresenceTests
{
    private static readonly string[] RequiredDocRelativePaths =
    {
        "docs/migration/Phase-17-Build-System-and-Godot-Export.md",
        "docs/migration/Phase-17-Build-Backlog.md",
        "docs/migration/Phase-17-Export-Checklist.md",
    };

    [Fact]
    public void ShouldHaveStableMigrationDocPaths_WhenValidated()
    {
        RequiredDocRelativePaths.Should().Equal(new[]
        {
            "docs/migration/Phase-17-Build-System-and-Godot-Export.md",
            "docs/migration/Phase-17-Build-Backlog.md",
            "docs/migration/Phase-17-Export-Checklist.md",
        });

        RequiredDocRelativePaths.Should().OnlyContain(p => !string.IsNullOrWhiteSpace(p));
        RequiredDocRelativePaths.Should().OnlyContain(p => p.StartsWith("docs/migration/", StringComparison.Ordinal));
        RequiredDocRelativePaths.Should().OnlyContain(p => p.EndsWith(".md", StringComparison.Ordinal));
        RequiredDocRelativePaths.Should().OnlyContain(p => !p.Contains('\\'));
    }

    // ACC:T33.5
    [Fact]
    public void ShouldFindMigrationDocsInDocsMigrationFolder_WhenPresent()
    {
        var repoRoot = TryFindRepoRoot();
        repoRoot.Should().NotBeNull("repo root should be discoverable from the test base directory");

        var migrationDir = Path.Combine(repoRoot!, "docs", "migration");
        Directory.Exists(migrationDir).Should().BeTrue("docs/migration should exist in this repo for Task 33 references");

        foreach (var rel in RequiredDocRelativePaths)
        {
            var fullPath = Path.Combine(repoRoot!, rel.Replace('/', Path.DirectorySeparatorChar));
            File.Exists(fullPath).Should().BeTrue($"Required migration doc must exist: {rel}");
        }
    }

    private static string? TryFindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var taskmaster = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            var projectGodot = Path.Combine(dir.FullName, "project.godot");

            if (File.Exists(taskmaster) || File.Exists(projectGodot))
                return dir.FullName;

            dir = dir.Parent;
        }

        return null;
    }
}
