using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task149CampaignBossVictoryScenarioTests
{
    // ACC:T149.1
    [Fact]
    public void ShouldReturnFinalBossVictoryOutcome_WhenFinalBossDefeatBranchIsTrue()
    {
        var outcome = CampaignEndgameAdjudicator.EvaluateFinalBossDefeatVictory(
            isFinalBossDefeated: true,
            winnerPlayerId: "player-a");

        outcome.ShouldEndGame.Should().BeTrue();
        outcome.EndReason.Should().Be(SanguoGameEnded.ReasonFinalBossDefeated);
        outcome.WinnerPlayerId.Should().Be("player-a");
        outcome.SplitScope.Should().Be(CampaignEndgameAdjudicator.SplitScopeR3);
    }

    // ACC:T149.2
    [Fact]
    public void ShouldReturnStableOutcome_WhenFinalBossDefeatInputsRepeat()
    {
        var first = CampaignEndgameAdjudicator.EvaluateFinalBossDefeatVictory(
            isFinalBossDefeated: true,
            winnerPlayerId: "player-a");
        var second = CampaignEndgameAdjudicator.EvaluateFinalBossDefeatVictory(
            isFinalBossDefeated: true,
            winnerPlayerId: "player-a");

        first.Should().BeEquivalentTo(second);
    }

    // ACC:T149.3
    [Fact]
    public void ShouldNotReturnVictoryOutcome_WhenFinalBossDefeatBranchIsFalse()
    {
        var outcome = CampaignEndgameAdjudicator.EvaluateFinalBossDefeatVictory(
            isFinalBossDefeated: false,
            winnerPlayerId: "player-a");

        outcome.ShouldEndGame.Should().BeFalse();
        outcome.EndReason.Should().BeNull();
        outcome.WinnerPlayerId.Should().BeNull();
        outcome.SplitScope.Should().Be(CampaignEndgameAdjudicator.SplitScopeR3);
    }

    // ACC:T149.4
    [Fact]
    public void ShouldKeepFinalBossReasonSeparatedFromCampFailureReason_WhenAdjudicationBranchesCompare()
    {
        var victory = CampaignEndgameAdjudicator.EvaluateFinalBossDefeatVictory(
            isFinalBossDefeated: true,
            winnerPlayerId: "player-a");
        var campFailure = CampaignEndgameAdjudicator.EvaluateCampFailureDefeat(
            isCampDurabilityFatal: true);

        victory.EndReason.Should().Be(SanguoGameEnded.ReasonFinalBossDefeated);
        campFailure.EndReason.Should().Be(CampFailSettlementRouter.EndReasonCampDurabilityFatal);
        campFailure.EndReason.Should().NotBe(SanguoGameEnded.ReasonFinalBossDefeated);
    }
}
