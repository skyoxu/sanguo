using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task55CharacterMultipliersAppliedTests
{
    // ACC:T55.3
    [Fact]
    public void ShouldComputeEffectiveMultiplier_WhenUsingAppliedMultipliersSteps()
    {
        var multipliers = new AppliedMultipliers(
            BaseSteps: AppliedMultipliers.BaseDefaultSteps,
            CharacterStepDelta: 1,
            BuildingStepDelta: 0,
            EventStepDelta: 0,
            ActionCardStepDelta: 0,
            RelicStepDelta: 0,
            RegionStepDelta: 0,
            EffectiveSteps: AppliedMultipliers.ClampSteps(AppliedMultipliers.BaseDefaultSteps + 1),
            Sources: AppliedMultiplierSources.Character);

        multipliers.EffectiveSteps.Should().Be(3);
        multipliers.EffectiveMultiplier.Should().Be(1.5m);
    }
}
