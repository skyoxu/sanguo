using System;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Domain;

public sealed class SanguoCampaignContractsTests
{
    [Fact]
    public void ShouldExposeStableEventType_WhenBossChallengeIsPrompted()
    {
        SanguoBossChallengePrompted.EventType.Should().Be("core.sanguo.boss.challenge.prompted");
    }

    [Fact]
    public void ShouldExposeStableEventType_WhenObjectiveIsSkipped()
    {
        SanguoObjectiveSkipped.EventType.Should().Be("core.sanguo.objective.skipped");
        SanguoObjectiveSkipped.ReasonRunEndedInBoss.Should().Be("run_ended_in_boss");
    }

    [Fact]
    public void ShouldInstantiateCampaignPromptAndObjectiveEvents_WithDeterministicPayload()
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
    public void A006_ShouldExposeBossPromptConstants_ForDefaultConfirmationCopy()
    {
        SanguoBossChallengePrompted.WinRateTierLow.Should().Be("low");
        SanguoBossChallengePrompted.WinRateTierMid.Should().Be("mid");
        SanguoBossChallengePrompted.WinRateTierHigh.Should().Be("high");
    }

    [Fact]
    public void A007_ShouldUseReturnToCampConsequence_ForBossPromptFailPath()
    {
        SanguoBossChallengePrompted.FailConsequenceReturnToCampAndEndRound
            .Should().Be("return_to_camp_end_round");
    }
}
