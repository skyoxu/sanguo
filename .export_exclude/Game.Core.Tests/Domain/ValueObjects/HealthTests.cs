using FluentAssertions;
using Game.Core.Domain.ValueObjects;
using Xunit;

namespace Game.Core.Tests.Domain.ValueObjects;

public class HealthTests
{
    [Fact]
    public void Constructor_SetsMaximumAndCurrent()
    {
        var health = new Health(100);
        health.Current.Should().Be(100);
        health.Maximum.Should().Be(100);
        health.IsAlive.Should().BeTrue();
    }

    [Fact]
    public void TakeDamage_ShouldReduceCurrent()
    {
        var health = new Health(100);
        var newHealth = health.TakeDamage(30);
        newHealth.Current.Should().Be(70);
        newHealth.IsAlive.Should().BeTrue();
    }

    [Fact]
    public void TakeDamage_ExceedingCurrent_ShouldClampToZero()
    {
        var health = new Health(100);
        var newHealth = health.TakeDamage(150);
        newHealth.Current.Should().Be(0);
        newHealth.IsAlive.Should().BeFalse();
    }

    [Fact]
    public void TakeDamage_ShouldNotModifyOriginal()
    {
        var original = new Health(100);
        var modified = original.TakeDamage(30);
        original.Current.Should().Be(100);
        modified.Current.Should().Be(70);
    }
}

