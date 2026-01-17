using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task51AppliedMultipliersSerializationTests
{
    // ACC:T51.3
    [Fact]
    public void AppliedMultipliers_ShouldRoundTrip_WithSystemTextJson()
    {
        var m = new AppliedMultipliers(
            BaseSteps: 2,
            CharacterStepDelta: 1,
            BuildingStepDelta: 0,
            EventStepDelta: -1,
            ActionCardStepDelta: 0,
            RelicStepDelta: 0,
            RegionStepDelta: 0,
            EffectiveSteps: 2,
            Sources: AppliedMultiplierSources.Character | AppliedMultiplierSources.ActionCard);

        var json = JsonSerializer.Serialize(m);
        var restored = JsonSerializer.Deserialize<AppliedMultipliers>(json);

        restored.Should().NotBeNull();
        restored!.BaseSteps.Should().Be(2);
        restored.CharacterStepDelta.Should().Be(1);
        restored.EventStepDelta.Should().Be(-1);
        restored.EffectiveSteps.Should().Be(2);
        restored.Sources.Should().Be(AppliedMultiplierSources.Character | AppliedMultiplierSources.ActionCard);
    }
}
