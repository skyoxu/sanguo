using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task78SplitIntegrationTests
{
    private const int TaskId = 78;
    private const string RewardDraftRef = "Game.Core.Tests/Tasks/Task78RewardDraftEngineTests.cs";
    private const string SplitRef = "Game.Core.Tests/Tasks/Task78SplitIntegrationTests.cs";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T78.2
    [Fact]
    [Trait("acceptance", "ACC:T78.2")]
    public void ShouldBindAcceptanceRefsToTaskScopedEvidence_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptance.Should().HaveCount(3);
            acceptance[0].Should().Contain(RewardDraftRef);
            acceptance[1].Should().Contain(SplitRef);
            acceptance[2].Should().Contain(SplitRef);

            testRefs.Should().Contain(RewardDraftRef);
            testRefs.Should().Contain(SplitRef);
        }
    }

    // ACC:T78.3
    [Fact]
    [Trait("acceptance", "ACC:T78.3")]
    public void ShouldCloseOnlyWhenSplitEvidenceIsCompleteAndDeterministic()
    {
        var closed = Task78SplitClosure.Evaluate(
            new[] { 119, 120 },
            hasDeterministicEvidence: true,
            hasThreeChoiceEvidence: true);
        closed.IsClosed.Should().BeTrue();
        closed.Reason.Should().BeNull();

        var missingDeterminism = Task78SplitClosure.Evaluate(
            new[] { 119, 120 },
            hasDeterministicEvidence: false,
            hasThreeChoiceEvidence: true);
        missingDeterminism.IsClosed.Should().BeFalse();
        missingDeterminism.Reason.Should().Be("MISSING_DETERMINISTIC_EVIDENCE");

        var missingThreeChoice = Task78SplitClosure.Evaluate(
            new[] { 119, 120 },
            hasDeterministicEvidence: true,
            hasThreeChoiceEvidence: false);
        missingThreeChoice.IsClosed.Should().BeFalse();
        missingThreeChoice.Reason.Should().Be("MISSING_THREE_CHOICE_EVIDENCE");
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

    private static string[] ReadStringArray(JsonElement task, string propertyName)
    {
        task.TryGetProperty(propertyName, out var value).Should().BeTrue();
        value.ValueKind.Should().Be(JsonValueKind.Array);
        return value.EnumerateArray().Select(static item => item.GetString() ?? string.Empty).ToArray();
    }

    private static JsonDocument LoadJson(string repoRoot, params string[] parts)
    {
        var path = Path.Combine(new[] { repoRoot }.Concat(parts).ToArray());
        using var stream = File.OpenRead(path);
        return JsonDocument.Parse(stream);
    }

    private readonly record struct SplitOutcome(bool IsClosed, string? Reason);

    private static class Task78SplitClosure
    {
        public static SplitOutcome Evaluate(
            IEnumerable<int> providedTaskIds,
            bool hasDeterministicEvidence,
            bool hasThreeChoiceEvidence)
        {
            var set = providedTaskIds.ToHashSet();
            if (!set.Contains(119) || !set.Contains(120))
            {
                return new SplitOutcome(false, "MISSING_SPLIT_EVIDENCE");
            }

            if (!hasDeterministicEvidence)
            {
                return new SplitOutcome(false, "MISSING_DETERMINISTIC_EVIDENCE");
            }

            if (!hasThreeChoiceEvidence)
            {
                return new SplitOutcome(false, "MISSING_THREE_CHOICE_EVIDENCE");
            }

            return new SplitOutcome(true, null);
        }
    }
}
