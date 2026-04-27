namespace Game.Godot.Scripts.UI;

public interface IHudEventHandlers
{
    void HandleGameStarted(HudGameStartedDto dto);
    void HandleScore(HudScoreDto dto);
    void HandleHealth(HudHealthDto dto);
    void HandleTurn(HudTurnDto dto);
    void HandlePlayerStateChanged(HudPlayerStateDto dto);
    void HandleDiceRolled(HudDiceRolledDto dto);
    void HandleCityTollPaid(HudCityTollPaidDto dto);
    void HandleCityBought(HudCityBoughtDto dto);
    void HandleTokenMoved(HudTokenMovedDto dto);
    void HandleBossChallengePrompted(HudBossChallengePromptedDto dto);
    void HandleObjectiveSkipped(HudObjectiveSkippedDto dto);
    void HandleGameEnded();
    void HandleUiOnly();
}
