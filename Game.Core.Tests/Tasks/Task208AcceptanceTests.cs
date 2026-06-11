using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task208AcceptanceTests
{
    private const int TaskId = 208;
    private const int LinkedTaskId = 78;
    private const string SelfRef = "Game.Core.Tests/Tasks/Task208AcceptanceTests.cs";
    private const string RewardDraftRef = "Game.Core.Tests/Tasks/Task78RewardDraftEngineTests.cs";
    private const string SplitRef = "Game.Core.Tests/Tasks/Task78SplitIntegrationTests.cs";
    private const string Task119Ref = "Game.Core.Tests/Tasks/Task119RewardDraftCandidateDeterminismTests.cs";
    private const string Task120Ref = "Game.Core.Tests/Tasks/Task120SplitTests.cs";
    private const string GameplayView = ".taskmaster/tasks/tasks_gameplay.json";

    // ACC:T208.1
    [Fact]
    [Trait("acceptance", "ACC:T208.1")]
    public void ShouldBindRequirementOneToTask208Evidence_WhenReadingGameplayView()
    {
        AssertAcceptanceBoundToSelfRef(0);
    }

    // ACC:T208.2
    [Fact]
    [Trait("acceptance", "ACC:T208.2")]
    public void ShouldBindRequirementTwoToTask208Evidence_WhenReadingGameplayView()
    {
        AssertAcceptanceBoundToSelfRef(1);
    }

    // ACC:T208.3
    [Fact]
    [Trait("acceptance", "ACC:T208.3")]
    public void ShouldBindRequirementThreeToTask208Evidence_WhenReadingGameplayView()
    {
        AssertAcceptanceBoundToSelfRef(2);
    }

    // ACC:T208.4
    [Fact]
    [Trait("acceptance", "ACC:T208.4")]
    public void ShouldBindRequirementFourToTask208Evidence_WhenReadingGameplayView()
    {
        AssertAcceptanceBoundToSelfRef(3);
    }

    // ACC:T208.5
    [Fact]
    [Trait("acceptance", "ACC:T208.5")]
    public void ShouldValidateRepeatedDraftOutcomes_WhenInputsAndSeedRepeat()
    {
        AssertAcceptanceBoundToSelfRef(4);
        AssertTask119And120EvidencePath();
        AssertDeterministicDraftEvidence();
    }

    // ACC:T208.6
    [Fact]
    [Trait("acceptance", "ACC:T208.6")]
    public void ShouldBindMissingDeterminismClosureRule_WhenReadingGameplayView()
    {
        AssertAcceptanceBoundToSelfRef(5);
        ReadAcceptance()[5].ToLowerInvariant().Should().Contain("task 78 remains open");
        AssertTask119And120EvidencePath();
        ValidateTask78ClosureEvidence(new[] { 119, 120 }).Should().BeTrue();
        ValidateTask78ClosureEvidence(new[] { 119 }).Should().BeFalse();
        ValidateTask78ClosureEvidence(new[] { 120 }).Should().BeFalse();
        ValidateRepeatedDraftOutcomes(null, new[] { "reward-a", "reward-b", "reward-c" })
            .Should()
            .BeFalse();
    }

    // ACC:T208.7
    [Fact]
    [Trait("acceptance", "ACC:T208.7")]
    public void ShouldValidateDeterministicFailureFixture_WhenDraftOutcomesDiffer()
    {
        AssertAcceptanceBoundToSelfRef(6);
        AssertTask119And120EvidencePath();
        ValidateRepeatedDraftOutcomes(
                new[] { "reward-a", "reward-b", "reward-c" },
                new[] { "reward-a", "reward-b", "reward-d" })
            .Should()
            .BeFalse();
    }

    // ACC:T208.8
    [Fact]
    [Trait("acceptance", "ACC:T208.8")]
    public void ShouldBindChapter38BaselineEvidence_WhenReadingGameplayView()
    {
        AssertAcceptanceBoundToSelfRef(7);
        ReadAcceptance()[7].Should().Contain("Chapter 3.8 triplet baseline validators");
    }

    // ACC:T208.9
    [Fact]
    [Trait("acceptance", "ACC:T208.9")]
    public void ShouldBindObligationOnePositiveEvidence_WhenReadingGameplayView()
    {
        AssertAcceptanceBoundToSelfRef(8);
    }

    // ACC:T208.10
    [Fact]
    [Trait("acceptance", "ACC:T208.10")]
    public void ShouldBindObligationOneNegativeEvidence_WhenReadingGameplayView()
    {
        AssertAcceptanceBoundToSelfRef(9);
    }

    // ACC:T208.11
    [Fact]
    [Trait("acceptance", "ACC:T208.11")]
    public void ShouldBindObligationOneTaskValidation_WhenReadingGameplayView()
    {
        AssertAcceptanceBoundToSelfRef(10);
    }

    // ACC:T208.12
    [Fact]
    [Trait("acceptance", "ACC:T208.12")]
    public void ShouldBindMinimalImplementationScope_WhenReadingGameplayView()
    {
        AssertAcceptanceBoundToSelfRef(11);
    }

    // ACC:T208.13
    [Fact]
    [Trait("acceptance", "ACC:T208.13")]
    public void ShouldBindSmallestValidationScope_WhenReadingGameplayView()
    {
        AssertAcceptanceBoundToSelfRef(12);
    }

    private static void AssertAcceptanceBoundToSelfRef(int index)
    {
        var acceptance = ReadAcceptance();
        var testRefs = ReadStringArray(GetTaskByTaskmasterId(FindRepoRoot(), TaskId), "test_refs");

        acceptance.Should().HaveCount(13);
        acceptance[index].Should().Contain(" Refs:");
        acceptance[index].Should().Contain(SelfRef);
        testRefs.Should().Contain(SelfRef);
        testRefs.Should().Contain(RewardDraftRef);
        testRefs.Should().Contain(SplitRef);
    }

    private static void AssertTask119And120EvidencePath()
    {
        var repoRoot = FindRepoRoot();
        var task208Refs = ReadStringArray(GetTaskByTaskmasterId(repoRoot, TaskId), "test_refs");
        var task119 = GetTaskByTaskmasterId(repoRoot, 119);
        var task120 = GetTaskByTaskmasterId(repoRoot, 120);
        var task119Refs = ReadStringArray(task119, "test_refs");
        var task120Refs = ReadStringArray(task120, "test_refs");

        task208Refs.Should().Contain(Task119Ref);
        task208Refs.Should().Contain(Task120Ref);
        task119Refs.Should().Contain(Task119Ref);
        task120Refs.Should().Contain(Task120Ref);
        File.Exists(Path.Combine(repoRoot, Task119Ref)).Should().BeTrue();
        File.Exists(Path.Combine(repoRoot, Task120Ref)).Should().BeTrue();
        ReadStringArray(task119, "acceptance").Should().Contain(item => item.Contains(Task119Ref, StringComparison.Ordinal));
        ReadStringArray(task120, "acceptance").Should().Contain(item => item.Contains(Task120Ref, StringComparison.Ordinal));
    }

    private static void AssertDeterministicDraftEvidence()
    {
        var first = RewardDraftCandidateDeterminismEngine.GenerateDraftCandidates(
            seed: LinkedTaskId,
            source: "task208_part1_state_config_validation",
            choiceCount: 3,
            actionCardsCatalog: null,
            relicsCatalog: null);
        var second = RewardDraftCandidateDeterminismEngine.GenerateDraftCandidates(
            seed: LinkedTaskId,
            source: "task208_part1_state_config_validation",
            choiceCount: 3,
            actionCardsCatalog: null,
            relicsCatalog: null);

        first.Should().HaveCount(3);
        second.Should().Equal(first);
        first.Should().OnlyHaveUniqueItems();
        ValidateRepeatedDraftOutcomes(first, second).Should().BeTrue();
    }

    private static bool ValidateRepeatedDraftOutcomes(IReadOnlyList<string>? first, IReadOnlyList<string>? second)
    {
        return first is not null &&
            second is not null &&
            first.Count == 3 &&
            second.Count == 3 &&
            first.SequenceEqual(second) &&
            first.Distinct().Count() == first.Count;
    }

    private static bool ValidateTask78ClosureEvidence(IEnumerable<int> completedSplitTaskIds)
    {
        var set = completedSplitTaskIds.ToHashSet();
        return set.Contains(119) && set.Contains(120);
    }

    private static string[] ReadAcceptance()
    {
        return ReadStringArray(GetTaskByTaskmasterId(FindRepoRoot(), TaskId), "acceptance");
    }

    private static string FindRepoRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            var marker = Path.Combine(current.FullName, GameplayView);
            if (File.Exists(marker))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks_gameplay.json).");
    }

    private static JsonElement GetTaskByTaskmasterId(string repoRoot, int taskmasterId)
    {
        using var doc = JsonDocument.Parse(File.ReadAllText(Path.Combine(repoRoot, GameplayView)));
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

        throw new InvalidOperationException($"Task {taskmasterId} not found in {GameplayView}.");
    }

    private static string[] ReadStringArray(JsonElement task, string propertyName)
    {
        task.TryGetProperty(propertyName, out var value).Should().BeTrue();
        value.ValueKind.Should().Be(JsonValueKind.Array);
        return value.EnumerateArray().Select(static item => item.GetString() ?? string.Empty).ToArray();
    }
}
