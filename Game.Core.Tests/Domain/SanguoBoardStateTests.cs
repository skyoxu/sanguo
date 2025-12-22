using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Domain;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;
using Xunit;

namespace Game.Core.Tests.Domain;

public sealed class SanguoBoardStateTests
{
    private const decimal UnitMultiplier = 1m;
    private static readonly SanguoEconomyRules Rules = SanguoEconomyRules.Default;

    private static City MakeCity(string id = "c1", decimal basePrice = 100m, decimal baseToll = 10m)
        => new(
            id: id,
            name: "CityName",
            regionId: "r1",
            basePrice: MoneyValue.FromDecimal(basePrice),
            baseToll: MoneyValue.FromDecimal(baseToll));

    [Fact]
    public void TryBuyCity_WhenCityOwnedByAnotherPlayer_ReturnsFalseAndDoesNotChangeBuyerState()
    {
        var city = MakeCity(id: "c1");
        var owner = new SanguoPlayer(playerId: "owner", money: 200m, positionIndex: 0, economyRules: Rules);
        var buyer = new SanguoPlayer(playerId: "buyer", money: 200m, positionIndex: 0, economyRules: Rules);

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { city.Id, city } };
        var state = new SanguoBoardState(players: new[] { owner, buyer }, citiesById: citiesById);

        state.TryBuyCity(buyerId: owner.PlayerId, cityId: city.Id, priceMultiplier: UnitMultiplier).Should().BeTrue();

        var buyerMoneyBefore = buyer.Money;
        buyer.OwnedCityIds.Should().NotContain(city.Id);

        state.TryBuyCity(buyerId: buyer.PlayerId, cityId: city.Id, priceMultiplier: UnitMultiplier).Should().BeFalse();

        buyer.Money.Should().Be(buyerMoneyBefore);
        buyer.OwnedCityIds.Should().NotContain(city.Id);
    }

    [Fact]
    public void ShouldReturnFalse_WhenBuyerNotFound()
    {
        var city = MakeCity(id: "c1");
        var owner = new SanguoPlayer(playerId: "owner", money: 200m, positionIndex: 0, economyRules: Rules);

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { city.Id, city } };
        var state = new SanguoBoardState(players: new[] { owner }, citiesById: citiesById);

        state.TryBuyCity(buyerId: "missing", cityId: city.Id, priceMultiplier: UnitMultiplier).Should().BeFalse();
        owner.OwnedCityIds.Should().BeEmpty();
    }

    [Fact]
    public void ShouldReturnFalse_WhenCityNotFound()
    {
        var owner = new SanguoPlayer(playerId: "owner", money: 200m, positionIndex: 0, economyRules: Rules);
        var state = new SanguoBoardState(
            players: new[] { owner },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        state.TryBuyCity(buyerId: owner.PlayerId, cityId: "missing", priceMultiplier: UnitMultiplier).Should().BeFalse();
        owner.OwnedCityIds.Should().BeEmpty();
    }
}
