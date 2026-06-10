using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task206TaskViewEvidenceTests
{
    private static readonly string[] ExpectedAnchors =
    {
        "REQ-943e3e409bd8",
        "REQ-e0579534b553",
        "REQ-9d056b5790b7",
        "REQ-4f8bfa3615cd",
    };

    // ACC:T206.5
    [Fact]
    public void ShouldRequireExecutableEvidenceRefs_WhenTask206AcceptanceIsValidated()
    {
        var repoRoot = FindRepoRoot();
        var task = LoadTask206(repoRoot);
        var acceptance = task.GetProperty("acceptance").EnumerateArray()
            .Select(item => item.GetString() ?? string.Empty)
            .ToArray();

        acceptance.Should().HaveCount(9);
        acceptance.Should().OnlyContain(item => item.Contains("Refs:", StringComparison.Ordinal));

        var refs = ExtractRefs(acceptance).Distinct(StringComparer.Ordinal).ToArray();
        refs.Should().NotBeEmpty();
        refs.Should().OnlyContain(path =>
            File.Exists(Path.Combine(repoRoot, path.Replace('/', Path.DirectorySeparatorChar))));
    }

    // ACC:T206.6
    [Fact]
    public void ShouldPreserveTask206AcceptanceOrdering_WhenEvidenceRefsAreWritten()
    {
        var repoRoot = FindRepoRoot();
        var task = LoadTask206(repoRoot);
        var acceptance = task.GetProperty("acceptance").EnumerateArray()
            .Select(item => item.GetString() ?? string.Empty)
            .ToArray();

        acceptance.Take(ExpectedAnchors.Length)
            .Select(item => ExpectedAnchors.FirstOrDefault(anchor => item.Contains(anchor, StringComparison.Ordinal)) ?? string.Empty)
            .Should()
            .Equal(ExpectedAnchors);

        acceptance[4].Should().Contain("deterministic validation", "the fifth item tracks the evidence validation obligation");
        acceptance[5].Should().Contain("acceptance evidence", "the sixth item tracks generated task-view evidence stability");
    }

    private static JsonElement LoadTask206(string repoRoot)
    {
        var path = Path.Combine(repoRoot, ".taskmaster", "tasks", "tasks_gameplay.json");
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        foreach (var item in document.RootElement.EnumerateArray())
        {
            if (item.TryGetProperty("taskmaster_id", out var id) && id.GetInt32() == 206)
            {
                return item.Clone();
            }
        }

        throw new InvalidOperationException("Task 206 was not found in tasks_gameplay.json.");
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(Directory.GetCurrentDirectory());
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks_gameplay.json");
            if (File.Exists(candidate))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repository root with .taskmaster/tasks/tasks_gameplay.json was not found.");
    }

    private static string[] ExtractRefs(string[] acceptance)
    {
        return acceptance
            .SelectMany(item => item.Split("Refs:", 2, StringSplitOptions.None).Skip(1))
            .SelectMany(rest => rest.Split(' ', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
            .Where(path => path.Contains('/', StringComparison.Ordinal) || path.Contains('\\', StringComparison.Ordinal))
            .ToArray();
    }
}
