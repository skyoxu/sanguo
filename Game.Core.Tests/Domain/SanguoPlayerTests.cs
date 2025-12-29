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
    private static readonly SanguoEconomyRules Rules = SanguoEconomyRules.Default;
    private static City MakeCity(string id = "c1", decimal? basePrice = null, decimal? baseToll = null, string? name = null)
        => new(
            id: id,
            name: name ?? DefaultCityName,
            regionId: DefaultRegionId,
            basePrice: MoneyValue.FromDecimal(basePrice ?? DefaultCityBasePrice),
            baseToll: MoneyValue.FromDecimal(baseToll ?? DefaultCityBaseToll));

    // ACC:T4.1
    [Fact]
    public void ShouldNotReferenceGodotAssemblies_WhenUsingSanguoPlayerDomain()
    {
        var referenced = typeof(SanguoPlayer).Assembly.GetReferencedAssemblies();
        referenced.Should().NotContain(a => a.Name != null && a.Name.StartsWith("Godot", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void ShouldInitializeMoneyPositionAndOwnedCities_WhenConstructed()
    {
        var player = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0, economyRules: Rules);
        player.PlayerId.Should().Be("p1");
        player.Money.Should().Be(MoneyValue.FromDecimal(200m));
        player.PositionIndex.Should().Be(0);
        player.OwnedCityIds.Should().BeEmpty();
    }
    [Fact]
    public void ShouldThrow_WhenConstructedWithInvalidInputs()
    {
        var emptyId = () => new SanguoPlayer(playerId: " ", money: 0m, positionIndex: 0, economyRules: Rules);
        var negativeMoney = () => new SanguoPlayer(playerId: "p1", money: -1m, positionIndex: 0, economyRules: Rules);
        var negativePosition = () => new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: -1, economyRules: Rules);
        emptyId.Should().Throw<ArgumentException>();
        negativeMoney.Should().Throw<ArgumentOutOfRangeException>();
        negativePosition.Should().Throw<ArgumentOutOfRangeException>();
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenConstructedWithMoneyAboveMax()
    {
        var aboveMax = (decimal)MoneyValue.MaxMajorUnits + 1m;
        var act = () => new SanguoPlayer(playerId: "p1", money: aboveMax, positionIndex: 0, economyRules: Rules);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }
    [Fact]
    public void ShouldDeductMoneyAndAddCity_WhenBuyingCityWithEnoughMoney()
    {
        var city = MakeCity(id: "c1");
        var initialMoney = DefaultCityBasePrice + 50m;
        var player = new SanguoPlayer(playerId: "p1", money: initialMoney, positionIndex: 0, economyRules: Rules);
        var bought = player.TryBuyCity(city, priceMultiplier: UnitMultiplier);
        bought.Should().BeTrue();
        player.Money.Should().Be(MoneyValue.FromDecimal(initialMoney - DefaultCityBasePrice));
        player.OwnedCityIds.Should().Contain("c1");
    }
    [Fact]
    public void ShouldReturnFalseAndNotChangeState_WhenBuyingCityWithoutEnoughMoney()
    {
        var city = MakeCity(id: "c1");
        var player = new SanguoPlayer(playerId: "p1", money: 50m, positionIndex: 0, economyRules: Rules);
        var bought = player.TryBuyCity(city, priceMultiplier: UnitMultiplier);
        bought.Should().BeFalse();
        player.Money.Should().Be(MoneyValue.FromDecimal(50m));
        player.OwnedCityIds.Should().BeEmpty();
    }
    [Fact]
    public void ShouldReturnFalse_WhenBuyingCityAlreadyOwned()
    {
        var city = MakeCity(id: "c1");
        var player = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: Rules);
        player.TryBuyCity(city, priceMultiplier: UnitMultiplier).Should().BeTrue();
        var moneyAfterFirstBuy = player.Money;
        player.TryBuyCity(city, priceMultiplier: UnitMultiplier).Should().BeFalse();
        player.Money.Should().Be(moneyAfterFirstBuy);
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenBuyingCityWithNegativePriceMultiplier()
    {
        var city = MakeCity(id: "c1");
        var player = new SanguoPlayer(playerId: "p1", money: 150m, positionIndex: 0, economyRules: Rules);
        var act = () => player.TryBuyCity(city, priceMultiplier: -1m);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenBuyingCityWithTooLargePriceMultiplier()
    {
        var rules = new SanguoEconomyRules(
            maxPriceMultiplier: 2m,
            maxTollMultiplier: SanguoEconomyRules.DefaultMaxTollMultiplier);
        var city = MakeCity(id: "c1", basePrice: 10m);
        var player = new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0, economyRules: rules);
        var act = () => player.TryBuyCity(city, priceMultiplier: 3m);
        act.Should().Throw<ArgumentOutOfRangeException>().WithParameterName("priceMultiplier");
    }
    [Fact]
    public void ShouldTransferMoney_WhenPayingTollToDifferentOwner()
    {
        var city = MakeCity(id: "c1");
        var initialMoney = 100m;
        var payer = new SanguoPlayer(playerId: "payer", money: initialMoney, positionIndex: 0, economyRules: Rules);
        var owner = new SanguoPlayer(playerId: "owner", money: 0m, positionIndex: 0, economyRules: Rules);
        var treasury = new SanguoTreasury();
        payer.TryPayTollTo(owner, city, tollMultiplier: UnitMultiplier, treasury: treasury).Should().BeTrue();
        payer.Money.Should().Be(MoneyValue.FromDecimal(initialMoney - DefaultCityBaseToll));
        owner.Money.Should().Be(MoneyValue.FromDecimal(DefaultCityBaseToll));
        treasury.MinorUnits.Should().Be(0);
    }
    [Fact]
    public void ShouldReturnFalseAndNotChangeMoney_WhenPayingTollToSelf()
    {
        var city = MakeCity(id: "c1");
        var player = new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0, economyRules: Rules);
        var treasury = new SanguoTreasury();
        player.TryPayTollTo(player, city, tollMultiplier: UnitMultiplier, treasury: treasury).Should().BeFalse();
        player.Money.Should().Be(MoneyValue.FromDecimal(100m));
        treasury.MinorUnits.Should().Be(0);
    }
    // ACC:T4.2
    [Fact]
    public void ShouldTransferRemainingMoneyAndEliminateAndReleaseCities_WhenPayingTollWithoutEnoughMoney()
    {
        var owned1 = MakeCity(id: "owned1", name: "Owned1", baseToll: 1m);
        var owned2 = MakeCity(id: "owned2", name: "Owned2", baseToll: 1m);
        var tollCity = MakeCity(id: "toll", name: "TollCity", baseToll: DefaultCityBaseToll);
        var remaining = 5m;
        var payerInitialMoney = (DefaultCityBasePrice * 2) + remaining;
        var payer = new SanguoPlayer(playerId: "payer", money: payerInitialMoney, positionIndex: 0, economyRules: Rules);
        var owner = new SanguoPlayer(playerId: "owner", money: 0m, positionIndex: 0, economyRules: Rules);
        var treasury = new SanguoTreasury();
        payer.TryBuyCity(owned1, priceMultiplier: UnitMultiplier).Should().BeTrue();
        payer.TryBuyCity(owned2, priceMultiplier: UnitMultiplier).Should().BeTrue();
        payer.Money.Should().Be(MoneyValue.FromDecimal(remaining));
        payer.OwnedCityIds.Should().HaveCount(2);
        payer.TryPayTollTo(owner, tollCity, tollMultiplier: UnitMultiplier, treasury: treasury).Should().BeTrue();
        payer.Money.Should().Be(MoneyValue.Zero);
        owner.Money.Should().Be(MoneyValue.FromDecimal(remaining));
        treasury.MinorUnits.Should().Be(0);
        payer.IsEliminated.Should().BeTrue();
        payer.OwnedCityIds.Should().BeEmpty();
        payer.TryBuyCity(owned1, priceMultiplier: UnitMultiplier).Should().BeFalse();
    }
    [Fact]
    public void ShouldReturnFalse_WhenEliminatedPayerAttemptsToPayToll()
    {
        var tollCity = MakeCity(id: "toll", name: "TollCity", baseToll: DefaultCityBaseToll);
        var payer = new SanguoPlayer(playerId: "payer", money: 0m, positionIndex: 0, economyRules: Rules);
        var owner = new SanguoPlayer(playerId: "owner", money: 0m, positionIndex: 0, economyRules: Rules);
        var treasury = new SanguoTreasury();
        payer.TryPayTollTo(owner, tollCity, tollMultiplier: UnitMultiplier, treasury: treasury).Should().BeTrue();
        payer.IsEliminated.Should().BeTrue();
        var ownerMoneyBefore = owner.Money;
        payer.TryPayTollTo(owner, tollCity, tollMultiplier: UnitMultiplier, treasury: treasury).Should().BeFalse();
        payer.Money.Should().Be(MoneyValue.Zero);
        payer.OwnedCityIds.Should().BeEmpty();
        owner.Money.Should().Be(ownerMoneyBefore);
        treasury.MinorUnits.Should().Be(0);
    }
    [Fact]
    public void ShouldReturnFalse_WhenPayingTollToEliminatedOwner()
    {
        var tollCity = MakeCity(id: "toll", name: "TollCity", baseToll: DefaultCityBaseToll);
        var creditor = new SanguoPlayer(playerId: "creditor", money: 0m, positionIndex: 0, economyRules: Rules);
        var owner = new SanguoPlayer(playerId: "owner", money: 0m, positionIndex: 0, economyRules: Rules);
        var treasury = new SanguoTreasury();
        owner.TryPayTollTo(creditor, tollCity, tollMultiplier: UnitMultiplier, treasury: treasury).Should().BeTrue();
        owner.IsEliminated.Should().BeTrue();
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0, economyRules: Rules);
        var payerMoneyBefore = payer.Money;
        var ownerMoneyBefore = owner.Money;
        payer.TryPayTollTo(owner, tollCity, tollMultiplier: UnitMultiplier, treasury: treasury).Should().BeFalse();
        payer.Money.Should().Be(payerMoneyBefore);
        owner.Money.Should().Be(ownerMoneyBefore);
        treasury.MinorUnits.Should().Be(0);
    }
    [Fact]
    public void ShouldCapCreditorAndDepositOverflowToTreasury_WhenCreditorWouldExceedMaxMoney()
    {
        var city = MakeCity(id: "c1", baseToll: 10m);
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0, economyRules: Rules);
        var owner = new SanguoPlayer(playerId: "owner", money: (decimal)MoneyValue.MaxMajorUnits - 5m, positionIndex: 0, economyRules: Rules);
        var treasury = new SanguoTreasury();
        payer.TryPayTollTo(owner, city, tollMultiplier: UnitMultiplier, treasury: treasury).Should().BeTrue();
        payer.Money.Should().Be(MoneyValue.FromDecimal(90m));
        owner.Money.Should().Be(MoneyValue.FromMajorUnits(MoneyValue.MaxMajorUnits));
        treasury.MinorUnits.Should().Be(MoneyValue.FromDecimal(5m).MinorUnits);
    }
    [Fact]
    public async Task ShouldThrowInvalidOperationException_WhenCalledFromDifferentThread()
    {
        var city = MakeCity(id: "c1");
        var player = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0, economyRules: Rules);
        Func<Task> act = async () => await Task.Run(() => player.TryBuyCity(city, priceMultiplier: UnitMultiplier));
        await act.Should().ThrowAsync<InvalidOperationException>();
    }
    [Fact]
    public void ShouldThrowArgumentNullException_WhenPayingTollWithNullOwner()
    {
        var city = MakeCity(id: "c1");
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0, economyRules: Rules);
        var treasury = new SanguoTreasury();
        var act = () => payer.TryPayTollTo(owner: null!, city: city, tollMultiplier: UnitMultiplier, treasury: treasury);
        act.Should().Throw<ArgumentNullException>();
    }
    [Fact]
    public void ShouldThrowArgumentNullException_WhenPayingTollWithNullCity()
    {
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0, economyRules: Rules);
        var owner = new SanguoPlayer(playerId: "owner", money: 0m, positionIndex: 0, economyRules: Rules);
        var treasury = new SanguoTreasury();
        var act = () => payer.TryPayTollTo(owner: owner, city: null!, tollMultiplier: UnitMultiplier, treasury: treasury);
        act.Should().Throw<ArgumentNullException>();
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenPayingTollWithNegativeMultiplier()
    {
        var city = MakeCity(id: "c1");
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0, economyRules: Rules);
        var owner = new SanguoPlayer(playerId: "owner", money: 0m, positionIndex: 0, economyRules: Rules);
        var treasury = new SanguoTreasury();
        var act = () => payer.TryPayTollTo(owner, city, tollMultiplier: -1m, treasury: treasury);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenPayingTollWithTooLargeMultiplier()
    {
        var rules = new SanguoEconomyRules(
            maxPriceMultiplier: SanguoEconomyRules.DefaultMaxPriceMultiplier,
            maxTollMultiplier: 2m);
        var city = MakeCity(id: "c1", baseToll: 10m);
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0, economyRules: rules);
        var owner = new SanguoPlayer(playerId: "owner", money: 0m, positionIndex: 0, economyRules: rules);
        var treasury = new SanguoTreasury();
        var act = () => payer.TryPayTollTo(owner, city, tollMultiplier: 3m, treasury: treasury);
        act.Should().Throw<ArgumentOutOfRangeException>().WithParameterName("tollMultiplier");
    }
    [Fact]
    public void ShouldReturnImmutableSnapshotForUiAndAi_WhenConvertingToView()
    {
        var city1 = MakeCity(id: "c1");
        var city2 = MakeCity(id: "c2");
        var player = new SanguoPlayer(playerId: "p1", money: 500m, positionIndex: 3, economyRules: Rules);
        player.TryBuyCity(city1, priceMultiplier: UnitMultiplier).Should().BeTrue();
        var view = player.ToView();
        player.TryBuyCity(city2, priceMultiplier: UnitMultiplier).Should().BeTrue();
        view.PlayerId.Should().Be("p1");
        view.PositionIndex.Should().Be(3);
        view.IsEliminated.Should().BeFalse();
        view.OwnedCityIds.Should().ContainSingle().Which.Should().Be("c1");
    }
}
