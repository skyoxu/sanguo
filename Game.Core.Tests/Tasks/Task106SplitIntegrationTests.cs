using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task106SplitIntegrationTests
{
    private const int TaskId = 106;
    private const int SplitTask141 = 141;
    private const int SplitTask142 = 142;
    private const string ExpectedTaskRef = "Game.Core.Tests/Tasks/Task106SplitIntegrationTests.cs";
    private const string SplitTask141Ref = "Game.Core.Tests/Tasks/Task141ObjectiveRewardSourceTests.cs";
    private const string SplitTask142Ref = "Game.Core.Tests/Tasks/Task142ObjectiveRewardDraftDeterminismTests.cs";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T106.1
    [Fact]
    [Trait("acceptance", "ACC:T106.1")]
    public void ShouldBindTask106AcceptanceToBothSplitTasks_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");
            var task141Refs = ReadTaskTestRefs(repoRoot, viewFile, SplitTask141);
            var task142Refs = ReadTaskTestRefs(repoRoot, viewFile, SplitTask142);

            acceptance.Should().ContainSingle();
            acceptance[0].Should().Contain("both tasks 141 and 142");
            acceptance[0].Should().Contain("combined integration closure is achieved");
            acceptance[0].Should().Contain("evidence from only one split task does not satisfy this item");
            acceptance[0].Should().Contain("Task106SplitIntegrationTests.cs");

            testRefs.Should().Contain(ExpectedTaskRef);
            task141Refs.Should().Contain(SplitTask141Ref);
            task142Refs.Should().Contain(SplitTask142Ref);

            var task141Path = Path.Combine(repoRoot, SplitTask141Ref.Replace('/', Path.DirectorySeparatorChar));
            var task142Path = Path.Combine(repoRoot, SplitTask142Ref.Replace('/', Path.DirectorySeparatorChar));

            File.Exists(task141Path).Should().BeTrue("split task 141 evidence must exist in the repository");
            File.Exists(task142Path).Should().BeTrue("split task 142 evidence must exist in the repository");

            ContainsTokenInFile(task141Path, "ACC:T141.1").Should().BeTrue();
            ContainsTokenInFile(task142Path, "ACC:T142.1").Should().BeTrue();
        }
    }

    // ACC:T106.1
    [Fact]
    [Trait("acceptance", "ACC:T106.1")]
    public void ShouldReportClosureComplete_WhenBothSplitTasksProvideCompletedObjectiveRewardEvidence()
    {
        var task141Evidence = new SplitClosureEvidence(
            SplitTask141,
            SplitTask141Ref,
            "objective_reward",
            "R8:event|elite|boss",
            IsCompleted: true);
        var task142Evidence = new SplitClosureEvidence(
            SplitTask142,
            SplitTask142Ref,
            "objective_reward",
            "R8:event|elite|boss",
            IsCompleted: true);

        var outcome = CurrentTask106SplitIntegrationPack.Evaluate(task141Evidence, task142Evidence);

        outcome.IsClosed.Should().BeTrue();
        outcome.ClosureCode.Should().Be("objective_reward|R8:event|elite|boss");
        outcome.FailureCode.Should().BeNull();
    }

    // ACC:T106.1
    [Fact]
    [Trait("acceptance", "ACC:T106.1")]
    public void ShouldRemainOpen_WhenOnlyOneSplitTaskProvidesEvidence()
    {
        var task141Evidence = new SplitClosureEvidence(
            SplitTask141,
            SplitTask141Ref,
            "objective_reward",
            "R8:event|elite|boss",
            IsCompleted: true);

        var outcome = CurrentTask106SplitIntegrationPack.Evaluate(task141Evidence);

        outcome.IsClosed.Should().BeFalse("the master task explicitly requires combined closure from tasks 141 and 142");
        outcome.FailureCode.Should().Be("MISSING_SPLIT_TASK_EVIDENCE");
    }

    // ACC:T106.1
    [Fact]
    [Trait("acceptance", "ACC:T106.1")]
    public void ShouldRemainOpen_WhenSplitTasksDoNotShareTheSameIntegrationSignature()
    {
        var task141Evidence = new SplitClosureEvidence(
            SplitTask141,
            SplitTask141Ref,
            "objective_reward",
            "R8:event|elite|boss",
            IsCompleted: true);
        var task142Evidence = new SplitClosureEvidence(
            SplitTask142,
            SplitTask142Ref,
            "objective_reward",
            "R8:event|elite",
            IsCompleted: true);

        var outcome = CurrentTask106SplitIntegrationPack.Evaluate(task141Evidence, task142Evidence);

        outcome.IsClosed.Should().BeFalse("combined integration closure requires the same deterministic integration signature from both split tasks");
        outcome.FailureCode.Should().Be("MISMATCHED_INTEGRATION_SIGNATURE");
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var marker = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(marker))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }

    private static JsonElement GetTaskByTaskmasterId(string repoRoot, string fileName, int taskmasterId)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", fileName);
        foreach (var task in doc.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var idProperty) &&
                idProperty.ValueKind == JsonValueKind.Number &&
                idProperty.TryGetInt32(out var idValue) &&
                idValue == taskmasterId)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException($"Task {taskmasterId} not found in {fileName}.");
    }

    private static string[] ReadTaskTestRefs(string repoRoot, string fileName, int taskmasterId)
    {
        var task = GetTaskByTaskmasterId(repoRoot, fileName, taskmasterId);
        return ReadStringArray(task, "test_refs");
    }

    private static string[] ReadStringArray(JsonElement task, string propertyName)
    {
        task.TryGetProperty(propertyName, out var property)
            .Should().BeTrue($"Task {TaskId} must contain '{propertyName}'.");

        property.ValueKind.Should().Be(JsonValueKind.Array);

        return property
            .EnumerateArray()
            .Select(static item => item.GetString() ?? string.Empty)
            .ToArray();
    }

    private static JsonDocument LoadJson(string repoRoot, params string[] relativeParts)
    {
        var path = Path.Combine(new[] { repoRoot }.Concat(relativeParts).ToArray());
        using var stream = File.OpenRead(path);
        return JsonDocument.Parse(stream);
    }

    private static bool ContainsTokenInFile(string path, string token)
    {
        foreach (var line in File.ReadLines(path))
        {
            if (line.Contains(token, StringComparison.Ordinal))
            {
                return true;
            }
        }

        return false;
    }

    private sealed record SplitClosureEvidence(
        int SplitTaskId,
        string SourcePath,
        string SourceTag,
        string IntegrationSignature,
        bool IsCompleted);

    private sealed record ClosureOutcome(bool IsClosed, string ClosureCode, string? FailureCode);

    private static class CurrentTask106SplitIntegrationPack
    {
        public static ClosureOutcome Evaluate(params SplitClosureEvidence[] evidence)
        {
            evidence.Should().NotBeNull();
            evidence.Should().NotBeEmpty();

            var nonTestEvidence = evidence.FirstOrDefault(item => !IsTaskScopedTestPath(item.SourcePath));
            if (nonTestEvidence is not null)
            {
                return new ClosureOutcome(false, string.Empty, "NON_TEST_EVIDENCE_PATH");
            }

            var splitTaskIds = evidence
                .Select(item => item.SplitTaskId)
                .ToHashSet();

            var hasTask141Evidence = splitTaskIds.Contains(SplitTask141);
            var hasTask142Evidence = splitTaskIds.Contains(SplitTask142);

            if (evidence.Any(item => !item.IsCompleted))
            {
                return new ClosureOutcome(false, string.Empty, "INCOMPLETE_SPLIT_EVIDENCE");
            }

            var sourceTags = evidence
                .Select(item => item.SourceTag)
                .Where(static tag => !string.IsNullOrWhiteSpace(tag))
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            if (sourceTags.Length != 1)
            {
                return new ClosureOutcome(false, string.Empty, "MISMATCHED_SOURCE_TAG");
            }

            var signatures = evidence
                .Select(item => item.IntegrationSignature)
                .Where(static signature => !string.IsNullOrWhiteSpace(signature))
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            if (signatures.Length != 1)
            {
                return new ClosureOutcome(false, string.Empty, "MISMATCHED_INTEGRATION_SIGNATURE");
            }

            var hasMinimumRequiredEvidence = hasTask141Evidence && hasTask142Evidence;
            if (!hasMinimumRequiredEvidence)
            {
                return new ClosureOutcome(false, string.Empty, "MISSING_SPLIT_TASK_EVIDENCE");
            }

            var closureCode = $"{sourceTags[0]}|{signatures[0]}";
            return new ClosureOutcome(true, closureCode, null);
        }

        private static bool IsTaskScopedTestPath(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                return false;
            }

            var normalized = path.Replace('\\', '/');
            return normalized.StartsWith("Game.Core.Tests/Tasks/Task", StringComparison.Ordinal)
                && normalized.EndsWith(".cs", StringComparison.Ordinal);
        }
    }
}
