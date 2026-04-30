using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task161SplitClosureTests
{
    private const int TaskId = 161;
    private const string ThisTestRef = "Game.Core.Tests/Tasks/Task161SplitClosureTests.cs";
    private const string Task166TestRef = "Game.Core.Tests/Tasks/Task166SplitTests.cs";
    private const string Task167TestRef = "Game.Core.Tests/Tasks/Task167SplitTests.cs";
    private const string Task168TestRef = "Game.Core.Tests/Tasks/Task168SplitTests.cs";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    [Fact]
    public void ShouldBindTask161ClosureEvidence_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task161 = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task161, "acceptance");
            var testRefs = ReadStringArray(task161, "test_refs");
            var dependsOn = ReadStringArray(task161, "depends_on");

            acceptance.Should().ContainSingle();
            acceptance[0].Should().Contain("tasks 166, 167, and 168");
            acceptance[0].Should().Contain("migration compatibility report automation gate");
            acceptance[0].Should().Contain(ThisTestRef);

            testRefs.Should().Contain(ThisTestRef);

            dependsOn.Should().HaveCount(3);
            dependsOn.Should().Contain(item => item.EndsWith("0166", StringComparison.Ordinal));
            dependsOn.Should().Contain(item => item.EndsWith("0167", StringComparison.Ordinal));
            dependsOn.Should().Contain(item => item.EndsWith("0168", StringComparison.Ordinal));
        }
    }

    // ACC:T161.1
    [Theory]
    [Trait("acceptance", "ACC:T161.1")]
    [InlineData(false, true, true)]
    [InlineData(true, false, true)]
    [InlineData(true, true, false)]
    public void ShouldRefuseClosure_WhenAnyRequiredSplitEvidenceIsMissing(
        bool hasTask166Evidence,
        bool hasTask167Evidence,
        bool hasTask168Evidence)
    {
        var result = MigrationCompatibilityClosureGate.Evaluate(
            new MigrationCompatibilityClosureEvidence(
                hasTask166Evidence,
                hasTask167Evidence,
                hasTask168Evidence,
                hasTask166Evidence,
                hasTask167Evidence,
                hasTask168Evidence));

        result.IsClosureComplete.Should().BeFalse(
            "Task 161 must stay open until evidence from tasks 166, 167, and 168 is all present.");
        result.AdvanceAllowed.Should().BeFalse(
            "the migration compatibility automation gate must refuse to advance on incomplete evidence.");
    }

    [Fact]
    public void ShouldRefuseClosure_WhenCompatibilityGateDoesNotPass()
    {
        var result = MigrationCompatibilityClosureGate.Evaluate(
            new MigrationCompatibilityClosureEvidence(
                HasReportGenerationEvidence: true,
                HasCompletenessValidationEvidence: true,
                HasCiGateEvidence: true,
                ReportGenerationSatisfied: true,
                CompletenessValidationSatisfied: true,
                CiGateSatisfied: false));

        result.IsClosureComplete.Should().BeFalse(
            "Task 161 requires the collected evidence to satisfy the migration compatibility report automation gate.");
        result.AdvanceAllowed.Should().BeFalse(
            "closure must not advance when the CI hard-gate integration still fails.");
    }

    [Fact]
    public void ShouldCloseTask161_WhenCurrentRepositoryProvidesAllRequiredSplitEvidenceAndGateCoverage()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var evidence = ReadCurrentClosureEvidence(repoRoot, viewFile);
            var result = MigrationCompatibilityClosureGate.Evaluate(evidence);

            result.IsClosureComplete.Should().BeTrue(
                "Task 161 closure should turn green only after tasks 166, 167, and 168 provide completed migration compatibility gate evidence.");
            result.AdvanceAllowed.Should().BeTrue(
                "a fully satisfied migration compatibility closure should allow the pipeline to advance.");
        }
    }

    private static MigrationCompatibilityClosureEvidence ReadCurrentClosureEvidence(string repoRoot, string viewFile)
    {
        var task166 = GetTaskByTaskmasterId(repoRoot, viewFile, 166);
        var task167 = GetTaskByTaskmasterId(repoRoot, viewFile, 167);
        var task168 = GetTaskByTaskmasterId(repoRoot, viewFile, 168);

        return new MigrationCompatibilityClosureEvidence(
            HasReportGenerationEvidence: HasRecordedEvidence(repoRoot, task166, Task166TestRef),
            HasCompletenessValidationEvidence: HasRecordedEvidence(repoRoot, task167, Task167TestRef),
            HasCiGateEvidence: HasRecordedEvidence(repoRoot, task168, Task168TestRef),
            ReportGenerationSatisfied: ReadRequiredString(task166, "status").Equals("done", StringComparison.OrdinalIgnoreCase),
            CompletenessValidationSatisfied: ReadRequiredString(task167, "status").Equals("done", StringComparison.OrdinalIgnoreCase),
            CiGateSatisfied: ReadRequiredString(task168, "status").Equals("done", StringComparison.OrdinalIgnoreCase));
    }

    private static bool HasRecordedEvidence(string repoRoot, JsonElement task, string expectedTestRef)
    {
        var testRefs = ReadStringArray(task, "test_refs");
        var expectedPath = Path.Combine(repoRoot, expectedTestRef.Replace('/', Path.DirectorySeparatorChar));

        return testRefs.Contains(expectedTestRef, StringComparer.Ordinal) && File.Exists(expectedPath);
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
        return JsonDocument.Parse(File.ReadAllText(path));
    }

    private sealed record MigrationCompatibilityClosureEvidence(
        bool HasReportGenerationEvidence,
        bool HasCompletenessValidationEvidence,
        bool HasCiGateEvidence,
        bool ReportGenerationSatisfied,
        bool CompletenessValidationSatisfied,
        bool CiGateSatisfied);

    private sealed record ClosureEvaluation(bool IsClosureComplete, bool AdvanceAllowed);

    private static class MigrationCompatibilityClosureGate
    {
        public static ClosureEvaluation Evaluate(MigrationCompatibilityClosureEvidence evidence)
        {
            var hasAllRequiredEvidence =
                evidence.HasReportGenerationEvidence &&
                evidence.HasCompletenessValidationEvidence &&
                evidence.HasCiGateEvidence;

            var allGateSignalsSatisfied =
                evidence.ReportGenerationSatisfied &&
                evidence.CompletenessValidationSatisfied &&
                evidence.CiGateSatisfied;

            var isClosureComplete = hasAllRequiredEvidence && allGateSignalsSatisfied;
            return new ClosureEvaluation(isClosureComplete, isClosureComplete);
        }
    }
}
