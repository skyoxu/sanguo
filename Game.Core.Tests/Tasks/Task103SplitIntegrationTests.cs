using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task103SplitIntegrationTests
{
    private const int TaskId = 103;
    private const string ThisTestRef = "Game.Core.Tests/Tasks/Task103SplitIntegrationTests.cs";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T103.1
    [Fact]
    [Trait("acceptance", "ACC:T103.1")]
    public void ShouldListTask135AndTask136EvidenceInTaskReferences_WhenTask103ClosureDependsOnRecordedSplitEvidence()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task103 = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var task103TestRefs = ReadStringArray(task103, "test_refs");
            var task103EvidenceRefs = ReadStringArray(task103, "evidence_refs");
            var task135TestRefs = ReadTaskTestRefs(repoRoot, viewFile, 135);
            var task136TestRefs = ReadTaskTestRefs(repoRoot, viewFile, 136);
            var requiredEvidenceRefs = task135TestRefs.Concat(task136TestRefs).Distinct().ToArray();

            task103TestRefs.Should().Contain(ThisTestRef);
            requiredEvidenceRefs.Should().NotBeEmpty("Task 103 closure is defined as a recorded-evidence check over split tasks 135 and 136.");

            foreach (var requiredEvidenceRef in requiredEvidenceRefs)
            {
                task103EvidenceRefs.Should().Contain(
                    requiredEvidenceRef,
                    $"Task 103 should enumerate split evidence '{requiredEvidenceRef}' in {viewFile} evidence_refs because closure depends on recorded split-task evidence.");
            }
        }
    }

    // ACC:T103.1
    [Fact]
    [Trait("acceptance", "ACC:T103.1")]
    public void ShouldKeepClosureOpen_WhenStandaloneImplementationIsClaimedBeyondClosureCheck()
    {
        var delayReplay = CreateDelayedRevealChallengeReplay();
        var hardCapReplay = CreateHardCapForcingReplay(hardCapReachedAtLeaveCampEdge: true);

        var outcome = Task103BossRevealDelayHardCapForcingIntegrationPack.Evaluate(
            delayReplay,
            hardCapReplay,
            hasTask135Evidence: true,
            hasTask136Evidence: true,
            claimsStandaloneImplementation: true);

        outcome.ClaimsStandaloneImplementation.Should().BeTrue();
        outcome.HasExplicitCombinedOutcome.Should().BeTrue();
        outcome.IsClosureComplete.Should().BeFalse(
            "Task 103 is a closure-only integration pack and must not stay closed when it claims standalone implementation beyond that closure check.");
    }

    // ACC:T103.1
    [Fact]
    [Trait("acceptance", "ACC:T103.1")]
    public void ShouldKeepClosureOpen_WhenTask135EvidenceIsMissing()
    {
        var delayReplay = CreateDelayedRevealChallengeReplay();
        var hardCapReplay = CreateHardCapForcingReplay(hardCapReachedAtLeaveCampEdge: true);

        var outcome = Task103BossRevealDelayHardCapForcingIntegrationPack.Evaluate(
            delayReplay,
            hardCapReplay,
            hasTask135Evidence: false,
            hasTask136Evidence: true,
            claimsStandaloneImplementation: false);

        outcome.HasTask135Evidence.Should().BeFalse();
        outcome.HasTask136Evidence.Should().BeTrue();
        outcome.HasExplicitCombinedOutcome.Should().BeTrue();
        outcome.IsClosureComplete.Should().BeFalse(
            "Task 103 closure requires evidence from both split tasks; missing Task 135 evidence must keep closure open.");
    }

    // ACC:T103.1
    [Fact]
    [Trait("acceptance", "ACC:T103.1")]
    public void ShouldKeepClosureOpen_WhenTask136EvidenceIsMissing()
    {
        var delayReplay = CreateDelayedRevealChallengeReplay();
        var hardCapReplay = CreateHardCapForcingReplay(hardCapReachedAtLeaveCampEdge: true);

        var outcome = Task103BossRevealDelayHardCapForcingIntegrationPack.Evaluate(
            delayReplay,
            hardCapReplay,
            hasTask135Evidence: true,
            hasTask136Evidence: false,
            claimsStandaloneImplementation: false);

        outcome.HasTask135Evidence.Should().BeTrue();
        outcome.HasTask136Evidence.Should().BeFalse();
        outcome.HasExplicitCombinedOutcome.Should().BeTrue();
        outcome.IsClosureComplete.Should().BeFalse(
            "Task 103 closure requires evidence from both split tasks; missing Task 136 evidence must keep closure open.");
    }

    // ACC:T103.2
    [Fact]
    [Trait("acceptance", "ACC:T103.2")]
    public void ShouldProveBossRevealDelayChallengeAndHardCapForcing_WhenRecordedSplitEvidenceIsCombined()
    {
        var delayReplay = CreateDelayedRevealChallengeReplay();
        var hardCapReplay = CreateHardCapForcingReplay(hardCapReachedAtLeaveCampEdge: true);

        var outcome = Task103BossRevealDelayHardCapForcingIntegrationPack.Evaluate(
            delayReplay,
            hardCapReplay,
            hasTask135Evidence: true,
            hasTask136Evidence: true,
            claimsStandaloneImplementation: false);

        outcome.ProvenBehaviors.Should().Equal("boss_reveal_delay_challenge", "hard_cap_forcing");
        outcome.HasExplicitCombinedOutcome.Should().BeTrue(
            "Task 103 closes only when split evidence explicitly proves both the delayed-reveal challenge and the hard-cap forcing branch.");
        outcome.IsClosureComplete.Should().BeTrue();
    }

    // ACC:T103.2
    [Fact]
    [Trait("acceptance", "ACC:T103.2")]
    public void ShouldKeepClosureOpen_WhenCombinedSplitEvidenceDoesNotProveBothPackBehaviors()
    {
        var delayReplay = CreateDelayedRevealChallengeReplay();
        var hardCapReplay = CreateHardCapForcingReplay(hardCapReachedAtLeaveCampEdge: false);

        var outcome = Task103BossRevealDelayHardCapForcingIntegrationPack.Evaluate(
            delayReplay,
            hardCapReplay,
            hasTask135Evidence: true,
            hasTask136Evidence: true,
            claimsStandaloneImplementation: false);

        outcome.ProvenBehaviors.Should().Equal("boss_reveal_delay_challenge");
        outcome.HasExplicitCombinedOutcome.Should().BeFalse(
            "Task 103 must stay open when the combined replay proves only delayed-reveal challenge behavior but not hard-cap forcing.");
        outcome.IsClosureComplete.Should().BeFalse();
    }

    private static BossRevealDelayPressureReplayResult CreateDelayedRevealChallengeReplay()
    {
        return BossRevealDelayPressureStackingEngine.Replay(
            new[]
            {
                "round:1:boss_revealed_delayed",
                "round:1:end",
                "round:2:boss_revealed_delayed",
                "round:2:end",
                "round:3:boss_revealed_delayed",
                "round:3:forced_challenge_preempted",
            });
    }

    private static CampPressureBoardTransitionReplayResult CreateHardCapForcingReplay(bool hardCapReachedAtLeaveCampEdge)
    {
        return CampPressureBoardTransitionSequencer.ReplayEventTypes(
            new[]
            {
                SanguoGameTurnAdvanced.EventType,
                SanguoBossChallengePrompted.EventType,
                SanguoTokenMoved.EventType,
                SanguoGameTurnEnded.EventType,
            },
            hardCapReachedAtLeaveCampEdge);
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

    private sealed record Task103IntegrationOutcome(
        IReadOnlyList<string> ProvenBehaviors,
        bool HasTask135Evidence,
        bool HasTask136Evidence,
        bool ClaimsStandaloneImplementation,
        bool HasExplicitCombinedOutcome,
        bool IsClosureComplete);

    private static class Task103BossRevealDelayHardCapForcingIntegrationPack
    {
        public static Task103IntegrationOutcome Evaluate(
            BossRevealDelayPressureReplayResult delayReplay,
            CampPressureBoardTransitionReplayResult hardCapReplay,
            bool hasTask135Evidence,
            bool hasTask136Evidence,
            bool claimsStandaloneImplementation)
        {
            var provenBehaviors = new List<string>();

            var hasExplicitDelayedRevealChallenge = delayReplay.ForcedChallengeTriggered
                && delayReplay.StateTimeline.Contains("revealed_delayed", StringComparer.Ordinal)
                && delayReplay.AuditTrail.Contains("delay_stack_applied", StringComparer.Ordinal);

            if (hasExplicitDelayedRevealChallenge)
            {
                provenBehaviors.Add("boss_reveal_delay_challenge");
            }

            var hasExplicitHardCapForcing = string.Equals(
                    hardCapReplay.BoardEntryBranch,
                    "boss_preempted_board_entry",
                    StringComparison.Ordinal)
                && hardCapReplay.Checkpoints.Contains("pressure_preempted_by_boss", StringComparer.Ordinal)
                && !hardCapReplay.Checkpoints.Contains("board_entered", StringComparer.Ordinal);

            if (hasExplicitHardCapForcing)
            {
                provenBehaviors.Add("hard_cap_forcing");
            }

            var hasExplicitCombinedOutcome = provenBehaviors.Count == 2;
            var isClosureComplete = hasTask135Evidence
                && hasTask136Evidence
                && !claimsStandaloneImplementation
                && hasExplicitCombinedOutcome;

            return new Task103IntegrationOutcome(
                provenBehaviors,
                hasTask135Evidence,
                hasTask136Evidence,
                claimsStandaloneImplementation,
                hasExplicitCombinedOutcome,
                isClosureComplete);
        }
    }
}
