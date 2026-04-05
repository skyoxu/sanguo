using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task74IntegrationClosureTests
{
    private const int TaskId = 74;

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    private static readonly string[] ExpectedTaskRefs =
    {
        "Game.Core.Tests/Tasks/Task74IntegrationClosureTests.cs",
    };

    // ACC:T74.1
    [Fact]
    [Trait("acceptance", "ACC:T74.1")]
    public void ShouldBindTask74AcceptanceToSplitEvidence_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptanceRefs = ReadStringArray(task, "acceptanceRefs");
            var acceptance = ReadStringArray(task, "acceptance");

            acceptanceRefs.Should().Equal("R1", "R3");
            acceptance.Should().HaveCount(2);
            acceptance[0].Should().Contain("split tasks 85 and 86");
            acceptance[0].Should().Contain("Task74IntegrationClosureTests.cs");
            acceptance[1].Should().Contain("closure-only after split delivery");
            acceptance[1].Should().Contain("Task74IntegrationClosureTests.cs");

            var task85Refs = ReadTaskTestRefs(repoRoot, viewFile, taskmasterId: 85);
            var task86Refs = ReadTaskTestRefs(repoRoot, viewFile, taskmasterId: 86);
            var task85AcceptanceRefs = ReadTaskAcceptanceRefs(repoRoot, viewFile, taskmasterId: 85);
            var task86AcceptanceRefs = ReadTaskAcceptanceRefs(repoRoot, viewFile, taskmasterId: 86);

            task85Refs.Should().NotBeEmpty("Task 74 acceptance requires verifiable evidence from split task 85.");
            task86Refs.Should().NotBeEmpty("Task 74 acceptance requires verifiable evidence from split task 86.");
            task85AcceptanceRefs.Should().Contain("R1");
            task86AcceptanceRefs.Should().Contain("R3");

            task85Refs.Concat(task86Refs)
                .Select(testRef => Path.Combine(repoRoot, testRef.Replace('/', Path.DirectorySeparatorChar)))
                .Should().OnlyContain(path => File.Exists(path), "split-task evidence files must exist in the repository.");

            var task85EvidencePath = Path.Combine(repoRoot, "Game.Core.Tests", "Tasks", "Task85SplitTests.cs");
            var task86EvidencePath = Path.Combine(repoRoot, "Game.Core.Tests", "Tasks", "Task86SplitTests.cs");
            File.ReadAllText(task85EvidencePath).Should().Contain("ACC:T85", "Task 85 evidence must stay acceptance-addressable.");
            File.ReadAllText(task86EvidencePath).Should().Contain("ACC:T86", "Task 86 evidence must stay acceptance-addressable.");
        }
    }

    [Fact]
    public void ShouldRouteTask74TestRefsToSplitEvidence_WhenReadingTaskViews()
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

    // ACC:T74.2
    [Fact]
    [Trait("acceptance", "ACC:T74.2")]
    public void ShouldAggregateR1AndR3Evidence_WhenBuildingIntegrationPackEvidence()
    {
        var evidence = CampaignRuleEngineIntegrationPack.BuildEvidence();

        evidence.R1IsolationDelivered.Should().BeTrue();
        evidence.R3AdjudicatorDelivered.Should().BeTrue();
        evidence.SplitScopes.Should().Equal(
            CampaignRuleEngineIntegrationPack.SplitScopeR1,
            CampaignRuleEngineIntegrationPack.SplitScopeR3);
        evidence.IsClosureComplete.Should().BeTrue();
    }

    [Fact]
    public void ShouldMarkClosureIncomplete_WhenEitherSplitEvidenceIsMissing()
    {
        var missingR1 = CampaignRuleEngineIntegrationPack.EvaluateSplitEvidence(
            hasR1IsolationEvidence: false,
            hasR3AdjudicatorEvidence: true,
            CampaignRuleEngineIntegrationPack.SplitScopeR1,
            CampaignRuleEngineIntegrationPack.SplitScopeR3);
        var missingR3 = CampaignRuleEngineIntegrationPack.EvaluateSplitEvidence(
            hasR1IsolationEvidence: true,
            hasR3AdjudicatorEvidence: false,
            CampaignRuleEngineIntegrationPack.SplitScopeR1,
            CampaignRuleEngineIntegrationPack.SplitScopeR3);

        missingR1.IsClosureComplete.Should().BeFalse();
        missingR3.IsClosureComplete.Should().BeFalse();
    }

    [Fact]
    public void ShouldMarkClosureIncomplete_WhenRequiredSplitScopeIsMissing()
    {
        var evidence = CampaignRuleEngineIntegrationPack.EvaluateSplitEvidence(
            hasR1IsolationEvidence: true,
            hasR3AdjudicatorEvidence: true,
            CampaignRuleEngineIntegrationPack.SplitScopeR1);

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
