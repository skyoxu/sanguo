// Acceptance anchors:
// ACC:T17.14
// ACC:T17.3
using System;
using System.Globalization;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Domain.ValueObjects;
using Xunit;
namespace Game.Core.Tests.Domain;
public class MoneyTests
{
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenFromDecimalIsNegative()
    {
        var act = () => Money.FromDecimal(-0.01m);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenFromDecimalExceedsMax()
    {
        var aboveMax = (decimal)Money.MaxMajorUnits + 1m;
        var act = () => Money.FromDecimal(aboveMax);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }
    [Fact]
    public void ShouldThrowOverflowException_WhenAddingWouldExceedMax()
    {
        var max = Money.FromMajorUnits(Money.MaxMajorUnits);
        var one = Money.FromMajorUnits(1);
        var act = () => _ = max + one;
        act.Should().Throw<OverflowException>();
    }
    [Fact]
    public void ShouldReturnMaxAndOverflow_WhenAddCappedWouldExceedMax()
    {
        var baseValue = Money.FromMajorUnits(Money.MaxMajorUnits - 5);
        var add = Money.FromMajorUnits(10);
        var capped = baseValue.AddCapped(add, out var overflow);
        capped.Should().Be(Money.FromMajorUnits(Money.MaxMajorUnits));
        overflow.Should().Be(Money.FromMajorUnits(5));
    }
    [Fact]
    public void ShouldThrowInvalidOperationException_WhenSubtractWouldBecomeNegative()
    {
        var a = Money.FromMajorUnits(1);
        var b = Money.FromMajorUnits(2);
        var act = () => _ = a - b;
        act.Should().Throw<InvalidOperationException>();
    }
    [Fact]
    public void ShouldThrowJsonException_WhenJsonDeserializeAboveMax()
    {
        var json = ((decimal)Money.MaxMajorUnits + 1m).ToString(CultureInfo.InvariantCulture);
        var act = () => JsonSerializer.Deserialize<Money>(json);
        act.Should().Throw<JsonException>();
    }
    [Fact]
    public void ShouldPreserveValue_WhenJsonRoundTrip()
    {
        var value = Money.FromDecimal(123.45m);
        var json = JsonSerializer.Serialize(value);
        var roundTrip = JsonSerializer.Deserialize<Money>(json);
        roundTrip.Should().Be(value);
    }
    [Fact]
    public void ShouldWork_WhenJsonDeserializeWithStringNumber()
    {
        var json = "\"123.45\"";
        var value = JsonSerializer.Deserialize<Money>(json);
        value.Should().Be(Money.FromDecimal(123.45m));
    }
    [Fact]
    public void ShouldThrowJsonException_WhenJsonDeserializeWithEmptyString()
    {
        var act = () => JsonSerializer.Deserialize<Money>("\"\"");
        act.Should().Throw<JsonException>();
    }

    [Fact]
    public void ShouldThrowJsonException_WhenJsonDeserializeWithInvalidString()
    {
        var act = () => JsonSerializer.Deserialize<Money>("\"not-a-number\"");
        act.Should().Throw<JsonException>();
    }
}
