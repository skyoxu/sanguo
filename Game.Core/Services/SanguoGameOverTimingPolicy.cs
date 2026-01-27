using System;

namespace Game.Core.Services;

public static class SanguoGameOverTimingPolicy
{
    public static string GetGameOverCheckPhaseForElimination(string actorKind)
    {
        ArgumentNullException.ThrowIfNull(actorKind, nameof(actorKind));
        return actorKind.Trim() switch
        {
            "Player" => "Immediate",
            "Human" => "Immediate",
            "HumanPlayer" => "Immediate",
            "Ai" => "AfterTurnAdvanced",
            "AI" => "AfterTurnAdvanced",
            _ => "AfterTurnAdvanced",
        };
    }
}

