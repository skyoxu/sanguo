using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task51MultiplierCompositionTests
{
    // ACC:T51.1
    [Fact]
    public void AppliedMultipliers_Rules_ShouldBeStable()
    {
        AppliedMultipliers.Step.Should().Be(0.5m);
        AppliedMultipliers.BaseDefaultSteps.Should().Be(2);
        AppliedMultipliers.MinSteps.Should().Be(1);
        AppliedMultipliers.MaxSteps.Should().Be(6);

        AppliedMultipliers.ClampSteps(0).Should().Be(1);
        AppliedMultipliers.ClampSteps(1).Should().Be(1);
        AppliedMultipliers.ClampSteps(6).Should().Be(6);
        AppliedMultipliers.ClampSteps(999).Should().Be(6);

        AppliedMultipliers.IsHalfStepMultiplier(0.5m).Should().BeTrue();
        AppliedMultipliers.IsHalfStepMultiplier(1.0m).Should().BeTrue();
        AppliedMultipliers.IsHalfStepMultiplier(1.5m).Should().BeTrue();
        AppliedMultipliers.IsHalfStepMultiplier(1.25m).Should().BeFalse();

        var placeholder = new AppliedMultipliers(
            BaseSteps: 2,
            CharacterStepDelta: 0,
            BuildingStepDelta: 0,
            EventStepDelta: 0,
            ActionCardStepDelta: 0,
            RelicStepDelta: 0,
            RegionStepDelta: 0,
            EffectiveSteps: 2);
        placeholder.Sources.Should().Be(AppliedMultiplierSources.None);
        placeholder.EffectiveMultiplier.Should().Be(1.0m);
    }
}
