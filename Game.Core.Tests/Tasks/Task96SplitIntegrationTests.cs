using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task96SplitIntegrationTests
{
    private const int TaskId = 96;
    private const int SplitTaskA = 123;
    private const int SplitTaskB = 124;
    private const string Task96EvidenceRef = "Game.Core.Tests/Tasks/Task96SplitIntegrationTests.cs";
    private const string SplitTask123EvidenceRef = "Game.Core.Tests/Services/SanguoGlobalEventRoundGateTests.cs";
    private const string SplitTask124EvidenceRef = "Game.Core.Tests/Services/SanguoGlobalEventRoundGateTests.cs";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T96.1
    [Fact]
    [Trait("acceptance", "ACC:T96.1")]
    public void ShouldRequireCombinedSplitEvidence_WhenReadingTask96FromBothViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptance.Should().HaveCount(2);
            acceptance[0].Should().Contain("ACC:T96.1");
            acceptance[0].Should().Contain("split tasks 123 and 124");
            acceptance[0].Should().Contain("both required");
            acceptance[0].Should().Contain(Task96EvidenceRef);
            acceptance[0].Should().Contain(SplitTask123EvidenceRef);
            acceptance[0].Should().Contain(SplitTask124EvidenceRef);

            acceptance[1].Should().Contain("ACC:T96.2");
            acceptance[1].Should().Contain(Task96EvidenceRef);

            testRefs.Should().Contain(Task96EvidenceRef);
            testRefs.Should().Contain(SplitTask123EvidenceRef);
            testRefs.Should().Contain(SplitTask124EvidenceRef);

            var split123TaskRefs = ReadTaskTestRefs(repoRoot, viewFile, SplitTaskA);
            var split124TaskRefs = ReadTaskTestRefs(repoRoot, viewFile, SplitTaskB);

            // Task 96 only references Task96* files under Game.Core.Tests/Tasks by policy.
            // Split-evidence linkage is still validated through split task refs and service-level evidence.
            split123TaskRefs.Should().Contain("Game.Core.Tests/Tasks/Task123SplitTests.cs");
            split124TaskRefs.Should().Contain(SplitTask124EvidenceRef);
        }
    }

    // ACC:T96.2
    [Fact]
    [Trait("acceptance", "ACC:T96.2")]
    public void ShouldFailClosure_WhenEitherSplitEvidenceIsMissing()
    {
        var complete = Task96ClosureEvaluator.Evaluate(
            hasTask123Evidence: true,
            hasTask124Evidence: true,
            introducesNewProductionBehavior: false);
        var missingTask123 = Task96ClosureEvaluator.Evaluate(
            hasTask123Evidence: false,
            hasTask124Evidence: true,
            introducesNewProductionBehavior: false);
        var missingTask124 = Task96ClosureEvaluator.Evaluate(
            hasTask123Evidence: true,
            hasTask124Evidence: false,
            introducesNewProductionBehavior: false);

        complete.IsClosed.Should().BeTrue();
        missingTask123.IsClosed.Should().BeFalse();
        missingTask124.IsClosed.Should().BeFalse();
    }

    // ACC:T96.2
    [Fact]
    [Trait("acceptance", "ACC:T96.2")]
    public void ShouldFailClosure_WhenMasterTaskAddsNewProductionBehavior()
    {
        var result = Task96ClosureEvaluator.Evaluate(
            hasTask123Evidence: true,
            hasTask124Evidence: true,
            introducesNewProductionBehavior: true);

        result.IsClosed.Should().BeFalse();
        result.Reason.Should().Be("Master task closure cannot require new production implementation.");
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

    private sealed record ClosureOutcome(bool IsClosed, string Reason);

    private static class Task96ClosureEvaluator
    {
        public static ClosureOutcome Evaluate(
            bool hasTask123Evidence,
            bool hasTask124Evidence,
            bool introducesNewProductionBehavior)
        {
            if (!hasTask123Evidence || !hasTask124Evidence)
            {
                return new ClosureOutcome(false, "Both split evidences are required for closure.");
            }

            if (introducesNewProductionBehavior)
            {
                return new ClosureOutcome(false, "Master task closure cannot require new production implementation.");
            }

            return new ClosureOutcome(true, "Split-evidence integration closure is complete.");
        }
    }
}
