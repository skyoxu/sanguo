using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task139SplitTests
{
    private const int TaskId = 139;
    private const string ExpectedCoreRef = "Game.Core.Tests/Tasks/Task139SplitTests.cs";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T139.1
    [Fact]
    [Trait("acceptance", "ACC:T139.1")]
    public void ShouldKeepObjectiveUnpublished_WhenBossBranchIsStillInProgress()
    {
        var replayResult = CampPressureBoardTransitionSequencer.ReplayEventTypes(new[]
        {
            SanguoGameTurnAdvanced.EventType,
            SanguoBossChallengePrompted.EventType,
            SanguoCombatStarted.EventType,
        });

        replayResult.Checkpoints.Should().NotContain(
            "objective_published",
            "the leave-camp timeline must not publish the round objective before the boss branch has completed");
        replayResult.Checkpoints.Should().NotContain(
            "board_entered",
            "board entry must remain blocked while the boss branch is still in progress");
    }

    [Fact]
    [Trait("acceptance", "ACC:T139.1")]
    public void ShouldPublishObjectiveAfterBossCompletion_WhenCampLeaveTimelineReplays()
    {
        var replayResult = CampPressureBoardTransitionSequencer.ReplayEventTypes(new[]
        {
            SanguoGameTurnAdvanced.EventType,
            SanguoBossChallengePrompted.EventType,
            SanguoCombatStarted.EventType,
            SanguoCombatEnded.EventType,
            SanguoTokenMoved.EventType,
        });

        var checkpoints = replayResult.Checkpoints.ToList();

        checkpoints.Should().Contain(
            "objective_published",
            "the leave-camp timeline should publish the current-round objective after the boss branch completes");
        checkpoints.Should().ContainInOrder(
            "camp_entered",
            "pressure_entered",
            "pressure_preempted_by_boss",
            "objective_published",
            "board_entered");
    }

    [Fact]
    public void ShouldKeepTaskSpecificAcceptanceEvidence_WhenReadingTask139FromBothViews()
    {
        var repoRoot = FindRepoRoot();
        var sourcePath = Path.Combine(repoRoot, ExpectedCoreRef.Replace('/', Path.DirectorySeparatorChar));

        File.Exists(sourcePath).Should().BeTrue("task-specific deterministic evidence must be stored in the referenced test file");

        var sourceText = File.ReadAllText(sourcePath);
        sourceText.Should().Contain("ACC:T139.1");
        sourceText.Should().Contain("ShouldKeepObjectiveUnpublished_WhenBossBranchIsStillInProgress");
        sourceText.Should().Contain("ShouldPublishObjectiveAfterBossCompletion_WhenCampLeaveTimelineReplays");

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptance.Should().ContainSingle();
            acceptance[0].Should().Contain("objective remains unpublished until the boss branch is completed");
            acceptance.Should().OnlyContain(item => item.Contains(ExpectedCoreRef, StringComparison.Ordinal));

            testRefs.Should().ContainSingle().Which.Should().Be(ExpectedCoreRef);
        }
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

    private static JsonDocument LoadJson(string repoRoot, params string[] relativeParts)
    {
        var path = Path.Combine(new[] { repoRoot }.Concat(relativeParts).ToArray());
        var text = File.ReadAllText(path);
        return JsonDocument.Parse(text);
    }
}
