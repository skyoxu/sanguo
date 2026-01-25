using System;
using Game.Core.Contracts.Sanguo;

namespace Game.Core.Services.Sanguo;

public static class SanguoCombatResolver
{
    public static SanguoCombatResult ResolvePveCombat(int combatRating, int encounterTarget, int seed)
    {
        if (combatRating < 0)
            throw new ArgumentOutOfRangeException(nameof(combatRating), "Combat rating must be non-negative.");

        if (encounterTarget < 0)
            throw new ArgumentOutOfRangeException(nameof(encounterTarget), "Encounter target must be non-negative.");

        var outcome = combatRating >= encounterTarget ? "win" : "lose";

        if (outcome == "lose")
            return new SanguoCombatResult(outcome, MoneyDelta: 0m, EncounterTarget: encounterTarget, EffectiveCombatRating: combatRating);

        var rng = new Random(seed);
        var reward = 40m + rng.Next(0, 21); // 40..60
        return new SanguoCombatResult(outcome, MoneyDelta: reward, EncounterTarget: encounterTarget, EffectiveCombatRating: combatRating);
    }
}

