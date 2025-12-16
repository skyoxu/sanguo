using System;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Domain;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;
using Xunit;

namespace Game.Core.Tests.Domain;

public class SanguoPlayerTests
{
    private const string DefaultRegionId = "r1";
    private const string DefaultCityName = "CityName";
    private const decimal DefaultCityBasePrice = 100m;
    private const decimal DefaultCityBaseToll = 10m;
    private const decimal UnitMultiplier = 1m;

    private static City MakeCity(string id = "c1", decimal? basePrice = null, decimal? baseToll = null, string? name = null)
        => new(
            id: id,
            name: name ?? DefaultCityName,
            regionId: DefaultRegionId,
            basePrice: MoneyValue.FromDecimal(basePrice ?? DefaultCityBasePrice),
            baseToll: MoneyValue.FromDecimal(baseToll ?? DefaultCityBaseToll));

    [Fact]
    public void SanguoPlayer_Construct_InitializesMoneyPositionAndOwnedCities()
    {
        var player = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0);

        player.PlayerId.Should().Be("p1");
        player.Money.Should().Be(MoneyValue.FromDecimal(200m));
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
    public void SanguoPlayer_Construct_WithMoneyAboveMax_ShouldThrowArgumentOutOfRangeException()
    {
        var aboveMax = (decimal)MoneyValue.MaxMajorUnits + 1m;
        var act = () => new SanguoPlayer(playerId: "p1", money: aboveMax, positionIndex: 0);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void SanguoPlayer_TryBuyCity_WhenEnoughMoney_ShouldDeductMoneyAndAddCity()
    {
        var city = MakeCity(id: "c1");
        var initialMoney = DefaultCityBasePrice + 50m;
        var player = new SanguoPlayer(playerId: "p1", money: initialMoney, positionIndex: 0);

        var bought = player.TryBuyCity(city, priceMultiplier: UnitMultiplier);

        bought.Should().BeTrue();
        player.Money.Should().Be(MoneyValue.FromDecimal(initialMoney - DefaultCityBasePrice));
        player.OwnedCityIds.Should().Contain("c1");
    }

    [Fact]
    public void SanguoPlayer_TryBuyCity_WhenNotEnoughMoney_ShouldReturnFalseAndNotChangeState()
    {
        var city = MakeCity(id: "c1");
        var player = new SanguoPlayer(playerId: "p1", money: 50m, positionIndex: 0);

        var bought = player.TryBuyCity(city, priceMultiplier: UnitMultiplier);

        bought.Should().BeFalse();
        player.Money.Should().Be(MoneyValue.FromDecimal(50m));
        player.OwnedCityIds.Should().BeEmpty();
    }

    [Fact]
    public void SanguoPlayer_TryBuyCity_WhenCityAlreadyOwned_ShouldReturnFalse()
    {
        var city = MakeCity(id: "c1");
        var player = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0);

        player.TryBuyCity(city, priceMultiplier: UnitMultiplier).Should().BeTrue();
        var moneyAfterFirstBuy = player.Money;

        player.TryBuyCity(city, priceMultiplier: UnitMultiplier).Should().BeFalse();
        player.Money.Should().Be(moneyAfterFirstBuy);
    }

    [Fact]
    public void SanguoPlayer_TryBuyCity_WithNegativeMultiplier_ShouldThrowArgumentOutOfRangeException()
    {
        var city = MakeCity(id: "c1");
        var player = new SanguoPlayer(playerId: "p1", money: 150m, positionIndex: 0);

        var act = () => player.TryBuyCity(city, priceMultiplier: -1m);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void SanguoPlayer_TryPayTollTo_WhenOwnerIsDifferent_ShouldTransferMoney()
    {
        var city = MakeCity(id: "c1");
        var initialMoney = 100m;
        var payer = new SanguoPlayer(playerId: "payer", money: initialMoney, positionIndex: 0);
        var owner = new SanguoPlayer(playerId: "owner", money: 0m, positionIndex: 0);

        payer.TryPayTollTo(owner, city, tollMultiplier: UnitMultiplier, out var overflow).Should().BeTrue();

        payer.Money.Should().Be(MoneyValue.FromDecimal(initialMoney - DefaultCityBaseToll));
        owner.Money.Should().Be(MoneyValue.FromDecimal(DefaultCityBaseToll));
        overflow.Should().Be(MoneyValue.Zero);
    }

    [Fact]
    public void SanguoPlayer_TryPayTollTo_WhenOwnerIsSelf_ReturnsFalseAndDoesNotChangeMoney()
    {
        var city = MakeCity(id: "c1");
        var player = new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0);

        player.TryPayTollTo(player, city, tollMultiplier: UnitMultiplier, out _).Should().BeFalse();

        player.Money.Should().Be(MoneyValue.FromDecimal(100m));
    }

