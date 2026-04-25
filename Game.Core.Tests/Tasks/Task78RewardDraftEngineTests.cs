using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task78RewardDraftEngineTests
{
    // ACC:T78.1
    [Theory]
    [InlineData(".taskmaster/tasks/tasks_back.json", "SG-0119", "SG-0120")]
    [InlineData(".taskmaster/tasks/tasks_gameplay.json", "GM-0119", "GM-0120")]
    [Trait("acceptance", "ACC:T78.1")]
    public void ShouldCloseMasterTaskEvidence_WhenSplitImplementationsAreFullyReferenced(string taskViewPath, string splitTask119Id, string splitTask120Id)
    {
        var tasks = LoadTaskEntries(taskViewPath);
        var masterTask = tasks.Single(task => task.TaskmasterId == 78);
        var splitTask119 = tasks.Single(task => task.TaskmasterId == 119);
        var splitTask120 = tasks.Single(task => task.TaskmasterId == 120);

        var report = EvaluateClosure(masterTask, splitTask119, splitTask120, splitTask119Id, splitTask120Id);

        report.IsClosed.Should().BeTrue(report.FormatFailureMessage());
    }

    // ACC:T78.1
    [Fact]
    [Trait("acceptance", "ACC:T78.1")]
    public void ShouldKeepMasterTaskOpen_WhenSplitEvidenceIsMissing()
    {
        var masterTask = new TaskEntry(
            TaskmasterId: 78,
            Id: "GM-0078",
            DependsOn: new[] { "GM-0119", "GM-0120" },
            Acceptance: new[]
            {
                "Integration closure verifies that split tasks 119 and 120 supply the RewardDraftEngine implementation evidence required by task 78, and that no remaining implementation work is left on this master task. Refs: Game.Core.Tests/Tasks/Task78RewardDraftEngineTests.cs",
            },
            TestRefs: new[]
            {
                "Game.Core.Tests/Tasks/Task78RewardDraftEngineTests.cs",
            });

        var splitTask119 = new TaskEntry(
            TaskmasterId: 119,
            Id: "GM-0119",
            DependsOn: Array.Empty<string>(),
            Acceptance: Array.Empty<string>(),
            TestRefs: new[]
            {
                "Game.Core.Tests/Tasks/Task119RewardDraftCandidateDeterminismTests.cs",
            });

        var splitTask120 = new TaskEntry(
            TaskmasterId: 120,
            Id: "GM-0120",
            DependsOn: new[] { "GM-0119" },
            Acceptance: Array.Empty<string>(),
            TestRefs: new[]
            {
                "Game.Core.Tests/Tasks/Task120SplitTests.cs",
            });

        var report = EvaluateClosure(masterTask, splitTask119, splitTask120, "GM-0119", "GM-0120");

        report.IsClosed.Should().BeFalse("Task 78 must stay open until the master task aggregates the split implementation evidence");
        report.MissingEvidence.Should().Contain("missing master test ref: Game.Core.Tests/Tasks/Task78SplitIntegrationTests.cs");
    }

    private static ClosureReport EvaluateClosure(TaskEntry masterTask, TaskEntry splitTask119, TaskEntry splitTask120, string expectedSplit119Id, string expectedSplit120Id)
    {
        var missingEvidence = new List<string>();

        if (!masterTask.DependsOn.Contains(expectedSplit119Id, StringComparer.Ordinal))
        {
            missingEvidence.Add($"missing dependency: {expectedSplit119Id}");
        }

        if (!masterTask.DependsOn.Contains(expectedSplit120Id, StringComparer.Ordinal))
        {
            missingEvidence.Add($"missing dependency: {expectedSplit120Id}");
        }

        if (splitTask119.TestRefs.Count == 0)
        {
            missingEvidence.Add($"split task {splitTask119.Id} has no implementation evidence");
        }

        if (splitTask120.TestRefs.Count == 0)
        {
            missingEvidence.Add($"split task {splitTask120.Id} has no implementation evidence");
        }

        var requiredMasterRefs = new HashSet<string>(ExtractAcceptanceRefs(masterTask.Acceptance), StringComparer.Ordinal)
        {
            NormalizePath("Game.Core.Tests/Tasks/Task78RewardDraftEngineTests.cs"),
            NormalizePath("Game.Core.Tests/Tasks/Task78SplitIntegrationTests.cs"),
        };

        var normalizedMasterRefs = new HashSet<string>(masterTask.TestRefs.Select(NormalizePath), StringComparer.Ordinal);
        foreach (var requiredRef in requiredMasterRefs.OrderBy(path => path, StringComparer.Ordinal))
        {
            if (!normalizedMasterRefs.Contains(requiredRef))
            {
                missingEvidence.Add($"missing master test ref: {requiredRef}");
            }
        }

        return new ClosureReport(missingEvidence.Count == 0, missingEvidence);
    }

    private static IReadOnlyList<TaskEntry> LoadTaskEntries(string taskViewPath)
    {
        var repoRoot = FindRepoRoot();
        var absolutePath = Path.Combine(repoRoot, taskViewPath.Replace('/', Path.DirectorySeparatorChar));
        var json = File.ReadAllText(absolutePath);

        using var document = JsonDocument.Parse(json);
        if (document.RootElement.ValueKind == JsonValueKind.Array)
        {
            return document.RootElement.EnumerateArray().Select(ParseTaskEntry).ToArray();
        }

        if (document.RootElement.ValueKind == JsonValueKind.Object &&
            document.RootElement.TryGetProperty("tasks", out var tasksElement) &&
            tasksElement.ValueKind == JsonValueKind.Array)
        {
            return tasksElement.EnumerateArray().Select(ParseTaskEntry).ToArray();
        }

        throw new InvalidOperationException($"Unsupported task view shape in '{taskViewPath}'.");
    }

    private static TaskEntry ParseTaskEntry(JsonElement element)
    {
        return new TaskEntry(
            TaskmasterId: element.GetProperty("taskmaster_id").GetInt32(),
            Id: element.GetProperty("id").GetString() ?? string.Empty,
            DependsOn: ReadStringArray(element, "depends_on"),
            Acceptance: ReadStringArray(element, "acceptance"),
            TestRefs: ReadStringArray(element, "test_refs"));
    }

    private static string[] ReadStringArray(JsonElement element, string propertyName)
    {
        if (!element.TryGetProperty(propertyName, out var property) || property.ValueKind != JsonValueKind.Array)
        {
            return Array.Empty<string>();
        }

        return property
            .EnumerateArray()
            .Where(item => item.ValueKind == JsonValueKind.String)
            .Select(item => item.GetString() ?? string.Empty)
            .Where(value => !string.IsNullOrWhiteSpace(value))
            .Select(NormalizePath)
            .ToArray();
    }

    private static IReadOnlyList<string> ExtractAcceptanceRefs(IEnumerable<string> acceptanceItems)
    {
        var refs = new HashSet<string>(StringComparer.Ordinal);

        foreach (var acceptanceItem in acceptanceItems)
        {
            var markerIndex = acceptanceItem.IndexOf("Refs:", StringComparison.OrdinalIgnoreCase);
            if (markerIndex < 0)
            {
                continue;
            }

            var refsSection = acceptanceItem[(markerIndex + "Refs:".Length)..];
            var tokens = refsSection.Split(new[] { ',', ' ', '\t', '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
            foreach (var token in tokens)
            {
                var normalizedToken = NormalizePath(token.Trim());
                if (normalizedToken.EndsWith(".cs", StringComparison.OrdinalIgnoreCase) ||
                    normalizedToken.EndsWith(".gd", StringComparison.OrdinalIgnoreCase))
                {
                    refs.Add(normalizedToken);
                }
            }
        }

        return refs.ToArray();
    }

    private static string FindRepoRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            var taskmasterDirectory = Path.Combine(current.FullName, ".taskmaster");
            if (Directory.Exists(taskmasterDirectory))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("Could not locate the repository root from the current test base directory.");
    }

    private static string NormalizePath(string path)
    {
        return path.Replace('\\', '/').Trim();
    }

    private sealed record TaskEntry(
        int TaskmasterId,
        string Id,
        IReadOnlyList<string> DependsOn,
        IReadOnlyList<string> Acceptance,
        IReadOnlyList<string> TestRefs);

    private sealed record ClosureReport(bool IsClosed, IReadOnlyList<string> MissingEvidence)
    {
        public string FormatFailureMessage()
        {
            return MissingEvidence.Count == 0
                ? "Task 78 closure evidence is complete."
                : "Expected Task 78 closure evidence to be complete, but " + string.Join("; ", MissingEvidence);
        }
    }
}
