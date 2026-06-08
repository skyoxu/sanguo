using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task202EvidenceTests
{
    // ACC:T202.4
    // ACC:T202.11
    // ACC:T202.12
    // ACC:T202.13
    // ACC:T202.14
    [Fact]
    public void ShouldRecordTask202CompletedCapabilitySurfaceEvidence_WhenTask202IsLoaded()
    {
        var task = LoadTask202();
        var acceptance = GetStringArray(task, "acceptance");

        acceptance.Should().Contain(item => item.Contains("single governed planning surface", StringComparison.Ordinal)
            && item.Contains("completed task capabilities", StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal));
        acceptance.Should().Contain(item => item.Contains("ownership-facing responsibility", StringComparison.Ordinal)
            && item.Contains("completion state", StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal));
    }

    // ACC:T202.15
    // ACC:T202.16
    // ACC:T202.17
    [Fact]
    public void ShouldRecordTask202AuditAndTripletValidatorEvidence_WhenTask202IsLoaded()
    {
        var acceptance = GetStringArray(LoadTask202(), "acceptance");

        acceptance.Should().Contain(item => item.Contains("[OBL:T202.O6]", StringComparison.Ordinal)
            && item.Contains("logs/ci/2026-06-08/sc-analyze/summary.json", StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal));
        acceptance.Should().Contain(item => item.Contains("[OBL:T202.O7]", StringComparison.Ordinal)
            && item.Contains("logs/ci/2026-06-08/sc-analyze/validate_task_master_triplet.log", StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal));
    }

    private static JsonElement LoadTask202()
    {
        var repoRoot = FindRepoRoot();
        var jsonPath = Path.Combine(repoRoot, ".taskmaster", "tasks", "tasks_gameplay.json");
        using var document = JsonDocument.Parse(File.ReadAllText(jsonPath));

        foreach (var task in document.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var id) && id.GetInt32() == 202)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException("Task 202 was not found in tasks_gameplay.json.");
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
