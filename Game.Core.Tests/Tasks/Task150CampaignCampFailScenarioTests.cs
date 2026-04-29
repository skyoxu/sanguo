using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task150CampaignCampFailScenarioTests
{
    // ACC:T150.1
    [Fact]
    [Trait("acceptance", "ACC:T150.1")]
    public void ShouldProduceCampFailDefeatWithDeterministicEvidenceScope_WhenCampaignRunsFromStartToFatalCampDurability()
    {
        const int checkpointTick91 = 91;
        var steps = new List<string>();
        var router = new CampFailSettlementRouter();
        var routeState = SettlementRouteState.InProgress();

        steps.Add("campaign_started");
        routeState.CurrentScreen.Should().Be(CampFailSettlementRouter.InProgressScreen);
        routeState.LastProcessedTick.Should().Be(-1);

        var routeResult = router.Route(routeState, campDurability: 0, currentTick: checkpointTick91);
        steps.Add(routeResult.NextScreen);

        var adjudication = CampaignEndgameAdjudicator.EvaluateCampFailureDefeat(
            isCampDurabilityFatal: routeResult.EndReason == CampFailSettlementRouter.EndReasonCampDurabilityFatal);
        steps.Add(adjudication.EndReason ?? "none");

        routeResult.NextScreen.Should().Be("defeat_settlement");
        routeResult.EndReason.Should().Be(CampFailSettlementRouter.EndReasonCampDurabilityFatal);

        routeResult.EvidenceScope.Should().Be(CampFailSettlementRouter.EvidenceScopeR3);
        routeResult.NextState.LastProcessedTick.Should().Be(checkpointTick91);
        var checkpointTag = $"9.{routeResult.NextState.LastProcessedTick - 90}";
        checkpointTag.Should().Be("9.1");

        adjudication.ShouldEndGame.Should().BeTrue();
        adjudication.EndReason.Should().Be(CampFailSettlementRouter.EndReasonCampDurabilityFatal);
        adjudication.WinnerPlayerId.Should().BeNull();

        steps.Should().Equal(
            "campaign_started",
            "defeat_settlement",
            CampFailSettlementRouter.EndReasonCampDurabilityFatal);
    }

    // ACC:T150.2
    [Fact]
    [Trait("acceptance", "ACC:T150.2")]
    public void ShouldKeepRouteUnchanged_WhenCampDurabilityIsNotFatal()
    {
        var router = new CampFailSettlementRouter();
        var routeState = SettlementRouteState.InProgress();

        var routeResult = router.Route(routeState, campDurability: 2, currentTick: 91);
        var adjudication = CampaignEndgameAdjudicator.EvaluateCampFailureDefeat(isCampDurabilityFatal: false);

        routeResult.NextScreen.Should().Be(CampFailSettlementRouter.InProgressScreen);
        routeResult.EndReason.Should().BeNull();
        routeResult.NextState.Should().Be(routeState);
        routeResult.DeadlockDetected.Should().BeFalse();

        adjudication.ShouldEndGame.Should().BeFalse();
        adjudication.EndReason.Should().BeNull();
        adjudication.WinnerPlayerId.Should().BeNull();
    }

    // ACC:T150.3
    [Fact]
    [Trait("acceptance", "ACC:T150.3")]
    public void ShouldKeepTerminalDefeatState_WhenCampaignFlowReentersRouterAfterFatalOutcome()
    {
        const int tick90 = 90;
        const int tick91 = 91;
        const int tick92 = 92;
        const int tick93 = 93;
        var router = new CampFailSettlementRouter();
        var startState = SettlementRouteState.InProgress();

        startState.CurrentScreen.Should().Be(CampFailSettlementRouter.InProgressScreen);
        startState.LastProcessedTick.Should().Be(-1);

        var firstTurn = router.Route(startState, campDurability: 2, currentTick: tick90);
        var secondTurn = router.Route(firstTurn.NextState, campDurability: 1, currentTick: tick91);
        var fatalTurn = router.Route(secondTurn.NextState, campDurability: 0, currentTick: tick92);
        var postFatalTurn = router.Route(fatalTurn.NextState, campDurability: 5, currentTick: tick93);

        var adjudication = CampaignEndgameAdjudicator.EvaluateCampFailureDefeat(
            isCampDurabilityFatal: fatalTurn.EndReason == CampFailSettlementRouter.EndReasonCampDurabilityFatal);

        firstTurn.NextScreen.Should().Be(CampFailSettlementRouter.InProgressScreen);
        secondTurn.NextScreen.Should().Be(CampFailSettlementRouter.InProgressScreen);
        fatalTurn.NextScreen.Should().Be(CampFailSettlementRouter.DefeatSettlementScreen);
        fatalTurn.NextState.LastProcessedTick.Should().Be(tick92);
        postFatalTurn.NextScreen.Should().Be(CampFailSettlementRouter.DefeatSettlementScreen);
        postFatalTurn.NextState.CurrentScreen.Should().Be(CampFailSettlementRouter.DefeatSettlementScreen);

        adjudication.ShouldEndGame.Should().BeTrue();
        adjudication.WinnerPlayerId.Should().BeNull();
    }
}
