using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task201EvidenceTests
{
    // ACC:T201.9
    // ACC:T201.10
    [Fact]
    public void ShouldRecordChapter3CoverageAuditEvidence_WhenTask201IsLoaded()
    {
        var acceptance = GetStringArray(LoadTask201(), "acceptance");

        acceptance.Should().Contain(item => item.Contains("[OBL:T201.O9]", StringComparison.Ordinal)
            && item.Contains("Chapter 3 coverage audit", StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal)
            && item.Contains("Game.Core.Tests/Tasks/Task201EvidenceTests.cs", StringComparison.Ordinal));
    }

    // ACC:T201.11
    // ACC:T201.12
    [Fact]
    public void ShouldRecordChapter38TripletValidatorEvidence_WhenTask201IsLoaded()
    {
        var acceptance = GetStringArray(LoadTask201(), "acceptance");

        acceptance.Should().Contain(item => item.Contains("[OBL:T201.O10]", StringComparison.Ordinal)
            && item.Contains("Chapter 3.8 triplet baseline validators", StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal)
            && item.Contains("Game.Core.Tests/Tasks/Task201EvidenceTests.cs", StringComparison.Ordinal));
    }

    private static JsonElement LoadTask201()
    {
        var repoRoot = FindRepoRoot();
        var jsonPath = Path.Combine(repoRoot, ".taskmaster", "tasks", "tasks_gameplay.json");
        using var document = JsonDocument.Parse(File.ReadAllText(jsonPath));

        foreach (var task in document.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var id) && id.GetInt32() == 201)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException("Task 201 was not found in tasks_gameplay.json.");
    }

    private static string FindRepoRoot()
    {
        var current = new DirectoryInfo(Directory.GetCurrentDirectory());
        while (current is not null)
        {
            if (Directory.Exists(Path.Combine(current.FullName, ".taskmaster")))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("Unable to locate repository root containing .taskmaster.");
    }

    private static string[] GetStringArray(JsonElement task, string propertyName)
    {
        task.TryGetProperty(propertyName, out var property).Should().BeTrue();
        property.ValueKind.Should().Be(JsonValueKind.Array);
        return property.EnumerateArray().Select(item => item.GetString() ?? string.Empty).ToArray();
    }
}
