using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task105SplitIntegrationTests
{
    private const int TaskId = 105;
    private const int SplitTaskA = 139;
    private const int SplitTaskB = 140;
    private const string ExpectedTaskRef = "Game.Core.Tests/Tasks/Task105SplitIntegrationTests.cs";
    private const string SplitTaskARef = "Game.Core.Tests/Tasks/Task139SplitTests.cs";
    private const string SplitTaskBRef = "Game.Core.Tests/Tasks/Task140SplitTests.cs";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T105.1
    [Fact]
    [Trait("acceptance", "ACC:T105.1")]
    public void ShouldBindTask105AcceptanceToSplitClosureEvidence_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptance.Should().ContainSingle();
            acceptance[0].Should().Contain("split-task evidence from tasks 139 and 140");
            acceptance[0].Should().Contain("requires no additional implementation");
            acceptance[0].Should().Contain("Task105SplitIntegrationTests.cs");

            testRefs.Should().Equal(ExpectedTaskRef);

            var splitTaskARefs = ReadTaskTestRefs(repoRoot, viewFile, SplitTaskA);
            var splitTaskBRefs = ReadTaskTestRefs(repoRoot, viewFile, SplitTaskB);

            splitTaskARefs.Should().Contain(SplitTaskARef);
            splitTaskBRefs.Should().Contain(SplitTaskBRef);

            splitTaskARefs.Concat(splitTaskBRefs)
                .Select(testRef => Path.Combine(repoRoot, testRef.Replace('/', Path.DirectorySeparatorChar)))
                .Should().OnlyContain(path => File.Exists(path), "split-task evidence files must exist in the repository.");

            ContainsTokenInFile(Path.Combine(repoRoot, SplitTaskARef.Replace('/', Path.DirectorySeparatorChar)), "ACC:T139.1")
                .Should().BeTrue();
            ContainsTokenInFile(Path.Combine(repoRoot, SplitTaskBRef.Replace('/', Path.DirectorySeparatorChar)), "ACC:T140.1")
                .Should().BeTrue();
        }
    }

    // ACC:T105.1
    [Fact]
    [Trait("acceptance", "ACC:T105.1")]
    public void ShouldReportClosureComplete_WhenBothSplitEvidenceExistAndNoAdditionalImplementationIsRequired()
    {
        var outcome = Task105ClosureEvaluator.Evaluate(
            hasTask139Evidence: true,
            hasTask140Evidence: true,
            additionalImplementationRequired: false,
            Task105ClosureEvaluator.SplitScopeTask139,
            Task105ClosureEvaluator.SplitScopeTask140);

        outcome.IsClosed.Should().BeTrue();
    }

    // ACC:T105.1
    [Fact]
    [Trait("acceptance", "ACC:T105.1")]
    public void ShouldReportClosureIncomplete_WhenEitherSplitEvidenceIsMissing()
    {
        var missingTask139 = Task105ClosureEvaluator.Evaluate(
            hasTask139Evidence: false,
            hasTask140Evidence: true,
            additionalImplementationRequired: false,
            Task105ClosureEvaluator.SplitScopeTask139,
            Task105ClosureEvaluator.SplitScopeTask140);
        var missingTask140 = Task105ClosureEvaluator.Evaluate(
            hasTask139Evidence: true,
            hasTask140Evidence: false,
            additionalImplementationRequired: false,
            Task105ClosureEvaluator.SplitScopeTask139,
            Task105ClosureEvaluator.SplitScopeTask140);

        missingTask139.IsClosed.Should().BeFalse();
        missingTask140.IsClosed.Should().BeFalse();
    }

    // ACC:T105.1
    [Fact]
    [Trait("acceptance", "ACC:T105.1")]
    public void ShouldReportClosureIncomplete_WhenAdditionalImplementationIsRequired()
    {
        var outcome = Task105ClosureEvaluator.Evaluate(
            hasTask139Evidence: true,
            hasTask140Evidence: true,
            additionalImplementationRequired: true,
            Task105ClosureEvaluator.SplitScopeTask139,
            Task105ClosureEvaluator.SplitScopeTask140);

        outcome.IsClosed.Should().BeFalse();
    }

    // ACC:T105.1
    [Fact]
    [Trait("acceptance", "ACC:T105.1")]
    public void ShouldReportClosureIncomplete_WhenAnyRequiredSplitScopeIsMissing()
    {
        var missingTask139Scope = Task105ClosureEvaluator.Evaluate(
            hasTask139Evidence: true,
            hasTask140Evidence: true,
            additionalImplementationRequired: false,
            Task105ClosureEvaluator.SplitScopeTask140);
        var missingTask140Scope = Task105ClosureEvaluator.Evaluate(
            hasTask139Evidence: true,
            hasTask140Evidence: true,
            additionalImplementationRequired: false,
            Task105ClosureEvaluator.SplitScopeTask139);

        missingTask139Scope.IsClosed.Should().BeFalse();
        missingTask140Scope.IsClosed.Should().BeFalse();
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

    private sealed record ClosureOutcome(bool IsClosed, string Reason);

    private static class Task105ClosureEvaluator
    {
        internal const string SplitScopeTask139 = "task-139-closure-evidence";
        internal const string SplitScopeTask140 = "task-140-closure-evidence";

        public static ClosureOutcome Evaluate(
            bool hasTask139Evidence,
            bool hasTask140Evidence,
            bool additionalImplementationRequired,
            params string[] splitScopes)
        {
            if (!hasTask139Evidence || !hasTask140Evidence)
            {
                return new ClosureOutcome(false, "Both split evidences are required for closure.");
            }

            if (additionalImplementationRequired)
            {
                return new ClosureOutcome(false, "Master task closure cannot require additional production implementation.");
            }

            var normalizedScopes = splitScopes
                .Where(scope => !string.IsNullOrWhiteSpace(scope))
                .Select(scope => scope.Trim())
                .ToHashSet(StringComparer.Ordinal);

            if (!normalizedScopes.Contains(SplitScopeTask139) || !normalizedScopes.Contains(SplitScopeTask140))
            {
                return new ClosureOutcome(false, "Both split scopes must be explicitly represented.");
            }

            return new ClosureOutcome(true, "Split-evidence integration closure is complete.");
        }
    }
}
