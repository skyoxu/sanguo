using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task51MultiplierCompositionTests
{
    // ACC:T51.1
    [Fact]
    public void AppliedMultipliers_ShouldBeConstructible()
    {
        var m = new AppliedMultipliers(
            1.0m,
            1.0m,
            1.0m,
            1.0m,
            1.0m);

        m.Effective.Should().Be(1.0m);
    }
}
