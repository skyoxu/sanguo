using System;
using System.Linq;
using System.Reflection;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task143SplitTests
{
    // ACC:T143.1
    [Fact]
    [Trait("acceptance", "ACC:T143.1")]
    public void ShouldExposeFinalBossVictoryReason_WhenCampaignWinUsesDedicatedAdjudicationBranch()
    {
        var finalBossVictoryReason = typeof(SanguoGameEnded)
            .GetFields(BindingFlags.Public | BindingFlags.Static)
            .Where(field => field.IsLiteral && !field.IsInitOnly && field.FieldType == typeof(string))
            .Select(field => field.GetRawConstantValue() as string)
            .FirstOrDefault(value => string.Equals(value, "final_boss_defeated", StringComparison.Ordinal));

        finalBossVictoryReason.Should().Be(
            "final_boss_defeated",
            "Task 143 requires a dedicated campaign win reason for the final boss defeat branch.");
    }

    // ACC:T143.1
    [Fact]
    [Trait("acceptance", "ACC:T143.1")]
    public void ShouldKeepNonBossOutcomesOffVictoryBranch_WhenCampaignEndgameAdjudicatorEnumeratesR3Entries()
    {
        var methodNames = typeof(CampaignEndgameAdjudicator)
            .GetMethods(BindingFlags.Public | BindingFlags.Static)
            .Select(method => method.Name)
            .ToArray();

        methodNames.Should().Contain("EvaluateHumanElimination");
        methodNames.Should().Contain("EvaluatePostPrune");
        methodNames.Should().Contain(
            name => name.Contains("FinalBoss", StringComparison.Ordinal) ||
                    name.Contains("BossDefeat", StringComparison.Ordinal) ||
                    name.Contains("CampaignVictory", StringComparison.Ordinal),
            "Task 143 requires a dedicated final boss victory branch in addition to the existing non-boss R3 endgame branches.");

        SanguoGameEnded.ReasonNoPlayers.Should().NotBe("final_boss_defeated");
        SanguoGameEnded.ReasonLastActorStanding.Should().NotBe("final_boss_defeated");
        SanguoGameEnded.ReasonPlayerBankrupt.Should().NotBe("final_boss_defeated");
    }

    // ACC:T143.1
    [Fact]
    [Trait("acceptance", "ACC:T143.1")]
    public void ShouldAdjudicateCampaignWinOnly_WhenFinalBossDefeatBranchIsTrue()
    {
        var noBossOutcome = CampaignEndgameAdjudicator.EvaluateFinalBossDefeatVictory(
            isFinalBossDefeated: false,
            winnerPlayerId: "player-a");
        var finalBossOutcome = CampaignEndgameAdjudicator.EvaluateFinalBossDefeatVictory(
            isFinalBossDefeated: true,
            winnerPlayerId: "player-a");

        noBossOutcome.ShouldEndGame.Should().BeFalse();
        noBossOutcome.EndReason.Should().BeNull();

        finalBossOutcome.ShouldEndGame.Should().BeTrue();
        finalBossOutcome.EndReason.Should().Be(SanguoGameEnded.ReasonFinalBossDefeated);
        finalBossOutcome.WinnerPlayerId.Should().Be("player-a");
    }
}
