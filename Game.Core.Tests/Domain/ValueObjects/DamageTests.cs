using Game.Core.Domain.ValueObjects;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Domain.ValueObjects;

public class DamageTests
{
    [Fact]
    public void EffectiveAmountIsNeverNegative()
    {
        // Arrange
        var d1 = new Damage(-10, DamageType.Physical);
        var d2 = new Damage(0, DamageType.Fire);
        var d3 = new Damage(5, DamageType.Ice, IsCritical: true);

        // Act
        var e1 = d1.EffectiveAmount;
        var e2 = d2.EffectiveAmount;
        var e3 = d3.EffectiveAmount;

        // Assert
        e1.Should().Be(0);
        e2.Should().Be(0);
        e3.Should().Be(5);
        d3.IsCritical.Should().BeTrue();
    }

    [Theory]
    [InlineData(-10, 0)]
    [InlineData(0, 0)]
    [InlineData(5, 5)]
    public void EffectiveAmountClampsNegativeAndKeepsPositive(int rawAmount, int expected)
    {
        // Arrange
        var damage = new Damage(rawAmount, DamageType.Physical);

        // Act
        var effective = damage.EffectiveAmount;

        // Assert
        effective.Should().Be(expected);
    }
}