    [Fact]
    public void SanguoPlayer_TryPayTollTo_WhenInsufficientFunds_TransfersRemainingMoney_EliminatesAndReleasesCities()
    {
        var owned1 = MakeCity(id: "owned1", name: "Owned1", baseToll: 1m);
        var owned2 = MakeCity(id: "owned2", name: "Owned2", baseToll: 1m);
        var tollCity = MakeCity(id: "toll", name: "TollCity", baseToll: DefaultCityBaseToll);
        var remaining = 5m;
        var payerInitialMoney = (DefaultCityBasePrice * 2) + remaining;
        var payer = new SanguoPlayer(playerId: "payer", money: payerInitialMoney, positionIndex: 0);
        var owner = new SanguoPlayer(playerId: "owner", money: 0m, positionIndex: 0);

        payer.TryBuyCity(owned1, priceMultiplier: UnitMultiplier).Should().BeTrue();
        payer.TryBuyCity(owned2, priceMultiplier: UnitMultiplier).Should().BeTrue();
        payer.Money.Should().Be(MoneyValue.FromDecimal(remaining));
        payer.OwnedCityIds.Should().HaveCount(2);

        payer.TryPayTollTo(owner, tollCity, tollMultiplier: UnitMultiplier, out var overflow).Should().BeTrue();

        payer.Money.Should().Be(MoneyValue.Zero);
        owner.Money.Should().Be(MoneyValue.FromDecimal(remaining));
        overflow.Should().Be(MoneyValue.Zero);
        payer.IsEliminated.Should().BeTrue();
        payer.OwnedCityIds.Should().BeEmpty();

        payer.TryBuyCity(owned1, priceMultiplier: UnitMultiplier).Should().BeFalse();
    }

    [Fact]
    public void SanguoPlayer_TryPayTollTo_WhenCreditorWouldExceedMax_ShouldCapCreditorAndReturnOverflowToTreasury()
    {
        var city = MakeCity(id: "c1", baseToll: 10m);
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0);
        var owner = new SanguoPlayer(playerId: "owner", money: (decimal)MoneyValue.MaxMajorUnits - 5m, positionIndex: 0);

        payer.TryPayTollTo(owner, city, tollMultiplier: UnitMultiplier, out var overflowToTreasury).Should().BeTrue();

        payer.Money.Should().Be(MoneyValue.FromDecimal(90m));
        owner.Money.Should().Be(MoneyValue.FromMajorUnits(MoneyValue.MaxMajorUnits));
        overflowToTreasury.Should().Be(MoneyValue.FromDecimal(5m));
    }

    [Fact]
    public async Task SanguoPlayer_CalledFromDifferentThread_ShouldThrowInvalidOperationException()
    {
        var city = MakeCity(id: "c1");
        var player = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0);

        Func<Task> act = async () => await Task.Run(() => player.TryBuyCity(city, priceMultiplier: UnitMultiplier));

        await act.Should().ThrowAsync<InvalidOperationException>();
    }

    [Fact]
    public void SanguoPlayer_TryPayTollTo_WithNegativeMultiplier_ShouldThrowArgumentOutOfRangeException()
    {
        var city = MakeCity(id: "c1");
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0);
        var owner = new SanguoPlayer(playerId: "owner", money: 0m, positionIndex: 0);

        var act = () => payer.TryPayTollTo(owner, city, tollMultiplier: -1m, out _);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }
}
