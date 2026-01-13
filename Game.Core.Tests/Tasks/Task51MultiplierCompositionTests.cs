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
        AppliedMultipliers.MinMultiplier.Should().Be(0.5m);
        AppliedMultipliers.MaxMultiplier.Should().Be(3.0m);
        AppliedMultipliers.Step.Should().Be(0.5m);

        AppliedMultipliers.ClampToRange(0.0m).Should().Be(0.5m);
        AppliedMultipliers.ClampToRange(0.5m).Should().Be(0.5m);
        AppliedMultipliers.ClampToRange(3.0m).Should().Be(3.0m);
        AppliedMultipliers.ClampToRange(10.0m).Should().Be(3.0m);

        AppliedMultipliers.IsHalfStep(0.5m).Should().BeTrue();
        AppliedMultipliers.IsHalfStep(1.0m).Should().BeTrue();
        AppliedMultipliers.IsHalfStep(1.5m).Should().BeTrue();
        AppliedMultipliers.IsHalfStep(1.25m).Should().BeFalse();

        var placeholder = new AppliedMultipliers(1.0m, 1.0m, 1.0m, 1.0m, 1.0m);
        placeholder.Sources.Should().Be(AppliedMultiplierSources.None);
    }
}
