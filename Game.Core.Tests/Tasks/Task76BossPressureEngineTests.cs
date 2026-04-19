using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task76BossPressureEngineTests
{
    private const int TaskId = 76;

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    private const string ExpectedTaskRef = "Game.Core.Tests/Tasks/Task76BossPressureEngineTests.cs";
    private const string Task89EvidenceRef = "Game.Core.Tests/Tasks/Task89SplitTests.cs";
    private const string Task89TimelineEvidenceRef = "Game.Core.Tests/Tasks/Task89BossPressureTimelineTests.cs";
    private const string Task90EvidenceRef = "Game.Core.Tests/Tasks/Task90SplitTests.cs";
    private const string Task90PreemptionEvidenceRef = "Game.Core.Tests/Services/ForcedChallengePreemptionTests.cs";

    // ACC:T76.1
    [Fact]
    [Trait("acceptance", "ACC:T76.1")]
    public void ShouldKeepTaskScopedClosureRef_WhenReadingTask76FromBothViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptanceRefs = ReadStringArray(task, "acceptanceRefs");
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptanceRefs.Should().Equal("R6", "A-006", "A-007");
            acceptance.Should().ContainSingle();
            acceptance[0].Should().Contain("split task 89");
            acceptance[0].Should().Contain("split task 90");
            acceptance[0].Should().Contain(ExpectedTaskRef);

            testRefs.Should().Equal(ExpectedTaskRef);
        }
    }

    // ACC:T76.1
    [Fact]
    [Trait("acceptance", "ACC:T76.1")]
    public void ShouldRequireBothSplitTaskEvidence_WhenEvaluatingTask76Closure()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task76 = GetTaskByTaskmasterId(repoRoot, viewFile, taskmasterId: 76);
            var task76Status = ReadRequiredString(task76, "status");
            var task89Refs = ReadTaskTestRefs(repoRoot, viewFile, taskmasterId: 89);
            var task90Refs = ReadTaskTestRefs(repoRoot, viewFile, taskmasterId: 90);
            var task89 = GetTaskByTaskmasterId(repoRoot, viewFile, taskmasterId: 89);
            var task90 = GetTaskByTaskmasterId(repoRoot, viewFile, taskmasterId: 90);

            task89Refs.Should().Contain(Task89EvidenceRef);
            task89Refs.Should().Contain(Task89TimelineEvidenceRef);
            task90Refs.Should().Contain(Task90EvidenceRef);
            task90Refs.Should().Contain(Task90PreemptionEvidenceRef);

            task89Refs.Concat(task90Refs)
                .Select(testRef => Path.Combine(repoRoot, testRef.Replace('/', Path.DirectorySeparatorChar)))
                .Should().OnlyContain(path => File.Exists(path), "Task 76 closure must be backed by existing split-task evidence files.");

            var task89Outcome = ReadSplitTaskCompletionOutcome(
                task89,
                expectedTaskId: 89,
                expectedAcceptanceRefsToken: "R6",
                requiredAcceptanceSnippets:
                [
                    "task-specific deterministic verification",
                    "scope drifts away from the T76-origin split boundary",
                ],
                requiredEvidenceRefs:
                [
                    Task89EvidenceRef,
                    Task89TimelineEvidenceRef,
                ]);

            var task90Outcome = ReadSplitTaskCompletionOutcome(
                task90,
                expectedTaskId: 90,
                expectedAcceptanceRefsToken: "A-006~A-007",
                requiredAcceptanceSnippets:
                [
                    "deterministic task-specific evidence verifies both preemption transition and non-advance guarantees",
                ],
                requiredEvidenceRefs:
                [
                    Task90EvidenceRef,
                    Task90PreemptionEvidenceRef,
                ]);

            var closureOutcome = EvaluateClosure(task89Outcome, task90Outcome);

            // Task 76 remains deferred until both split tasks expose complete outcomes and are marked done.
            closureOutcome.IsClosed.Should().BeFalse();
            closureOutcome.Task76Status.Should().Be("deferred");
            task76Status.Should().Be(closureOutcome.Task76Status);
        }
    }

    [Fact]
    public void GivenMissingSplitOutcome_WhenEvaluatingClosure_ThenTask76RemainsDeferred()
    {
        var completed89 = new SplitTaskCompletionOutcome(
            TaskId: 89,
            Status: "done",
            HasExpectedScope: true,
            HasDeterministicEvidence: true,
            HasDeterministicAcceptanceWording: true);
        var completed90 = new SplitTaskCompletionOutcome(
            TaskId: 90,
            Status: "done",
            HasExpectedScope: true,
            HasDeterministicEvidence: true,
            HasDeterministicAcceptanceWording: true);
        var missing90 = completed90 with { Status = "deferred" };
        var missing89 = completed89 with { Status = "deferred" };

        EvaluateClosure(completed89, completed90).Should().Be(
            new Task76ClosureOutcome(IsClosed: true, Task76Status: "done"));
        EvaluateClosure(completed89, missing90).Should().Be(
            new Task76ClosureOutcome(IsClosed: false, Task76Status: "deferred"));
        EvaluateClosure(missing89, completed90).Should().Be(
            new Task76ClosureOutcome(IsClosed: false, Task76Status: "deferred"));
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

    private static SplitTaskCompletionOutcome ReadSplitTaskCompletionOutcome(
        JsonElement task,
        int expectedTaskId,
        string expectedAcceptanceRefsToken,
        string[] requiredAcceptanceSnippets,
        string[] requiredEvidenceRefs)
    {
        var status = ReadRequiredString(task, "status");
        var acceptanceRefs = ReadStringArray(task, "acceptanceRefs");
        var acceptance = ReadStringArray(task, "acceptance");
        var testRefs = ReadStringArray(task, "test_refs");

        var hasExpectedScope = acceptanceRefs.Contains(expectedAcceptanceRefsToken, StringComparer.Ordinal);
        var hasDeterministicEvidence = requiredEvidenceRefs.All(
            requiredRef => testRefs.Contains(requiredRef, StringComparer.Ordinal));
        var joinedAcceptance = string.Join("\n", acceptance);
        var hasDeterministicAcceptanceWording = requiredAcceptanceSnippets.All(
            snippet => joinedAcceptance.Contains(snippet, StringComparison.Ordinal));

        return new SplitTaskCompletionOutcome(
            TaskId: expectedTaskId,
            Status: status,
            HasExpectedScope: hasExpectedScope,
            HasDeterministicEvidence: hasDeterministicEvidence,
            HasDeterministicAcceptanceWording: hasDeterministicAcceptanceWording);
    }

    private static Task76ClosureOutcome EvaluateClosure(
        SplitTaskCompletionOutcome task89Outcome,
        SplitTaskCompletionOutcome task90Outcome)
    {
        var isTask89Complete = task89Outcome.IsComplete;
        var isTask90Complete = task90Outcome.IsComplete;

        return isTask89Complete && isTask90Complete
            ? new Task76ClosureOutcome(IsClosed: true, Task76Status: "done")
            : new Task76ClosureOutcome(IsClosed: false, Task76Status: "deferred");
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

    private static string ReadRequiredString(JsonElement task, string propertyName)
    {
        task.TryGetProperty(propertyName, out var property)
            .Should().BeTrue($"Task {TaskId} must contain '{propertyName}'.");

        property.ValueKind.Should().Be(JsonValueKind.String);
        return property.GetString() ?? string.Empty;
    }

    private static JsonDocument LoadJson(string repoRoot, params string[] relativeParts)
    {
        var path = Path.Combine(new[] { repoRoot }.Concat(relativeParts).ToArray());
        var text = File.ReadAllText(path);
        return JsonDocument.Parse(text);
    }

    private sealed record SplitTaskCompletionOutcome(
        int TaskId,
        string Status,
        bool HasExpectedScope,
        bool HasDeterministicEvidence,
        bool HasDeterministicAcceptanceWording)
    {
        public bool IsComplete =>
            string.Equals(Status, "done", StringComparison.Ordinal) &&
            HasExpectedScope &&
            HasDeterministicEvidence &&
            HasDeterministicAcceptanceWording;
    }

    private sealed record Task76ClosureOutcome(bool IsClosed, string Task76Status);
}
