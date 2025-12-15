using System;
using FluentAssertions;
using Game.Core.Domain;
using Xunit;

namespace Game.Core.Tests.Domain;

public class CityTests
{
    [Fact]
    public void City_Construct_SetsProperties()
    {
        var city = new City(id: "c1", name: "CityName", regionId: "r1", basePrice: 100m, baseToll: 10m);

        city.Id.Should().Be("c1");
        city.Name.Should().Be("CityName");
        city.RegionId.Should().Be("r1");
        city.BasePrice.Should().Be(100m);
        city.BaseToll.Should().Be(10m);
    }

    [Fact]
    public void City_Construct_WithNegativeBasePrice_ShouldThrowArgumentOutOfRangeException()
    {
        var act = () => new City("c1", "CityName", "r1", basePrice: -1m, baseToll: 10m);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void City_Construct_WithNegativeBaseToll_ShouldThrowArgumentOutOfRangeException()
    {
        var act = () => new City("c1", "CityName", "r1", basePrice: 100m, baseToll: -1m);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void City_GetPrice_WithZeroMultiplier_ReturnsZero()
    {
        var city = new City("c1", "CityName", "r1", basePrice: 100m, baseToll: 10m);

        city.GetPrice(multiplier: 0m).Should().Be(0m);
    }

    [Fact]
    public void City_GetPrice_WithMultiplier_ReturnsScaledPrice()
    {
        var city = new City("c1", "CityName", "r1", basePrice: 100m, baseToll: 10m);

        city.GetPrice(multiplier: 1.5m).Should().Be(150m);
    }

    [Fact]
    public void City_GetPrice_WithNegativeMultiplier_ShouldThrowArgumentOutOfRangeException()
    {
        var city = new City("c1", "CityName", "r1", basePrice: 100m, baseToll: 10m);

        var act = () => city.GetPrice(multiplier: -1m);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void City_GetPrice_WithDecimalPrecisionMultiplier_ShouldReturnExpectedValue()
    {
        var city = new City("c1", "CityName", "r1", basePrice: 100m, baseToll: 10m);

        city.GetPrice(multiplier: 0.333m).Should().Be(33.3m);
    }

    [Fact]
    public void City_GetPrice_WithMaxValueMultiplier_ShouldThrowOverflowException()
    {
        var city = new City("c1", "CityName", "r1", basePrice: 100m, baseToll: 10m);

        var act = () => city.GetPrice(multiplier: decimal.MaxValue);

        act.Should().Throw<OverflowException>();
    }

    [Fact]
    public void City_GetPrice_CalledMultipleTimes_ShouldReturnConsistentResult()
    {
        var city = new City("c1", "CityName", "r1", basePrice: 100m, baseToll: 10m);

        var first = city.GetPrice(multiplier: 1.5m);
        var second = city.GetPrice(multiplier: 1.5m);
        var third = city.GetPrice(multiplier: 1.5m);

        second.Should().Be(first);
        third.Should().Be(first);
    }

    [Fact]
    public void City_GetToll_WithZeroMultiplier_ReturnsZero()
    {
        var city = new City("c1", "CityName", "r1", basePrice: 100m, baseToll: 10m);

        city.GetToll(multiplier: 0m).Should().Be(0m);
    }

    [Fact]
    public void City_GetToll_WithMultiplier_ReturnsScaledToll()
    {
        var city = new City("c1", "CityName", "r1", basePrice: 100m, baseToll: 10m);

        city.GetToll(multiplier: 2m).Should().Be(20m);
    }

    [Fact]
    public void City_GetToll_WithNegativeMultiplier_ShouldThrowArgumentOutOfRangeException()
    {
        var city = new City("c1", "CityName", "r1", basePrice: 100m, baseToll: 10m);

        var act = () => city.GetToll(multiplier: -1m);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void City_GetToll_WithMaxValueMultiplier_ShouldThrowOverflowException()
    {
        var city = new City("c1", "CityName", "r1", basePrice: 100m, baseToll: 10m);

        var act = () => city.GetToll(multiplier: decimal.MaxValue);

        act.Should().Throw<OverflowException>();
    }
}
