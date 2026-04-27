using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;

namespace Game.Godot.Scripts.UI;

public static class HudEventHandlerRegistry
{
    public static void RegisterAll(HudEventHandlersController controller, IHudEventHandlers handlers)
    {
        if (controller == null || handlers == null)
        {
            return;
        }

        controller.Register(SanguoGameStarted.EventType, root =>
        {
            if (HudEventDtoMapper.TryParseGameStarted(root, out var dto))
            {
                handlers.HandleGameStarted(dto);
            }
        });

        controller.Register(CoreGameEvents.ScoreUpdated, root =>
        {
            if (HudEventDtoMapper.TryParseScore(root, out var dto))
            {
                handlers.HandleScore(dto);
            }
        });
        controller.Register(CoreGameEvents.ScoreChanged, root =>
        {
            if (HudEventDtoMapper.TryParseScore(root, out var dto))
            {
                handlers.HandleScore(dto);
            }
        });

        controller.Register(CoreGameEvents.HealthUpdated, root =>
        {
            if (HudEventDtoMapper.TryParseHealth(root, out var dto))
            {
                handlers.HandleHealth(dto);
            }
        });
        controller.Register(CoreGameEvents.PlayerHealthChanged, root =>
        {
            if (HudEventDtoMapper.TryParseHealth(root, out var dto))
            {
                handlers.HandleHealth(dto);
            }
        });

        controller.Register(SanguoGameTurnStarted.EventType, root =>
        {
            if (HudEventDtoMapper.TryParseTurn(root, out var dto))
            {
                handlers.HandleTurn(dto);
            }
        });
        controller.Register(SanguoGameTurnAdvanced.EventType, root =>
        {
            if (HudEventDtoMapper.TryParseTurn(root, out var dto))
            {
                handlers.HandleTurn(dto);
            }
        });
        controller.Register(SanguoGameTurnEnded.EventType, _ => handlers.HandleUiOnly());

        controller.Register(SanguoPlayerStateChanged.EventType, root =>
        {
            if (HudEventDtoMapper.TryParsePlayerStateChanged(root, out var dto))
            {
                handlers.HandlePlayerStateChanged(dto);
            }
        });
        controller.Register(SanguoDiceRolled.EventType, root =>
        {
            if (HudEventDtoMapper.TryParseDiceRolled(root, out var dto))
            {
                handlers.HandleDiceRolled(dto);
            }
        });
        controller.Register(SanguoCityTollPaid.EventType, root =>
        {
            if (HudEventDtoMapper.TryParseCityTollPaid(root, out var dto))
            {
                handlers.HandleCityTollPaid(dto);
            }
        });
        controller.Register(SanguoCityBought.EventType, root =>
        {
            if (HudEventDtoMapper.TryParseCityBought(root, out var dto))
            {
                handlers.HandleCityBought(dto);
            }
        });

        controller.Register(SanguoCityOwnerChanged.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoAiDecisionMade.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoActionCardPlayed.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoCombatStarted.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoCombatEnded.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoPlayerEliminated.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoGameSaved.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoGameLoaded.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoTokenMoved.EventType, root =>
        {
            if (HudEventDtoMapper.TryParseTokenMoved(root, out var dto))
            {
                handlers.HandleTokenMoved(dto);
            }
        });
        controller.Register(SanguoMonthSettled.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoSeasonEventApplied.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoYearPriceAdjusted.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoLootGranted.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoRelicApplied.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoCardLost.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoRegionCaptured.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoRegionLost.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoRandomEventApplied.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoCityTollSynergyPaid.EventType, _ => handlers.HandleUiOnly());
        controller.Register(SanguoBossChallengePrompted.EventType, root =>
        {
            if (HudEventDtoMapper.TryParseBossChallengePrompted(root, out var dto))
            {
                handlers.HandleBossChallengePrompted(dto);
            }
            else
            {
                handlers.HandleUiOnly();
            }
        });
        controller.Register(SanguoObjectiveSkipped.EventType, root =>
        {
            if (HudEventDtoMapper.TryParseObjectiveSkipped(root, out var dto))
            {
                handlers.HandleObjectiveSkipped(dto);
            }
            else
            {
                handlers.HandleUiOnly();
            }
        });
        controller.Register(SanguoGameEnded.EventType, _ => handlers.HandleGameEnded());
    }
}
