using System;
using System.Linq;
using System.Reflection;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task144SplitTests
{
    // ACC:T144.2
    [Fact]
    [Trait("acceptance", "ACC:T144.2")]
    public void ShouldNotTriggerDefeatSettlement_WhenCampDurabilityIsNotFatal()
    {
        var router = new CampFailSettlementRouter();
        var initialState = SettlementRouteState.InProgress();

        var result = router.Route(initialState, campDurability: 2, currentTick: 9);

        result.NextScreen.Should().Be(CampFailSettlementRouter.InProgressScreen);
        result.EndReason.Should().BeNull("non-fatal camp durability must not trigger the camp-failure defeat branch");
        result.NextState.Should().Be(initialState);
        result.DeadlockDetected.Should().BeFalse();
    }

    [Fact]
    public void ShouldNotAdjudicateCampFailureDefeat_WhenCampConditionIsNotFatal()
    {
        var method = FindCampFailureDefeatBranch();

        method.Should().NotBeNull(
            "Task 144 requires a dedicated campaign defeat adjudication branch for camp failure instead of leaking into unrelated endgame rules.");

        var outcome = InvokeCampFailureBranch(method!, isCampDurabilityFatal: false);

        outcome.ShouldEndGame.Should().BeFalse("the camp-failure defeat branch must stay inactive while the camp condition is not fatal");
        outcome.EndReason.Should().BeNull();
        outcome.WinnerPlayerId.Should().BeNull();
        outcome.SplitScope.Should().Be(CampaignEndgameAdjudicator.SplitScopeR3);
    }

    // ACC:T144.1
    [Fact]
    public void ShouldReturnCampDurabilityFatalDefeat_WhenCampConditionIsFatal()
    {
        var method = FindCampFailureDefeatBranch();

        method.Should().NotBeNull(
            "Task 144 requires a fatal camp-failure defeat adjudication branch alongside the final boss victory branch.");

        var outcome = InvokeCampFailureBranch(method!, isCampDurabilityFatal: true);

        outcome.ShouldEndGame.Should().BeTrue("fatal camp durability must terminate the campaign from the dedicated camp-failure defeat branch");
        outcome.EndReason.Should().Be(CampFailSettlementRouter.EndReasonCampDurabilityFatal);
        outcome.WinnerPlayerId.Should().BeNull();
        outcome.SplitScope.Should().Be(CampaignEndgameAdjudicator.SplitScopeR3);
        SanguoGameEnded.ReasonPlayerBankrupt.Should().NotBe(CampFailSettlementRouter.EndReasonCampDurabilityFatal);
        SanguoGameEnded.ReasonFinalBossDefeated.Should().NotBe(CampFailSettlementRouter.EndReasonCampDurabilityFatal);
    }

    private static MethodInfo? FindCampFailureDefeatBranch()
    {
        return typeof(CampaignEndgameAdjudicator)
            .GetMethods(BindingFlags.Public | BindingFlags.Static)
            .SingleOrDefault(method =>
                method.ReturnType == typeof(CampaignEndgameAdjudicationOutcome) &&
                method.Name.Contains("Camp", StringComparison.Ordinal) &&
                (method.Name.Contains("Failure", StringComparison.Ordinal) ||
                 method.Name.Contains("Defeat", StringComparison.Ordinal)));
    }

    private static CampaignEndgameAdjudicationOutcome InvokeCampFailureBranch(MethodInfo method, bool isCampDurabilityFatal)
    {
        var parameters = method.GetParameters();
        object?[] arguments;

        if (parameters.Length == 1 && parameters[0].ParameterType == typeof(bool))
        {
            arguments = new object?[] { isCampDurabilityFatal };
        }
        else if (parameters.Length == 1 && parameters[0].ParameterType == typeof(int))
        {
            arguments = new object?[] { isCampDurabilityFatal ? 0 : 1 };
        }
        else if (parameters.Length == 2 &&
                 parameters[0].ParameterType == typeof(bool) &&
                 parameters[1].ParameterType == typeof(string))
        {
            arguments = new object?[] { isCampDurabilityFatal, null };
        }
        else if (parameters.Length == 2 &&
                 parameters[0].ParameterType == typeof(int) &&
                 parameters[1].ParameterType == typeof(string))
        {
            arguments = new object?[] { isCampDurabilityFatal ? 0 : 1, null };
        }
        else
        {
            throw new InvalidOperationException(
                $"Camp failure defeat branch must accept either (bool), (int), (bool, string), or (int, string), but was ({string.Join(", ", parameters.Select(parameter => parameter.ParameterType.Name))}).");
        }

        var result = method.Invoke(null, arguments);
        result.Should().BeOfType<CampaignEndgameAdjudicationOutcome>();
        return (CampaignEndgameAdjudicationOutcome)result!;
    }
}
