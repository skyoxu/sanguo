using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task100SplitIntegrationTests
{
    private const int TaskId = 100;

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    private static readonly string[] ExpectedTaskRefs =
    {
        "Game.Core.Tests/Tasks/Task100SplitIntegrationTests.cs",
    };

    // ACC:T100.1
    [Fact]
    [Trait("acceptance", "ACC:T100.1")]
    public void ShouldBindTask100AcceptanceToSplitEvidence_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptance.Should().HaveCount(1);
            acceptance[0].Should().Contain("split-task evidence from tasks 129 and 130");
            acceptance[0].Should().Contain("requires no additional implementation");
            acceptance[0].Should().Contain("Task100SplitIntegrationTests.cs");
            testRefs.Should().Equal(ExpectedTaskRefs);

            var task129Refs = ReadTaskTestRefs(repoRoot, viewFile, taskmasterId: 129);
            var task130Refs = ReadTaskTestRefs(repoRoot, viewFile, taskmasterId: 130);

            task129Refs.Should().NotBeEmpty("Task 100 closure requires deterministic split evidence from task 129.");
            task130Refs.Should().NotBeEmpty("Task 100 closure requires deterministic split evidence from task 130.");

            task129Refs.Concat(task130Refs)
                .Select(testRef => Path.Combine(repoRoot, testRef.Replace('/', Path.DirectorySeparatorChar)))
                .Should().OnlyContain(path => File.Exists(path), "split-task evidence files must exist in repository.");
        }
    }

    // ACC:T100.1
    [Fact]
    public void ShouldCloseIntegration_WhenBothSplitTaskEvidenceAndScopesArePresentAndNoAdditionalImplementationIsRequired()
    {
        var evidence = CampDurabilityFatalAdjudicatorIntegrationPack.EvaluateSplitEvidence(
            hasTask129Evidence: true,
            hasTask130Evidence: true,
            additionalImplementationRequired: false,
            CampDurabilityFatalAdjudicatorIntegrationPack.SplitScopeT129,
            CampDurabilityFatalAdjudicatorIntegrationPack.SplitScopeT130);

        evidence.Task129Delivered.Should().BeTrue();
        evidence.Task130Delivered.Should().BeTrue();
        evidence.AdditionalImplementationRequired.Should().BeFalse();
        evidence.IsClosureComplete.Should().BeTrue();
    }

    // ACC:T100.1
    [Fact]
    public void ShouldKeepIntegrationOpen_WhenAnySplitTaskEvidenceIsMissing()
    {
        var missing129 = CampDurabilityFatalAdjudicatorIntegrationPack.EvaluateSplitEvidence(
            hasTask129Evidence: false,
            hasTask130Evidence: true,
            additionalImplementationRequired: false,
            CampDurabilityFatalAdjudicatorIntegrationPack.SplitScopeT129,
            CampDurabilityFatalAdjudicatorIntegrationPack.SplitScopeT130);
        var missing130 = CampDurabilityFatalAdjudicatorIntegrationPack.EvaluateSplitEvidence(
            hasTask129Evidence: true,
            hasTask130Evidence: false,
            additionalImplementationRequired: false,
            CampDurabilityFatalAdjudicatorIntegrationPack.SplitScopeT129,
            CampDurabilityFatalAdjudicatorIntegrationPack.SplitScopeT130);

        missing129.IsClosureComplete.Should().BeFalse();
        missing130.IsClosureComplete.Should().BeFalse();
    }

    // ACC:T100.1
    [Fact]
    public void ShouldKeepIntegrationOpen_WhenAdditionalImplementationIsStillRequired()
    {
        var evidence = CampDurabilityFatalAdjudicatorIntegrationPack.EvaluateSplitEvidence(
            hasTask129Evidence: true,
            hasTask130Evidence: true,
            additionalImplementationRequired: true,
            CampDurabilityFatalAdjudicatorIntegrationPack.SplitScopeT129,
            CampDurabilityFatalAdjudicatorIntegrationPack.SplitScopeT130);

        evidence.IsClosureComplete.Should().BeFalse();
    }

    // ACC:T100.1
    [Fact]
    public void ShouldKeepIntegrationOpen_WhenAnyRequiredSplitScopeIsMissing()
    {
        var missingT129Scope = CampDurabilityFatalAdjudicatorIntegrationPack.EvaluateSplitEvidence(
            hasTask129Evidence: true,
            hasTask130Evidence: true,
            additionalImplementationRequired: false,
            CampDurabilityFatalAdjudicatorIntegrationPack.SplitScopeT130);
        var missingT130Scope = CampDurabilityFatalAdjudicatorIntegrationPack.EvaluateSplitEvidence(
            hasTask129Evidence: true,
            hasTask130Evidence: true,
            additionalImplementationRequired: false,
            CampDurabilityFatalAdjudicatorIntegrationPack.SplitScopeT129);

        missingT129Scope.IsClosureComplete.Should().BeFalse();
        missingT130Scope.IsClosureComplete.Should().BeFalse();
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
        var text = File.ReadAllText(path);
        return JsonDocument.Parse(text);
    }
}
