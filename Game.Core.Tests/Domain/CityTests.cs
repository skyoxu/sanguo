using System;
using FluentAssertions;
using Game.Core.Domain;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;
using Xunit;
namespace Game.Core.Tests.Domain;
public class CityTests
{
    private static readonly SanguoEconomyRules Rules = SanguoEconomyRules.Default;

    // ACC:T3.1
    [Fact]
    public void ShouldNotReferenceGodotAssemblies_WhenUsingCityDomain()
    {
        var referenced = typeof(City).Assembly.GetReferencedAssemblies();
        referenced.Should().NotContain(a => a.Name != null && a.Name.StartsWith("Godot", StringComparison.OrdinalIgnoreCase));
    }

    // ACC:T3.2
    [Fact]
    public void ShouldSetProperties_WhenConstructed()
    {
        var city = new City(
            id: "c1",
            name: "CityName",
            regionId: "r1",
            basePrice: MoneyValue.FromDecimal(100m),
            baseToll: MoneyValue.FromDecimal(10m),
            positionIndex: 7);
        city.Id.Should().Be("c1");
        city.Name.Should().Be("CityName");
        city.RegionId.Should().Be("r1");
        city.BasePrice.Should().Be(MoneyValue.FromDecimal(100m));
        city.BaseToll.Should().Be(MoneyValue.FromDecimal(10m));
        city.PositionIndex.Should().Be(7);
    }

    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenPositionIndexIsNegative()
    {
        var act = () => _ = new City(
            id: "c1",
            name: "CityName",
            regionId: "r1",
            basePrice: MoneyValue.FromDecimal(100m),
            baseToll: MoneyValue.FromDecimal(10m),
            positionIndex: -1);

        act.Should().Throw<ArgumentOutOfRangeException>()
            .WithParameterName("positionIndex");
    }
    // ACC:T3.3
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenPriceMultiplierIsBelowMin()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));
        var act = () => city.GetPrice(multiplier: 0m, rules: Rules);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }
    [Fact]
    public void ShouldReturnScaledPrice_WhenPriceMultiplierIsProvided()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));
        city.GetPrice(multiplier: 1.5m, rules: Rules).Should().Be(MoneyValue.FromDecimal(150m));
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenPriceMultiplierIsNegative()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));
        var act = () => city.GetPrice(multiplier: -1m, rules: Rules);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenPriceMultiplierIsNotHalfStep()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));
        var act = () => city.GetPrice(multiplier: 1.25m, rules: Rules);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenPriceMultiplierExceedsMax()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));
        var act = () => city.GetPrice(multiplier: Rules.MaxPriceMultiplier + 1m, rules: Rules);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void ShouldUseRulesParameter_WhenValidatingPriceMultiplierRange()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));
        var customRules = new SanguoEconomyRules(maxPriceSteps: 2, maxTollSteps: Rules.MaxTollSteps);
        var act = () => city.GetPrice(multiplier: 1.2m, rules: customRules);
        act.Should().Throw<ArgumentOutOfRangeException>()
            .WithParameterName("multiplier");
    }
    [Fact]
    public void ShouldReturnConsistentResult_WhenGettingPriceMultipleTimes()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));
        var first = city.GetPrice(multiplier: 1.5m, rules: Rules);
        var second = city.GetPrice(multiplier: 1.5m, rules: Rules);
        var third = city.GetPrice(multiplier: 1.5m, rules: Rules);
        second.Should().Be(first);
        third.Should().Be(first);
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenTollMultiplierIsBelowMin()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));
        var act = () => city.GetToll(multiplier: 0m, rules: Rules);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }
    [Fact]
    public void ShouldReturnScaledToll_WhenTollMultiplierIsProvided()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));
        city.GetToll(multiplier: 2m, rules: Rules).Should().Be(MoneyValue.FromDecimal(20m));
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenTollMultiplierIsNegative()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));
        var act = () => city.GetToll(multiplier: -1m, rules: Rules);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenTollMultiplierExceedsMax()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));
        var act = () => city.GetToll(multiplier: Rules.MaxTollMultiplier + 1m, rules: Rules);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    // ACC:T3.4
    [Fact]
    public void ShouldUseRulesParameter_WhenValidatingTollMultiplierRange()
    {
        var city = new City("c1", "CityName", "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m));
        var customRules = new SanguoEconomyRules(maxPriceSteps: Rules.MaxPriceSteps, maxTollSteps: 2);

        city.GetToll(multiplier: 1.0m, rules: customRules).Should().Be(MoneyValue.FromDecimal(10m));

        var act = () => city.GetToll(multiplier: 1.2m, rules: customRules);
        act.Should().Throw<ArgumentOutOfRangeException>()
            .WithParameterName("multiplier");
    }

    [Fact]
    public void ShouldThrowArgumentException_WhenIdIsEmpty()
    {
        var act = () => _ = new City(
            id: "",
            name: "CityName",
            regionId: "r1",
            basePrice: MoneyValue.FromDecimal(1m),
            baseToll: MoneyValue.FromDecimal(1m),
            positionIndex: 0);

        act.Should().Throw<ArgumentException>()
            .WithParameterName("id");
    }

    [Fact]
    public void ShouldThrowArgumentException_WhenNameIsEmpty()
    {
        var act = () => _ = new City(
            id: "c1",
            name: "",
            regionId: "r1",
            basePrice: MoneyValue.FromDecimal(1m),
            baseToll: MoneyValue.FromDecimal(1m),
            positionIndex: 0);

        act.Should().Throw<ArgumentException>()
            .WithParameterName("name");
    }

    [Fact]
    public void ShouldThrowArgumentException_WhenRegionIdIsEmpty()
    {
        var act = () => _ = new City(
            id: "c1",
            name: "CityName",
            regionId: "",
            basePrice: MoneyValue.FromDecimal(1m),
            baseToll: MoneyValue.FromDecimal(1m),
            positionIndex: 0);

        act.Should().Throw<ArgumentException>()
            .WithParameterName("regionId");
    }


}
