using System;
using System.Collections.Generic;

namespace Game.Core.Services;

public static class SanguoTurnDecisionPoints
{
    public static IReadOnlyList<string> GetDecisionPointSequence(string actorKind)
    {
        ArgumentNullException.ThrowIfNull(actorKind, nameof(actorKind));

        // For Task 61 the AI follows the same decision points as the player.
        // Keep the sequence stable and deterministic.
        return new[] { "BeforeRoll", "ResolveLanding", "Discard" };
    }
}

