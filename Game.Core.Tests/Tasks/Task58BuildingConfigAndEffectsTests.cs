using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task58BuildingConfigAndEffectsTests
{
    // ACC:T58.1
    [Fact]
    public void BuildingDefinition_ShouldOnlyUseMultiplierStepDelta()
    {
        var b = new SanguoBuildingDefinition(
            "b_house_1",
            "民宅",
            "desc",
            1);

        b.MultiplierStepDelta.Should().Be(1);
    }
}
