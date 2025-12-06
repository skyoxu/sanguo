using System;
using Game.Core.Domain.ValueObjects;
using Xunit;

namespace Game.Core.Tests.Domain.ValueObjects;

public class HealthTests
{
    [Fact]
    public void Constructor_sets_current_equals_max_and_disallows_negative()
    {
        var h = new Health(100);
        Assert.Equal(100, h.Maximum);
        Assert.Equal(100, h.Current);
        Assert.True(h.IsAlive);
    }

    [Fact]
    public void TakeDamage_clamps_at_zero_and_is_immutable()
    {
        var h = new Health(10);
        var h2 = h.TakeDamage(3);
        Assert.Equal(10, h.Current);
        Assert.Equal(7, h2.Current);

        var h3 = h2.TakeDamage(100);
        Assert.Equal(0, h3.Current);
        Assert.False(h3.IsAlive);
    }

    [Fact]
    public void TakeDamage_negative_throws()
    {
        var h = new Health(10);
        Assert.Throws<ArgumentOutOfRangeException>(() => h.TakeDamage(-1));
    }
}
