using FluentAssertions;
using Game.Core.Domain;
using Xunit;

namespace Game.Core.Tests.Domain;

public sealed class MvgEconomyMutationProbeTests
{
    [Fact]
    public void MinimumHalfStepPriceMultiplierIsAccepted()
    {
        var rules = SanguoEconomyRules.Default;
        rules.IsValidPriceMultiplier(rules.MinMultiplier).Should().BeTrue();
    }

    [Fact]
    public void MaximumPriceMultiplierIsAccepted()
    {
        var rules = SanguoEconomyRules.Default;
        rules.IsValidPriceMultiplier(rules.MaxPriceMultiplier).Should().BeTrue();
    }

    [Fact]
    public void OffGridPriceMultiplierIsRejected()
    {
        var rules = SanguoEconomyRules.Default;
        rules.IsValidPriceMultiplier(1.25m).Should().BeFalse();
    }
}
