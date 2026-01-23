using FluentAssertions;
using Game.Core.Utilities;
using System;
using Xunit;

namespace Game.Core.Tests.Utilities;

public sealed class DeterministicRandomNumberGeneratorTests
{
    [Fact]
    public void NextInt_ShouldThrow_WhenRangeInvalid()
    {
        var rng = new DeterministicRandomNumberGenerator(seed: 1);
        rng.Invoking(r => r.NextInt(5, 5)).Should().Throw<ArgumentOutOfRangeException>();
        rng.Invoking(r => r.NextInt(6, 5)).Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void NextInt_ShouldReturnMin_WhenRangeIsSingleValue()
    {
        var rng = new DeterministicRandomNumberGenerator(seed: 1);
        rng.NextInt(3, 4).Should().Be(3);
    }

    [Fact]
    public void NextDouble_ShouldStayWithinUnitInterval()
    {
        var rng = new DeterministicRandomNumberGenerator(seed: 42);
        for (var i = 0; i < 100; i++)
        {
            var v = rng.NextDouble();
            v.Should().BeGreaterOrEqualTo(0.0);
            v.Should().BeLessThan(1.0);
        }
    }

    [Fact]
    public void WithSameSeed_ShouldProduceSameSequence()
    {
        var a = new DeterministicRandomNumberGenerator(seed: 123);
        var b = new DeterministicRandomNumberGenerator(seed: 123);

        for (var i = 0; i < 50; i++)
        {
            a.NextInt(0, 1000).Should().Be(b.NextInt(0, 1000));
            a.NextDouble().Should().Be(b.NextDouble());
        }
    }
}
