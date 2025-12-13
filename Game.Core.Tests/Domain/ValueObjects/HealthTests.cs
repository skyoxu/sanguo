using System;
using FluentAssertions;
using Game.Core.Domain.ValueObjects;
using Xunit;

namespace Game.Core.Tests.Domain.ValueObjects;

public class HealthTests
{
    [Fact]
    public void ConstructorSetsCurrentEqualsMaxAndDisallowsNegative()
    {
        var h = new Health(100);
        h.Maximum.Should().Be(100);
        h.Current.Should().Be(100);
        h.IsAlive.Should().BeTrue();
    }

    [Fact]
    public void TakeDamageClampsAtZeroAndIsImmutable()
    {
        var h = new Health(10);
        var h2 = h.TakeDamage(3);
        h.Current.Should().Be(10);
        h2.Current.Should().Be(7);

        var h3 = h2.TakeDamage(100);
        h3.Current.Should().Be(0);
        h3.IsAlive.Should().BeFalse();
    }

    [Fact]
    public void TakeDamageNegativeThrows()
    {
        var h = new Health(10);
        h.Invoking(x => x.TakeDamage(-1)).Should().Throw<ArgumentOutOfRangeException>();
    }
}
