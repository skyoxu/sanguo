using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task111SplitIntegrationTests
{
    private const int TaskId = 111;
    private const int SplitTask149 = 149;
    private const int SplitTask150 = 150;
    private const string Task111Ref = "Game.Core.Tests/Tasks/Task111SplitIntegrationTests.cs";
    private const string SplitTask149Ref = "Game.Core.Tests/Tasks/Task149CampaignBossVictoryScenarioTests.cs";
    private const string SplitTask150Ref = "Game.Core.Tests/Tasks/Task150CampaignCampFailScenarioTests.cs";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T111.1
    [Fact]
    [Trait("acceptance", "ACC:T111.1")]
    public void ShouldBindTask111AcceptanceToTaskScopedIntegrationEvidence_WhenLoadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");
            var task149Refs = ReadTaskTestRefs(repoRoot, viewFile, SplitTask149);
            var task150Refs = ReadTaskTestRefs(repoRoot, viewFile, SplitTask150);

            acceptance.Should().HaveCount(2);
            acceptance[0].Should().Contain("split tasks 149 and 150");
            acceptance[0].Should().Contain("verified by deterministic acceptance evidence");
            acceptance[0].Should().Contain("not accepted if either split task lacks closure evidence");
            acceptance[1].Should().Contain("scope is limited to integration closure of split-task evidence");
            acceptance[1].Should().Contain("independent implementation belongs to split tasks 149 and 150");
            acceptance[1].Should().Contain("must not be introduced here");

            testRefs.Should().Contain(Task111Ref);
            testRefs.Should().HaveCount(1);
            task149Refs.Should().Contain(SplitTask149Ref);
            task150Refs.Should().Contain(SplitTask150Ref);

            File.Exists(Path.Combine(repoRoot, SplitTask149Ref.Replace('/', Path.DirectorySeparatorChar)))
                .Should().BeTrue("split task 149 evidence test must exist");
            File.Exists(Path.Combine(repoRoot, SplitTask150Ref.Replace('/', Path.DirectorySeparatorChar)))
                .Should().BeTrue("split task 150 evidence test must exist");
        }
    }

    // ACC:T111.2
    [Fact]
    [Trait("acceptance", "ACC:T111.2")]
    public void ShouldKeepTask111ScopeClosureOnly_WhenReadingAcceptanceContracts()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");

            acceptance.Should().HaveCount(2);
            acceptance[1].Should().Contain("scope is limited to integration closure of split-task evidence");
            acceptance[1].Should().Contain("independent implementation belongs to split tasks 149 and 150");
            acceptance[1].Should().Contain("must not be introduced here");
        }
    }

    // ACC:T111.1
    [Fact]
    [Trait("acceptance", "ACC:T111.1")]
    public void ShouldCloseIntegration_WhenBothSplitTaskEvidencesAreCompleted()
    {
        var task149Evidence = new SplitClosureEvidence(
            SplitTask149,
            SplitTask149Ref,
            "campaign-endgame-v3",
            IsCompleted: true);
        var task150Evidence = new SplitClosureEvidence(
            SplitTask150,
            SplitTask150Ref,
            "campaign-endgame-v3",
            IsCompleted: true);

        var outcome = Task111SplitIntegrationPack.Evaluate(task149Evidence, task150Evidence);

        outcome.IsClosed.Should().BeTrue();
        outcome.FailureCode.Should().BeNull();
        outcome.ClosureCode.Should().Be("campaign-endgame-v3");
    }

    // ACC:T111.1
    [Fact]
    [Trait("acceptance", "ACC:T111.1")]
    public void ShouldRemainOpen_WhenEitherSplitTaskEvidenceIsMissing()
    {
        var task149Evidence = new SplitClosureEvidence(
            SplitTask149,
            SplitTask149Ref,
            "campaign-endgame-v3",
            IsCompleted: true);

        var outcome = Task111SplitIntegrationPack.Evaluate(task149Evidence);

        outcome.IsClosed.Should().BeFalse();
        outcome.FailureCode.Should().Be("MISSING_SPLIT_TASK_EVIDENCE");
    }

    // ACC:T111.1
    [Fact]
    [Trait("acceptance", "ACC:T111.1")]
    public void ShouldRemainOpen_WhenSplitTaskEvidenceSignaturesDoNotMatch()
    {
        var task149Evidence = new SplitClosureEvidence(
            SplitTask149,
            SplitTask149Ref,
            "campaign-endgame-v3",
            IsCompleted: true);
        var task150Evidence = new SplitClosureEvidence(
            SplitTask150,
            SplitTask150Ref,
            "campaign-endgame-v3-with-drift",
            IsCompleted: true);

        var outcome = Task111SplitIntegrationPack.Evaluate(task149Evidence, task150Evidence);

        outcome.IsClosed.Should().BeFalse();
        outcome.FailureCode.Should().Be("MISMATCHED_CLOSURE_SIGNATURE");
    }

    private static string FindRepoRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            var marker = Path.Combine(current.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(marker))
            {
                return current.FullName;
            }

            current = current.Parent;
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
        task.TryGetProperty(propertyName, out var value).Should().BeTrue($"Task {TaskId} must define '{propertyName}'.");
        value.ValueKind.Should().Be(JsonValueKind.Array);
        return value.EnumerateArray().Select(static item => item.GetString() ?? string.Empty).ToArray();
    }

    private static JsonDocument LoadJson(string repoRoot, params string[] parts)
    {
        var path = Path.Combine(new[] { repoRoot }.Concat(parts).ToArray());
        using var stream = File.OpenRead(path);
        return JsonDocument.Parse(stream);
    }

    private sealed record SplitClosureEvidence(
        int SplitTaskId,
        string SourcePath,
        string ClosureSignature,
        bool IsCompleted);

    private sealed record ClosureOutcome(bool IsClosed, string ClosureCode, string? FailureCode);

    private static class Task111SplitIntegrationPack
    {
        public static ClosureOutcome Evaluate(params SplitClosureEvidence[] evidences)
        {
            evidences.Should().NotBeNull();
            evidences.Should().NotBeEmpty();

            if (evidences.Any(static item => !item.IsCompleted))
            {
                return new ClosureOutcome(false, string.Empty, "INCOMPLETE_SPLIT_TASK_EVIDENCE");
            }

            if (evidences.Any(static item => !IsTaskScopedTestPath(item.SourcePath)))
            {
                return new ClosureOutcome(false, string.Empty, "NON_TEST_EVIDENCE_PATH");
            }

            var evidenceTasks = evidences.Select(static item => item.SplitTaskId).ToHashSet();
            if (!evidenceTasks.Contains(SplitTask149) || !evidenceTasks.Contains(SplitTask150))
            {
                return new ClosureOutcome(false, string.Empty, "MISSING_SPLIT_TASK_EVIDENCE");
            }

            var signatures = evidences
                .Select(static item => item.ClosureSignature)
                .Where(static item => !string.IsNullOrWhiteSpace(item))
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            if (signatures.Length != 1)
            {
                return new ClosureOutcome(false, string.Empty, "MISMATCHED_CLOSURE_SIGNATURE");
            }

            return new ClosureOutcome(true, signatures[0], null);
        }

        private static bool IsTaskScopedTestPath(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                return false;
            }

            var normalized = path.Replace('\\', '/');
            return normalized.StartsWith("Game.Core.Tests/Tasks/Task", StringComparison.Ordinal);
        }
    }
}
