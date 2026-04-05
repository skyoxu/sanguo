using System;
using System.Collections.Generic;
using Game.Core.Contracts.Sanguo;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// T86 split scope policy:
/// keep campaign endgame adjudication deterministic and independent.
/// </summary>
public static class CampaignEndgameAdjudicator
{
    public const string SplitScopeR3 = "R3-EndgameAdjudicator";

    public static readonly IReadOnlyList<string> OwnedEventTypes = new[]
    {
        SanguoGameEnded.EventType,
        SanguoPlayerEliminated.EventType,
    };

    public static CampaignEndgameAdjudicationOutcome EvaluateHumanElimination(
        IReadOnlyList<string>? playerOrder,
        Func<string, bool> isAiPlayerId,
        Func<string, bool> isPlayerEliminated)
    {
        if (playerOrder is null || playerOrder.Count == 0)
        {
            return CampaignEndgameAdjudicationOutcome.None();
        }

        foreach (var playerId in playerOrder)
        {
            if (isAiPlayerId(playerId))
            {
                continue;
            }

            if (!isPlayerEliminated(playerId))
            {
                continue;
            }

            return new CampaignEndgameAdjudicationOutcome(
                ShouldEndGame: true,
                EndReason: SanguoGameEnded.ReasonPlayerBankrupt,
                WinnerPlayerId: null,
                SplitScope: SplitScopeR3);
        }

        return CampaignEndgameAdjudicationOutcome.None();
    }

    public static CampaignEndgameAdjudicationOutcome EvaluatePostPrune(
        int startingPlayersCount,
        IReadOnlyList<string>? remainingPlayerOrder)
    {
        if (remainingPlayerOrder is null || remainingPlayerOrder.Count == 0)
        {
            return new CampaignEndgameAdjudicationOutcome(
                ShouldEndGame: true,
                EndReason: SanguoGameEnded.ReasonNoPlayers,
                WinnerPlayerId: null,
                SplitScope: SplitScopeR3);
        }

        if (startingPlayersCount >= 2 && remainingPlayerOrder.Count == 1)
        {
            return new CampaignEndgameAdjudicationOutcome(
                ShouldEndGame: true,
                EndReason: SanguoGameEnded.ReasonLastActorStanding,
                WinnerPlayerId: remainingPlayerOrder[0],
                SplitScope: SplitScopeR3);
        }

        return CampaignEndgameAdjudicationOutcome.None();
    }
}

public sealed record CampaignEndgameAdjudicationOutcome(
    bool ShouldEndGame,
    string? EndReason,
    string? WinnerPlayerId,
    string SplitScope)
{
    public static CampaignEndgameAdjudicationOutcome None()
    {
        return new CampaignEndgameAdjudicationOutcome(
            ShouldEndGame: false,
            EndReason: null,
            WinnerPlayerId: null,
            SplitScope: CampaignEndgameAdjudicator.SplitScopeR3);
    }
}
