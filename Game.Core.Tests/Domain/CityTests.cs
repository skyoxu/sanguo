using System;
using FluentAssertions;
using Game.Core.Domain;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;
using Xunit;

namespace Game.Core.Tests.Domain;

public class CityTests
{
    private static readonly SanguoEconomyRules Rules = SanguoEconomyRules.Default;

    [Fact]
    public void City_Construct_SetsProperties()
    {
        var city = new City(
            id: "c1",
            name: "CityName",
            regionId: "r1",
            basePrice: MoneyValue.FromDecimal(100m),
            baseToll: MoneyValue.FromDecimal(10m));

        city.Id.Should().Be("c1");
        city.Name.Should().Be("CityName");
        city.RegionId.Should().Be("r1");
        city.BasePrice.Should().Be(MoneyValue.FromDecimal(100m));
        city.BaseToll.Should().Be(MoneyValue.FromDecimal(10m));
    }

    [Fact]
    public void City_GetPrice_WithZeroMultiplier_ReturnsZero()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));

        city.GetPrice(multiplier: 0m, rules: Rules).Should().Be(MoneyValue.Zero);
    }

    [Fact]
    public void City_GetPrice_WithMultiplier_ReturnsScaledPrice()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));

        city.GetPrice(multiplier: 1.5m, rules: Rules).Should().Be(MoneyValue.FromDecimal(150m));
    }

    [Fact]
    public void City_GetPrice_WithNegativeMultiplier_ShouldThrowArgumentOutOfRangeException()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));

        var act = () => city.GetPrice(multiplier: -1m, rules: Rules);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void City_GetPrice_WithDecimalPrecisionMultiplier_ShouldReturnExpectedValue()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));

        city.GetPrice(multiplier: 0.333m, rules: Rules).Should().Be(MoneyValue.FromDecimal(33.3m));
    }

    [Fact]
    public void City_GetPrice_WithMultiplierAboveMax_ShouldThrowArgumentOutOfRangeException()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));

        var act = () => city.GetPrice(multiplier: Rules.MaxPriceMultiplier + 1m, rules: Rules);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void City_GetPrice_CalledMultipleTimes_ShouldReturnConsistentResult()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));

        var first = city.GetPrice(multiplier: 1.5m, rules: Rules);
        var second = city.GetPrice(multiplier: 1.5m, rules: Rules);
        var third = city.GetPrice(multiplier: 1.5m, rules: Rules);

        second.Should().Be(first);
        third.Should().Be(first);
    }

    [Fact]
    public void City_GetToll_WithZeroMultiplier_ReturnsZero()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));

        city.GetToll(multiplier: 0m, rules: Rules).Should().Be(MoneyValue.Zero);
    }

    [Fact]
    public void City_GetToll_WithMultiplier_ReturnsScaledToll()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));

        city.GetToll(multiplier: 2m, rules: Rules).Should().Be(MoneyValue.FromDecimal(20m));
    }

    [Fact]
    public void City_GetToll_WithNegativeMultiplier_ShouldThrowArgumentOutOfRangeException()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));

        var act = () => city.GetToll(multiplier: -1m, rules: Rules);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void City_GetToll_WithMultiplierAboveMax_ShouldThrowArgumentOutOfRangeException()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));

        var act = () => city.GetToll(multiplier: Rules.MaxTollMultiplier + 1m, rules: Rules);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }
}
