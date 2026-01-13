using System;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
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
}
