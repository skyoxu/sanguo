using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task75CampLifecycleEngineIntegrationPackTests
{
    private const int TaskId = 75;

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    private static readonly string[] ExpectedTaskRefs =
    {
        "Game.Core.Tests/Tasks/Task75CampLifecycleEngineIntegrationPackTests.cs",
    };

    // ACC:T75.1
    [Fact]
    [Trait("acceptance", "ACC:T75.1")]
    public void ShouldBindTask75AcceptanceToSplitEvidence_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptanceRefs = ReadStringArray(task, "acceptanceRefs");
            var acceptance = ReadStringArray(task, "acceptance");

            acceptanceRefs.Should().Equal("R2", "R5", "A-003", "A-004", "A-005");
            acceptance.Should().HaveCount(1);
            acceptance[0].Should().Contain("split tasks 87 and 88");
            acceptance[0].Should().Contain("R2/R5");
            acceptance[0].Should().Contain("A-003~A-005");
            acceptance[0].Should().Contain("non-leave-camp save evidence");
            acceptance[0].Should().Contain("Task75CampLifecycleEngineIntegrationPackTests.cs");

            var task87Refs = ReadTaskTestRefs(repoRoot, viewFile, taskmasterId: 87);
            var task88Refs = ReadTaskTestRefs(repoRoot, viewFile, taskmasterId: 88);
            var task87AcceptanceRefs = ReadTaskAcceptanceRefs(repoRoot, viewFile, taskmasterId: 87);
            var task88AcceptanceRefs = ReadTaskAcceptanceRefs(repoRoot, viewFile, taskmasterId: 88);

            task87Refs.Should().NotBeEmpty("Task 75 closure requires deterministic evidence from split task 87.");
            task88Refs.Should().NotBeEmpty("Task 75 closure requires deterministic evidence from split task 88.");
            task87AcceptanceRefs.Should().Contain("R2/R5");
            task88AcceptanceRefs.Single().Should().Contain("A-003");
            task88AcceptanceRefs.Single().Should().Contain("A-005");

            task87Refs.Concat(task88Refs)
                .Select(testRef => Path.Combine(repoRoot, testRef.Replace('/', Path.DirectorySeparatorChar)))
                .Should().OnlyContain(path => File.Exists(path), "split-task evidence files must exist in the repository.");

            var task87EvidencePath = Path.Combine(repoRoot, "Game.Core.Tests", "Tasks", "Task87SplitTests.cs");
            var task88EvidencePath = Path.Combine(repoRoot, "Game.Core.Tests", "Tasks", "Task88SplitTests.cs");
            File.ReadAllText(task87EvidencePath).Should().Contain("ACC:T87", "Task 87 evidence must remain acceptance-addressable.");
            File.ReadAllText(task88EvidencePath).Should().Contain("ACC:T88", "Task 88 evidence must remain acceptance-addressable.");
        }
    }

    [Fact]
    public void ShouldRouteTask75TestRefsToTaskScopedEvidence_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var testRefs = ReadStringArray(task, "test_refs");

            testRefs.Should().Equal(ExpectedTaskRefs);
            testRefs.Should().OnlyContain(testRef => ExpectedTaskRefs.Contains(testRef, StringComparer.Ordinal));
        }
    }

    [Fact]
    public void ShouldAggregateTask87AndTask88Evidence_WhenBuildingIntegrationPackEvidence()
    {
        var evidence = CampLifecycleEngineIntegrationPack.BuildEvidence(
            new Task87SplitEvidence(
                HasDeterministicEvidence: true,
                CoversR2R5Obligations: true,
                SplitScopes: new[] { CampLifecycleEngineIntegrationPack.SplitScopeT87 }),
            new Task88SplitEvidence(
                HasDeterministicEvidence: true,
                CoversA003A005Obligations: true,
                RejectsNonLeaveCampStandIn: true,
                SplitScopes: new[] { CampLifecycleEngineIntegrationPack.SplitScopeT88 }));

        evidence.Task87Delivered.Should().BeTrue();
        evidence.Task88Delivered.Should().BeTrue();
        evidence.SplitScopes.Should().Equal(
            CampLifecycleEngineIntegrationPack.SplitScopeT87,
            CampLifecycleEngineIntegrationPack.SplitScopeT88);
        evidence.IsClosureComplete.Should().BeTrue();
    }

    [Fact]
    public void ShouldMarkClosureIncomplete_WhenEitherSplitEvidenceIsMissing()
    {
        var missingTask87 = CampLifecycleEngineIntegrationPack.BuildEvidence(
            new Task87SplitEvidence(
                HasDeterministicEvidence: false,
                CoversR2R5Obligations: true,
                SplitScopes: new[] { CampLifecycleEngineIntegrationPack.SplitScopeT87 }),
            new Task88SplitEvidence(
                HasDeterministicEvidence: true,
                CoversA003A005Obligations: true,
                RejectsNonLeaveCampStandIn: true,
                SplitScopes: new[] { CampLifecycleEngineIntegrationPack.SplitScopeT88 }));
        var missingTask88 = CampLifecycleEngineIntegrationPack.BuildEvidence(
            new Task87SplitEvidence(
                HasDeterministicEvidence: true,
                CoversR2R5Obligations: true,
                SplitScopes: new[] { CampLifecycleEngineIntegrationPack.SplitScopeT87 }),
            new Task88SplitEvidence(
                HasDeterministicEvidence: false,
                CoversA003A005Obligations: true,
                RejectsNonLeaveCampStandIn: true,
                SplitScopes: new[] { CampLifecycleEngineIntegrationPack.SplitScopeT88 }));

        missingTask87.IsClosureComplete.Should().BeFalse();
        missingTask88.IsClosureComplete.Should().BeFalse();
    }

    [Fact]
    public void ShouldMarkClosureIncomplete_WhenRequiredSplitScopeIsMissing()
    {
        var evidence = CampLifecycleEngineIntegrationPack.BuildEvidence(
            new Task87SplitEvidence(
                HasDeterministicEvidence: true,
                CoversR2R5Obligations: true,
                SplitScopes: new[] { CampLifecycleEngineIntegrationPack.SplitScopeT87 }),
            new Task88SplitEvidence(
                HasDeterministicEvidence: true,
                CoversA003A005Obligations: true,
                RejectsNonLeaveCampStandIn: true,
                SplitScopes: Array.Empty<string>()));

        evidence.IsClosureComplete.Should().BeFalse();
    }

    [Fact]
    public void ShouldMarkClosureIncomplete_WhenTask88EvidenceUsesNonLeaveCampStandIn()
    {
        var evidence = CampLifecycleEngineIntegrationPack.BuildEvidence(
            new Task87SplitEvidence(
                HasDeterministicEvidence: true,
                CoversR2R5Obligations: true,
                SplitScopes: new[] { CampLifecycleEngineIntegrationPack.SplitScopeT87 }),
            new Task88SplitEvidence(
                HasDeterministicEvidence: true,
                CoversA003A005Obligations: true,
                RejectsNonLeaveCampStandIn: false,
                SplitScopes: new[] { CampLifecycleEngineIntegrationPack.SplitScopeT88 }));

        evidence.Task87Delivered.Should().BeTrue();
        evidence.Task88Delivered.Should().BeFalse();
        evidence.IsClosureComplete.Should().BeFalse();
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

    private static string[] ReadTaskAcceptanceRefs(string repoRoot, string fileName, int taskmasterId)
    {
        var task = GetTaskByTaskmasterId(repoRoot, fileName, taskmasterId);
        return ReadStringArray(task, "acceptanceRefs");
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
