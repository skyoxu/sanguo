using System;
using Game.Core.Contracts.Sanguo;

namespace Game.Core.Services.Sanguo;

public static class SanguoCombatResolver
{
    public static SanguoCombatResult ResolvePveCombat(
        SanguoCombatStatsDefinition playerStats,
        int combatRating,
        int encounterTarget,
        int seed)
    {
        ValidatePlayerStats(playerStats);

        var effectiveCombatRating = ResolveAttributeCombatRating(playerStats);
        return ResolvePveCombat(effectiveCombatRating, encounterTarget, seed);
    }

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

    private static int ResolveAttributeCombatRating(SanguoCombatStatsDefinition playerStats)
    {
        var currentHpRatio = playerStats.MaxHP == 0 ? 0m : (decimal)playerStats.CurrentHP / playerStats.MaxHP;
        var hpContribution = (int)Math.Floor(currentHpRatio * 2m);
        var critContribution = (int)Math.Floor(playerStats.CritRate * playerStats.CritMultiplier * 2m);
        var speedContribution = playerStats.AttackSpeed <= 0m ? 0 : (int)Math.Floor(2m / playerStats.AttackSpeed);
        var mitigationContribution = (int)Math.Floor((playerStats.DamageReductionRate + playerStats.DodgeRate + playerStats.ReflectRate) * 2m);
        var sustainContribution = (int)Math.Floor(playerStats.LifeStealRate * 2m);
        var aoeContribution = playerStats.AoEEnabled ? 1 : 0;

        return Math.Max(0, playerStats.Attack + hpContribution + critContribution + speedContribution + mitigationContribution + sustainContribution + aoeContribution);
    }

    private static void ValidatePlayerStats(SanguoCombatStatsDefinition playerStats)
    {
        if (playerStats.MaxHP <= 0)
            throw InvalidStats();

        if (playerStats.CurrentHP < 0 || playerStats.CurrentHP > playerStats.MaxHP)
            throw InvalidStats();

        if (playerStats.Attack < 0)
            throw InvalidStats();

        if (playerStats.CritMultiplier < 1m || playerStats.AttackSpeed <= 0m)
            throw InvalidStats();

        ValidateRate(playerStats.CritRate);
        ValidateRate(playerStats.LifeStealRate);
        ValidateRate(playerStats.DodgeRate);
        ValidateRate(playerStats.DamageReductionRate);
        ValidateRate(playerStats.ReflectRate);
    }

    private static void ValidateRate(decimal value)
    {
        if (value is < 0m or > 1m)
            throw InvalidStats();
    }

    private static ArgumentOutOfRangeException InvalidStats()
        => new("playerStats", "Combat stats are outside the supported v4 bounds.");
}
