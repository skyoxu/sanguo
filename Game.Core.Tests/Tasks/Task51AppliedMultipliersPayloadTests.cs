using System;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using System.Text.Json;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task51AppliedMultipliersPayloadTests
{
    // ACC:T51.2
    [Fact]
    public void ShouldExposeAppliedMultipliersField_WhenUsingEconomyEventContracts()
    {
        var m = new AppliedMultipliers(
            BaseSteps: 2,
            CharacterStepDelta: 0,
            BuildingStepDelta: 0,
            EventStepDelta: 0,
            ActionCardStepDelta: 0,
            RelicStepDelta: 0,
            RegionStepDelta: 0,
            EffectiveSteps: 2);

        var evt = new SanguoCityBought(
            "g1",
            1,
            "p1",
            "c1",
            50m,
            DateTimeOffset.UtcNow,
            "corr-1",
            null,
            m);

        evt.AppliedMultipliers.Should().NotBeNull();
        evt.AppliedMultipliers!.EffectiveMultiplier.Should().Be(1.0m);
    }

    // ACC:T51.4
    [Fact]
    public void ShouldRoundTripAppliedMultipliers_WhenSerializedWithSystemTextJson()
    {
        var m = new AppliedMultipliers(
            BaseSteps: 2,
            CharacterStepDelta: 1,
            BuildingStepDelta: 0,
            EventStepDelta: 0,
            ActionCardStepDelta: 0,
            RelicStepDelta: 0,
            RegionStepDelta: 0,
            EffectiveSteps: 3);

        var evt = new SanguoCityBought(
            "g1",
            1,
            "p1",
            "c1",
            50m,
            DateTimeOffset.UtcNow,
            "corr-1",
            null,
            m);

        var json = JsonSerializer.Serialize(evt);
        var restored = JsonSerializer.Deserialize<SanguoCityBought>(json);

        restored.Should().NotBeNull();
        restored!.AppliedMultipliers.Should().NotBeNull();
        restored.AppliedMultipliers!.EffectiveMultiplier.Should().Be(1.5m);
    }
}
