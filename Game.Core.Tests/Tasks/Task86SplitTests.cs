using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task86SplitTests
{
    private const int TaskId = 86;

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    private static readonly string[] ExpectedTaskRefs =
    {
        "Game.Core.Tests/Tasks/Task86SplitTests.cs",
        "Game.Core.Tests/Domain/SanguoCampaignContractsTests.cs",
    };

    // ACC:T86.1
    [Fact]
    [Trait("acceptance", "ACC:T86.1")]
    public void ShouldKeepIndependentR3SplitNarrative_WhenReadingTask86AcceptanceFromBothViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptanceRefs = ReadStringArray(task, "acceptanceRefs");
            var acceptance = ReadStringArray(task, "acceptance");

            acceptanceRefs.Should().Equal("R3");
            acceptance.Should().HaveCount(5);

            var splitScopeAcceptance = acceptance[0];
            splitScopeAcceptance.Should().Contain("independent R3 split from T74");
            splitScopeAcceptance.Should().Contain("did not expand beyond that narrow split scope");
            splitScopeAcceptance.Should().Contain("Game.Core.Tests/Tasks/Task86SplitTests.cs");
            splitScopeAcceptance.Should().Contain("Game.Core.Tests/Domain/SanguoCampaignContractsTests.cs");

            acceptance[1].Should().Contain("human elimination ends the run with player_bankrupt");
            acceptance[2].Should().Contain("run started with at least two players");
            acceptance[2].Should().Contain("last_actor_standing");
            acceptance[3].Should().Contain("no players remain after prune");
            acceptance[3].Should().Contain("no_players");
            acceptance[4].Should().Contain("no endgame condition is satisfied");
            acceptance[4].Should().Contain("no end reason is forced");
            acceptance.Skip(1).Should().OnlyContain(item => item.Contains("Game.Core.Tests/Tasks/Task86SplitTests.cs", StringComparison.Ordinal));
        }
    }

    [Fact]
    public void ShouldRefuseEvidenceScopeExpansion_WhenReadingTask86TestRefsFromBothViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var testRefs = ReadStringArray(task, "test_refs");

            testRefs.Should().HaveCount(2, "Task 86 is scoped as a narrow split and must not grow extra evidence files.");
            testRefs.Should().Equal(ExpectedTaskRefs);
            testRefs.Should().OnlyContain(testRef => ExpectedTaskRefs.Contains(testRef, StringComparer.Ordinal));
        }
    }

    // ACC:T86.2
    [Fact]
    [Trait("acceptance", "ACC:T86.2")]
    public void ShouldReturnPlayerBankruptReason_WhenHumanPlayerIsEliminated()
    {
        var outcome = CampaignEndgameAdjudicator.EvaluateHumanElimination(
            playerOrder: new[] { "human-1", "ai-1" },
            isAiPlayerId: static playerId => playerId.StartsWith("ai-", StringComparison.Ordinal),
            isPlayerEliminated: static playerId => string.Equals(playerId, "human-1", StringComparison.Ordinal));

        outcome.ShouldEndGame.Should().BeTrue();
        outcome.EndReason.Should().Be(SanguoGameEnded.ReasonPlayerBankrupt);
        outcome.WinnerPlayerId.Should().BeNull();
        outcome.SplitScope.Should().Be(CampaignEndgameAdjudicator.SplitScopeR3);
    }

    // ACC:T86.3
    [Fact]
    [Trait("acceptance", "ACC:T86.3")]
    public void ShouldReturnLastActorStandingReason_WhenOnlyOnePlayerRemainsAfterPrune()
    {
        var outcome = CampaignEndgameAdjudicator.EvaluatePostPrune(
            startingPlayersCount: 4,
            remainingPlayerOrder: new[] { "winner-1" });

        outcome.ShouldEndGame.Should().BeTrue();
        outcome.EndReason.Should().Be(SanguoGameEnded.ReasonLastActorStanding);
        outcome.WinnerPlayerId.Should().Be("winner-1");
        outcome.SplitScope.Should().Be(CampaignEndgameAdjudicator.SplitScopeR3);
    }

    // ACC:T86.4
    [Fact]
    [Trait("acceptance", "ACC:T86.4")]
    public void ShouldReturnNoPlayersReason_WhenPruneLeavesNoPlayers()
    {
        var outcome = CampaignEndgameAdjudicator.EvaluatePostPrune(
            startingPlayersCount: 2,
            remainingPlayerOrder: Array.Empty<string>());

        outcome.ShouldEndGame.Should().BeTrue();
        outcome.EndReason.Should().Be(SanguoGameEnded.ReasonNoPlayers);
        outcome.WinnerPlayerId.Should().BeNull();
        outcome.SplitScope.Should().Be(CampaignEndgameAdjudicator.SplitScopeR3);
    }

    // ACC:T86.5
    [Fact]
    [Trait("acceptance", "ACC:T86.5")]
    public void ShouldKeepGameRunning_WhenNoEndgameConditionIsSatisfied()
    {
        var eliminationOutcome = CampaignEndgameAdjudicator.EvaluateHumanElimination(
            playerOrder: new[] { "human-1", "ai-1" },
            isAiPlayerId: static playerId => playerId.StartsWith("ai-", StringComparison.Ordinal),
            isPlayerEliminated: static _ => false);
        var postPruneOutcome = CampaignEndgameAdjudicator.EvaluatePostPrune(
            startingPlayersCount: 4,
            remainingPlayerOrder: new[] { "human-1", "ai-1" });

        eliminationOutcome.ShouldEndGame.Should().BeFalse();
        eliminationOutcome.EndReason.Should().BeNull();
        postPruneOutcome.ShouldEndGame.Should().BeFalse();
        postPruneOutcome.EndReason.Should().BeNull();
    }

    [Fact]
    public void ShouldRequireDedicatedAdjudicatorModule_WhenValidatingIndependentR3SplitDelivery()
    {
        var repoRoot = FindRepoRoot();
        var adjudicatorPath = Path.Combine(repoRoot, "Game.Core", "Services", "Sanguo", "CampaignEndgameAdjudicator.cs");

        File.Exists(adjudicatorPath).Should().BeTrue(
            "Task 86 claims an independent endgame adjudicator split and should provide a dedicated adjudicator module.");

        var source = File.ReadAllText(adjudicatorPath);
        source.Should().Contain("SanguoGameEnded", "R3 adjudication should own the game-ended contract emission path.");
        source.Should().Contain("SanguoPlayerEliminated", "R3 adjudication should evaluate elimination and endgame outcomes together.");
        source.Should().NotContain("Task 74", "the split module should not rely on parent-task wiring details.");
        source.Should().NotContain("T74", "the split module should remain independent from parent-task coupling.");
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
