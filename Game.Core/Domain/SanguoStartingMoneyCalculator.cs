using Game.Core.Contracts.Sanguo;

namespace Game.Core.Domain;

public static class SanguoStartingMoneyCalculator
{
    public static decimal ComputeStartingMoney(int preset, int startingMoneyStepDelta)
    {
        var steps = AppliedMultipliers.ClampSteps(AppliedMultipliers.BaseDefaultSteps + startingMoneyStepDelta);
        var multiplier = steps * AppliedMultipliers.Step;
        return preset * multiplier;
    }
}

