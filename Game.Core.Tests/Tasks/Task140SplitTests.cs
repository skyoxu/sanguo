using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task140SplitTests
{
    private const int TaskId = 140;
    private const string ExpectedCoreRef = "Game.Core.Tests/Tasks/Task140SplitTests.cs";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T140.1
    [Fact]
    [Trait("acceptance", "ACC:T140.1")]
    public void ShouldSettlePreviousObjectiveAtCampAndSuppressNewPublish_WhenRunEndsInBoss()
    {
        var replayResult = CampPressureBoardTransitionSequencer.ReplayEventTypes(new[]
        {
            SanguoGameTurnAdvanced.EventType,
            SanguoBossChallengePrompted.EventType,
            SanguoCombatStarted.EventType,
            SanguoCombatEnded.EventType,
            SanguoGameEnded.EventType,
            SanguoTokenMoved.EventType,
        });

        var checkpoints = replayResult.Checkpoints.ToList();

        checkpoints.Should().ContainInOrder(
            "camp_entered",
            "objective_settled",
            "pressure_entered",
            "pressure_preempted_by_boss");
        checkpoints.Should().NotContain(
            "objective_published",
            "when game end is already determined, new objective publish must be suppressed.");
    }

    [Fact]
    public void ShouldPublishObjective_WhenBossBranchCompletesWithoutGameEnded()
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

        checkpoints.Should().Contain("objective_settled");
        checkpoints.Should().Contain(
            "objective_published",
            "objective publish should remain available when the run has not ended.");
    }

    [Fact]
    public void ShouldKeepTaskSpecificAcceptanceEvidence_WhenReadingTask140FromBothViews()
    {
        var repoRoot = FindRepoRoot();
        var sourcePath = Path.Combine(repoRoot, ExpectedCoreRef.Replace('/', Path.DirectorySeparatorChar));

        File.Exists(sourcePath).Should().BeTrue("task-specific deterministic evidence must be stored in the referenced test file");
        ContainsTokenInFile(sourcePath, "ACC:T140.1").Should().BeTrue();
        ContainsTokenInFile(sourcePath, "ShouldSettlePreviousObjectiveAtCampAndSuppressNewPublish_WhenRunEndsInBoss")
            .Should().BeTrue();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptance.Should().ContainSingle();
            acceptance[0].Should().Contain("Previous objective settles at camp and new objective publish is suppressed when the game ends");
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
}
