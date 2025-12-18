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
        rules.MaxPriceMultiplier.Should().Be(SanguoEconomyRules.DefaultMaxPriceMultiplier);
        rules.MaxTollMultiplier.Should().Be(SanguoEconomyRules.DefaultMaxTollMultiplier);
    }

    [Fact]
    public void Constructor_WhenMaxPriceMultiplierNegative_ThrowsArgumentOutOfRangeException()
    {
        Action act = () => _ = new SanguoEconomyRules(maxPriceMultiplier: -1m, maxTollMultiplier: 1m);
        act.Should().Throw<ArgumentOutOfRangeException>().WithParameterName("maxPriceMultiplier");
    }

    [Fact]
    public void Constructor_WhenMaxTollMultiplierNegative_ThrowsArgumentOutOfRangeException()
    {
        Action act = () => _ = new SanguoEconomyRules(maxPriceMultiplier: 1m, maxTollMultiplier: -1m);
        act.Should().Throw<ArgumentOutOfRangeException>().WithParameterName("maxTollMultiplier");
    }
}

