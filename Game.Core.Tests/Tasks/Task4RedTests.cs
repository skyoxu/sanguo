using System;
using FluentAssertions;
using Game.Core.Domain;
using Xunit;

namespace Game.Core.Tests.Tasks;

public class Task4RedTests
{
    [Fact]
    public void SanguoPlayer_Construct_InitializesMoneyPositionAndOwnedCities()
    {
        var player = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0);

        player.PlayerId.Should().Be("p1");
        player.Money.Should().Be(200m);
        player.PositionIndex.Should().Be(0);
        player.OwnedCityIds.Should().BeEmpty();
    }

    [Fact]
    public void SanguoPlayer_Construct_WithInvalidInputs_ShouldThrow()
    {
        var emptyId = () => new SanguoPlayer(playerId: " ", money: 0m, positionIndex: 0);
        var negativeMoney = () => new SanguoPlayer(playerId: "p1", money: -1m, positionIndex: 0);
        var negativePosition = () => new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: -1);

        emptyId.Should().Throw<ArgumentException>();
        negativeMoney.Should().Throw<ArgumentOutOfRangeException>();
        negativePosition.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void SanguoPlayer_TryBuyCity_WhenEnoughMoney_ShouldDeductMoneyAndAddCity()
    {
        var city = new City(id: "c1", name: "CityName", regionId: "r1", basePrice: 100m, baseToll: 10m);
        var player = new SanguoPlayer(playerId: "p1", money: 150m, positionIndex: 0);

        var bought = player.TryBuyCity(city, priceMultiplier: 1m);

        bought.Should().BeTrue();
        player.Money.Should().Be(50m);
        player.OwnedCityIds.Should().Contain("c1");
    }

    [Fact]
    public void SanguoPlayer_TryBuyCity_WhenNotEnoughMoney_ShouldReturnFalseAndNotChangeState()
    {
        var city = new City(id: "c1", name: "CityName", regionId: "r1", basePrice: 100m, baseToll: 10m);
        var player = new SanguoPlayer(playerId: "p1", money: 50m, positionIndex: 0);

        var bought = player.TryBuyCity(city, priceMultiplier: 1m);

        bought.Should().BeFalse();
        player.Money.Should().Be(50m);
        player.OwnedCityIds.Should().BeEmpty();
    }

    [Fact]
    public void SanguoPlayer_TryBuyCity_WhenCityAlreadyOwned_ShouldReturnFalse()
    {
        var city = new City(id: "c1", name: "CityName", regionId: "r1", basePrice: 100m, baseToll: 10m);
        var player = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0);

        player.TryBuyCity(city, priceMultiplier: 1m).Should().BeTrue();
        var moneyAfterFirstBuy = player.Money;

        player.TryBuyCity(city, priceMultiplier: 1m).Should().BeFalse();
        player.Money.Should().Be(moneyAfterFirstBuy);
    }

    [Fact]
    public void SanguoPlayer_TryBuyCity_WithNegativeMultiplier_ShouldThrowArgumentOutOfRangeException()
    {
        var city = new City(id: "c1", name: "CityName", regionId: "r1", basePrice: 100m, baseToll: 10m);
        var player = new SanguoPlayer(playerId: "p1", money: 150m, positionIndex: 0);

        var act = () => player.TryBuyCity(city, priceMultiplier: -1m);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void SanguoPlayer_PayTollTo_WhenOwnerIsDifferent_ShouldTransferMoney()
    {
        var city = new City(id: "c1", name: "CityName", regionId: "r1", basePrice: 100m, baseToll: 10m);
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0);
        var owner = new SanguoPlayer(playerId: "owner", money: 0m, positionIndex: 0);

        payer.PayTollTo(owner, city, tollMultiplier: 1m);

        payer.Money.Should().Be(90m);
        owner.Money.Should().Be(10m);
    }

    [Fact]
    public void SanguoPlayer_PayTollTo_WhenOwnerIsSelf_ShouldNotChangeMoney()
    {
        var city = new City(id: "c1", name: "CityName", regionId: "r1", basePrice: 100m, baseToll: 10m);
        var player = new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0);

        player.PayTollTo(player, city, tollMultiplier: 1m);

        player.Money.Should().Be(100m);
    }

    [Fact]
    public void SanguoPlayer_PayTollTo_WithNegativeMultiplier_ShouldThrowArgumentOutOfRangeException()
    {
        var city = new City(id: "c1", name: "CityName", regionId: "r1", basePrice: 100m, baseToll: 10m);
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0);
        var owner = new SanguoPlayer(playerId: "owner", money: 0m, positionIndex: 0);

        var act = () => payer.PayTollTo(owner, city, tollMultiplier: -1m);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }
}
