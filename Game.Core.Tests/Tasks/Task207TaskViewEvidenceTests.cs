using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task207TaskViewEvidenceTests
{
    // ACC:T207.7
    [Fact]
    public void ShouldBindValidatorRerunObligation_WhenTask207UsesExecutableTaskViewEvidence()
    {
        var repoRoot = FindRepoRoot();
        var task = LoadTask207(repoRoot);
        var acceptance = task.GetProperty("acceptance").EnumerateArray()
            .Select(item => item.GetString() ?? string.Empty)
            .ToArray();

        acceptance.Should().HaveCount(7);
        acceptance.Should().OnlyContain(item => item.Contains("Refs:", StringComparison.Ordinal));

        var validatorItem = acceptance[6];
        validatorItem.Should().Contain("task-scoped validation evidence");
        validatorItem.Should().Contain("Game.Core.Tests/Tasks/Task207TaskViewEvidenceTests.cs");

        var refs = ExtractRefs(new[] { validatorItem });
        refs.Should().ContainSingle("Game.Core.Tests/Tasks/Task207TaskViewEvidenceTests.cs");
        refs.Should().OnlyContain(path =>
            File.Exists(Path.Combine(repoRoot, path.Replace('/', Path.DirectorySeparatorChar))));
    }

    private static JsonElement LoadTask207(string repoRoot)
    {
        var path = Path.Combine(repoRoot, ".taskmaster", "tasks", "tasks_gameplay.json");
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        foreach (var item in document.RootElement.EnumerateArray())
        {
            if (item.TryGetProperty("taskmaster_id", out var id) && id.GetInt32() == 207)
            {
                return item.Clone();
            }
        }

        throw new InvalidOperationException("Task 207 was not found in tasks_gameplay.json.");
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
