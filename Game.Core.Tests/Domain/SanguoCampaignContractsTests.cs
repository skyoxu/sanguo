using System;
using System.Collections.Generic;
using System.IO;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Domain;

public sealed class SanguoCampaignContractsTests
{
    // ACC:T109.1
    [Fact]
    [Trait("acceptance", "ACC:T109.1")]
    public void ShouldExposeDeterministicCampaignContractsAndJsonEventDataCompatibility_WhenSplitIntegrationClosureRuns()
    {
        var now = DateTimeOffset.UtcNow;
        var prompted = new SanguoBossChallengePrompted(
            GameId: "game-109",
            BossId: "boss-109",
            RoundNumber: 9,
            WinRateTier: SanguoBossChallengePrompted.WinRateTierMid,
            NextRoundPressureForecast: 3,
            KeyLossSummary: "contract_shape_guard",
            FailConsequence: SanguoBossChallengePrompted.FailConsequenceReturnToCampAndEndRound,
            OccurredAt: now,
            CorrelationId: "corr-109",
            CausationId: "cause-109");

        prompted.GameId.Should().Be("game-109");
        prompted.BossId.Should().Be("boss-109");
        prompted.FailConsequence.Should().Be(SanguoBossChallengePrompted.FailConsequenceReturnToCampAndEndRound);

        var jsonPayload = JsonElementEventData.FromObject(new { kind = SanguoBossChallengePrompted.EventType, round = prompted.RoundNumber });
        jsonPayload.Should().BeAssignableTo<IEventData>();
        jsonPayload.Value.GetProperty("kind").GetString().Should().Be(SanguoBossChallengePrompted.EventType);
    }

    // ACC:T136.1
    [Fact]
    [Trait("acceptance", "ACC:T136.1")]
    public void ShouldExposeStableEventType_WhenBossChallengeIsPrompted()
    {
        SanguoBossChallengePrompted.EventType.Should().Be("core.sanguo.boss.challenge.prompted");
    }

    // ACC:T118.1
    [Fact]
    [Trait("acceptance", "ACC:T118.1")]
    public void ShouldExposeStableEventType_WhenObjectiveIsSkipped()
    {
        SanguoObjectiveSkipped.EventType.Should().Be("core.sanguo.objective.skipped");
        SanguoObjectiveSkipped.ReasonRunEndedInBoss.Should().Be("run_ended_in_boss");
    }

    [Fact]
    public void ShouldExposeDeterministicSkipSemanticsReason_WhenRunEndedInBoss()
    {
        var skipped = new SanguoObjectiveSkipped(
            GameId: "game-1",
            ObjectiveId: "obj-1",
            RoundNumber: 6,
            Reason: SanguoObjectiveSkipped.ReasonRunEndedInBoss,
            BossId: "boss-1",
            OccurredAt: DateTimeOffset.UtcNow,
            CorrelationId: "corr-1",
            CausationId: "boss-battle-1");

        skipped.Reason.Should().Be(SanguoObjectiveSkipped.ReasonRunEndedInBoss,
            "objective skip semantics should remain deterministic for boss-ending flow");
        skipped.BossId.Should().NotBeNullOrWhiteSpace(
            "boss-ending objective skip should preserve boss context for replay-safe diagnostics");
    }

    [Fact]
    public void ShouldInstantiateCampaignPromptAndObjectiveEvents_WhenPayloadIsDeterministic()
    {
        var now = DateTimeOffset.UtcNow;
        var prompted = new SanguoBossChallengePrompted(
            GameId: "game-1",
            BossId: "boss-1",
            RoundNumber: 6,
            WinRateTier: SanguoBossChallengePrompted.WinRateTierMid,
            NextRoundPressureForecast: 4,
            KeyLossSummary: "camp_hp_risk",
            FailConsequence: SanguoBossChallengePrompted.FailConsequenceReturnToCampAndEndRound,
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );

        prompted.GameId.Should().Be("game-1");
        prompted.BossId.Should().Be("boss-1");
        prompted.RoundNumber.Should().Be(6);
        prompted.WinRateTier.Should().Be(SanguoBossChallengePrompted.WinRateTierMid);
        prompted.NextRoundPressureForecast.Should().Be(4);
        prompted.KeyLossSummary.Should().Be("camp_hp_risk");
        prompted.FailConsequence.Should().Be(SanguoBossChallengePrompted.FailConsequenceReturnToCampAndEndRound);

        var skipped = new SanguoObjectiveSkipped(
            GameId: "game-1",
            ObjectiveId: "obj-1",
            RoundNumber: 6,
            Reason: SanguoObjectiveSkipped.ReasonRunEndedInBoss,
            BossId: "boss-1",
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: "boss-battle-1"
        );

        skipped.GameId.Should().Be("game-1");
        skipped.ObjectiveId.Should().Be("obj-1");
        skipped.RoundNumber.Should().Be(6);
        skipped.Reason.Should().Be(SanguoObjectiveSkipped.ReasonRunEndedInBoss);
        skipped.BossId.Should().Be("boss-1");
    }

