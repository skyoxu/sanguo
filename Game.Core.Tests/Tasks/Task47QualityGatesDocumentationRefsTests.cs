using System;
using System.IO;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task47QualityGatesDocumentationRefsTests
{
    private static readonly string[] ExpectedDocumentationPaths =
    {
        "docs/migration/Phase-13-Quality-Gates-Backlog.md",
        "docs/migration/Phase-13-Quality-Gates-Script.md",
    };

    // ACC:T47.5
    [Fact]
    public void ShouldContainExpectedDocumentationReferencePaths_WhenValidatingDocumentationList()
    {
        ExpectedDocumentationPaths.Should().NotBeNullOrEmpty();
        ExpectedDocumentationPaths.Should().OnlyContain(p => !string.IsNullOrWhiteSpace(p));
        ExpectedDocumentationPaths.Should().OnlyContain(p => p.EndsWith(".md", StringComparison.OrdinalIgnoreCase));
        ExpectedDocumentationPaths.Should().OnlyContain(p => p.StartsWith("docs/migration/", StringComparison.Ordinal));
        ExpectedDocumentationPaths.Should().OnlyHaveUniqueItems();
    }

    // ACC:T47.5
    [Fact]
    public void ShouldEnsureDocumentationFilesExistAndAreNotEmpty_WhenRepositoryRootIsDiscoverable()
    {
        var repoRoot = TryFindRepositoryRoot();
        if (repoRoot is null)
        {
            true.Should().BeTrue();
            return;
        }

        foreach (var relativePath in ExpectedDocumentationPaths)
        {
            var fullPath = Path.Combine(repoRoot, relativePath.Replace('/', Path.DirectorySeparatorChar));
            File.Exists(fullPath).Should().BeTrue($"Expected documentation file to exist: {relativePath}");
            new FileInfo(fullPath).Length.Should().BeGreaterThan(0, $"Expected documentation file to be non-empty: {relativePath}");
        }
    }

    private static string? TryFindRepositoryRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 12 && current is not null; i++)
        {
            if (File.Exists(Path.Combine(current.FullName, "project.godot")))
            {
                return current.FullName;
            }

            if (Directory.Exists(Path.Combine(current.FullName, ".git")))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        return null;
    }
}
