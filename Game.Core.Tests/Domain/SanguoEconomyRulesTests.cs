using System;
using FluentAssertions;
using Game.Core.Domain;
using Xunit;

namespace Game.Core.Tests.Domain;

public class SanguoEconomyRulesTests
{
    [Fact]
    public void Default_HasExpectedBounds()
    {
        var rules = SanguoEconomyRules.Default;
        rules.MaxPriceSteps.Should().Be(SanguoEconomyRules.DefaultMaxPriceSteps);
        rules.MaxTollSteps.Should().Be(SanguoEconomyRules.DefaultMaxTollSteps);
        rules.MinMultiplier.Should().Be(0.5m);
        rules.MaxPriceMultiplier.Should().Be(3.0m);
    }

    [Fact]
    public void Constructor_WhenMaxPriceStepsOutOfRange_ThrowsArgumentOutOfRangeException()
    {
        Action act = () => _ = new SanguoEconomyRules(maxPriceSteps: 0, maxTollSteps: 6);
        act.Should().Throw<ArgumentOutOfRangeException>().WithParameterName("maxPriceSteps");
    }

    [Fact]
    public void Constructor_WhenMaxTollStepsOutOfRange_ThrowsArgumentOutOfRangeException()
    {
        Action act = () => _ = new SanguoEconomyRules(maxPriceSteps: 6, maxTollSteps: 7);
        act.Should().Throw<ArgumentOutOfRangeException>().WithParameterName("maxTollSteps");
    }
}