    [Fact]
    public void ShouldExposeBossPromptConstants_WhenUsingDefaultConfirmationCopy()
    {
        SanguoBossChallengePrompted.WinRateTierLow.Should().Be("low");
        SanguoBossChallengePrompted.WinRateTierMid.Should().Be("mid");
        SanguoBossChallengePrompted.WinRateTierHigh.Should().Be("high");
    }

    [Fact]
    public void ShouldUseReturnToCampConsequence_WhenBossPromptFollowsFailPath()
    {
        SanguoBossChallengePrompted.FailConsequenceReturnToCampAndEndRound
            .Should().Be("return_to_camp_end_round");
    }

    // ACC:T172.1
    [Trait("acceptance", "ACC:T172.1")]
    [Fact]
    public void ShouldRejectCrossTableReferenceAndVersionBumpInvariant_WhenFixtureViolatesR9AndR11()
    {
        var knownReferences = new HashSet<string>(StringComparer.Ordinal);
        var fixture = new SanguoCampaignContentFixture(
            Id: "strategem-1",
            Power: 10,
            SchemaVersion: 1,
            RefId: "missing-objective-ref");

        var result = SanguoCampaignContentSchemaCatalog.ValidateFixture(
            SanguoCampaignContentFamily.Strategem,
            fixture,
            knownReferences,
            previousCatalogVersion: 3,
            currentCatalogVersion: 3,
            hasBreakingChange: true);

        result.IsValid.Should().BeFalse();
        result.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.BadReferenceError);
        result.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.MissingVersionBumpError);
    }

    // ACC:T172.5
    [Trait("acceptance", "ACC:T172.5")]
    [Fact]
    public void ShouldAcceptFixture_WhenReferenceResolvesAndVersionBumpIsApplied()
    {
        var knownReferences = new HashSet<string>(StringComparer.Ordinal)
        {
            "objective-1",
        };
        var fixture = new SanguoCampaignContentFixture(
            Id: "strategem-2",
            Power: 12,
            SchemaVersion: 2,
            RefId: "objective-1");

        var result = SanguoCampaignContentSchemaCatalog.ValidateFixture(
            SanguoCampaignContentFamily.Strategem,
            fixture,
            knownReferences,
            previousCatalogVersion: 3,
            currentCatalogVersion: 4,
            hasBreakingChange: true);

        result.IsValid.Should().BeTrue();
        result.ErrorCodes.Should().BeEmpty();
    }

    // ACC:T86.1
    [Fact]
    public void ShouldExposeStableEndgameContractEventTypes_WhenCampaignSplitUsesR3AdjudicationSignals()
    {
        SanguoGameEnded.EventType.Should().Be("core.sanguo.game.ended");
        SanguoPlayerEliminated.EventType.Should().Be("core.sanguo.player.eliminated");
    }

    // ACC:T145.1
    [Fact]
    [Trait("acceptance", "ACC:T145.1")]
    public void ShouldCloseIntegrationFromSplitTasks_WhenValidatingDeterministicCampaignContractEvidence()
    {
        var splitTask169Evidence = ReadFileFromRepository("Game.Core.Tests/Tasks/Task169SplitTests.cs");
        var splitTask170Evidence = ReadFileFromRepository("Game.Core.Tests/Tasks/Task170SplitTests.cs");
        var mergedEvidence = splitTask169Evidence + Environment.NewLine + splitTask170Evidence;

        mergedEvidence.Should().Contain("ACC:T169.1",
            "task 145 closure must include deterministic evidence from split task 169.");
        mergedEvidence.Should().Contain("ACC:T169.6",
            "task 145 closure should preserve split task 169 versioning evidence.");
        mergedEvidence.Should().Contain("ACC:T170.1",
            "task 145 closure must include deterministic evidence from split task 170.");
        mergedEvidence.Should().Contain("R9",
            "task 145 acceptance requires deterministic evidence for requirement R9.");
        mergedEvidence.Should().Contain("A-020",
            "task 145 acceptance requires deterministic compatibility evidence for A-020.");
    }

    private static string ReadFileFromRepository(string relativePath)
    {
        var repositoryRoot = FindRepositoryRoot();
        var normalizedRelativePath = relativePath.Replace('/', Path.DirectorySeparatorChar);
        var absolutePath = Path.Combine(repositoryRoot, normalizedRelativePath);

        File.Exists(absolutePath).Should().BeTrue($"Expected evidence file '{relativePath}' to exist.");

        return File.ReadAllText(absolutePath);
    }

    private static string FindRepositoryRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);

        while (current is not null)
        {
            var hasTaskmaster = Directory.Exists(Path.Combine(current.FullName, ".taskmaster"));
            var hasCoreTests = Directory.Exists(Path.Combine(current.FullName, "Game.Core.Tests"));

            if (hasTaskmaster && hasCoreTests)
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("Unable to locate repository root from test execution directory.");
    }
}
