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
    public void EconomyEvents_ShouldExposeAppliedMultipliersField()
    {
        var m = new AppliedMultipliers(1.0m, 1.0m, 1.0m, 1.0m, 1.0m);

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
        evt.AppliedMultipliers!.Effective.Should().Be(1.0m);
    }

    // ACC:T51.4
    [Fact]
    public void EconomyEvent_WithAppliedMultipliers_ShouldRoundTrip_WithSystemTextJson()
    {
        var m = new AppliedMultipliers(1.5m, 1.0m, 0.5m, 1.0m, 0.75m);

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
        restored.AppliedMultipliers!.Effective.Should().Be(0.75m);
    }
}
