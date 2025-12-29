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

    // ACC:T12.1
    [Fact]
    public void ShouldNotReferenceGodotAssemblies_WhenUsingBoardStateDomain()
    {
        var referenced = typeof(SanguoBoardState).Assembly.GetReferencedAssemblies();
        referenced.Should().NotContain(a => a.Name != null && a.Name.StartsWith("Godot", StringComparison.OrdinalIgnoreCase));
    }

    // ACC:T12.2
    [Fact]
    public void ShouldExposePlayersAndCitiesById_WhenCreated()
    {
        var city = MakeCity(id: "c1");
        var player = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0, economyRules: Rules);
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { city.Id, city } };
        var state = new SanguoBoardState(players: new[] { player }, citiesById: citiesById);
        state.Players.Should().ContainKey(player.PlayerId);
        state.CitiesById.Should().ContainKey(city.Id);
    state.Players[player.PlayerId].PositionIndex.Should().Be(0);
}

    // ACC:T12.3
    [Fact]
    public void ShouldEnforceUniquenessAndReferentialIntegrity_WhenCreatingBoardState()
    {
        var owned = MakeCity(id: "owned1");
        var player = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0, economyRules: Rules);
        player.TryBuyCity(owned, priceMultiplier: UnitMultiplier).Should().BeTrue();
        Action act = () => new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));
        act.Should().Throw<InvalidOperationException>();

        var cityKeyMismatch = MakeCity(id: "c2");
        var cleanPlayer = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0, economyRules: Rules);
        Action actKeyMismatch = () => new SanguoBoardState(
            players: new[] { cleanPlayer },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { { "c1", cityKeyMismatch } });
        actKeyMismatch.Should().Throw<ArgumentException>().WithParameterName("citiesById");

        var okCity = MakeCity(id: "c1");
        var p1 = new SanguoPlayer(playerId: "dup", money: 0m, positionIndex: 0, economyRules: Rules);
        var p2 = new SanguoPlayer(playerId: "dup", money: 0m, positionIndex: 0, economyRules: Rules);
        Action actDupPlayers = () => new SanguoBoardState(
            players: new[] { p1, p2 },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { { okCity.Id, okCity } });
        actDupPlayers.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void ShouldThrowArgumentException_WhenCitiesByIdKeyDoesNotMatchCityId()
    {
        var city = MakeCity(id: "c2");
        var player = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0, economyRules: Rules);
        Action act = () => new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { { "c1", city } });
        act.Should().Throw<ArgumentException>().WithParameterName("citiesById");
    }

    [Fact]
    public void ShouldThrowArgumentException_WhenDuplicatePlayerId()
    {
        var city = MakeCity(id: "c1");
        var p1 = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: Rules);
        var p2 = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: Rules);
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { city.Id, city } };
        Action act = () => new SanguoBoardState(players: new[] { p1, p2 }, citiesById: citiesById);
        act.Should().Throw<ArgumentException>();
    }

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
    [Fact]
    public void TryGetOwnerOfCity_WhenCityUnowned_ReturnsFalseAndOutputsNull()
    {
        var city = MakeCity(id: "c1");
        var player = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0, economyRules: Rules);
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { city.Id, city } };
        var state = new SanguoBoardState(players: new[] { player }, citiesById: citiesById);
        state.TryGetOwnerOfCity(city.Id, out var owner).Should().BeFalse();
        owner.Should().BeNull();
    }
    [Fact]
    public void TryGetOwnerOfCity_WhenCityOwnedByPlayer_ReturnsTrueAndOutputsOwner()
    {
        var city = MakeCity(id: "c1");
        var ownerPlayer = new SanguoPlayer(playerId: "owner", money: 200m, positionIndex: 0, economyRules: Rules);
        ownerPlayer.TryBuyCity(city, priceMultiplier: UnitMultiplier).Should().BeTrue();
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { city.Id, city } };
        var state = new SanguoBoardState(players: new[] { ownerPlayer }, citiesById: citiesById);
        state.TryGetOwnerOfCity(city.Id, out var resolved).Should().BeTrue();
        resolved.Should().BeSameAs(ownerPlayer);
    }
    [Fact]
    public void TryGetOwnerOfCity_WhenMultipleOwnersDetected_ThrowsInvalidOperationException()
    {
        var city = MakeCity(id: "c1");
        var owner1 = new SanguoPlayer(playerId: "o1", money: 200m, positionIndex: 0, economyRules: Rules);
        var owner2 = new SanguoPlayer(playerId: "o2", money: 200m, positionIndex: 0, economyRules: Rules);
        owner1.TryBuyCity(city, priceMultiplier: UnitMultiplier).Should().BeTrue();
        owner2.TryBuyCity(city, priceMultiplier: UnitMultiplier).Should().BeTrue();
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { city.Id, city } };
        var state = new SanguoBoardState(players: new[] { owner1, owner2 }, citiesById: citiesById);
        Action act = () => state.TryGetOwnerOfCity(city.Id, out _);
        act.Should().Throw<InvalidOperationException>();
    }
    [Fact]
    public void TryGetOwnerOfCity_WhenCityIdIsEmpty_ThrowsArgumentException()
    {
        var player = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: Rules);
        var state = new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));
        Action act = () => state.TryGetOwnerOfCity(" ", out _);
        act.Should().Throw<ArgumentException>().WithParameterName("cityId");
    }
    [Fact]
    public void TryGetPlayer_WhenPlayerNotFound_ReturnsFalseAndOutputsNull()
    {
        var player = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: Rules);
        var state = new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));
        state.TryGetPlayer("missing", out var resolved).Should().BeFalse();
        resolved.Should().BeNull();
    }
    [Fact]
    public void TryGetPlayer_WhenPlayerIdIsEmpty_ThrowsArgumentException()
    {
        var player = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: Rules);
        var state = new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));
        Action act = () => state.TryGetPlayer(" ", out _);
        act.Should().Throw<ArgumentException>().WithParameterName("playerId");
    }
    [Fact]
    public void GetCitiesSnapshot_ShouldNotAffectInternalCities()
    {
        var city = MakeCity(id: "c1");
        var buyer = new SanguoPlayer(playerId: "buyer", money: 200m, positionIndex: 0, economyRules: Rules);
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { city.Id, city } };
        var state = new SanguoBoardState(players: new[] { buyer }, citiesById: citiesById);
        var snapshot = state.GetCitiesSnapshot();
        snapshot.Should().ContainKey(city.Id);
        ((Dictionary<string, City>)snapshot).Remove(city.Id);
        state.TryBuyCity(buyerId: buyer.PlayerId, cityId: city.Id, priceMultiplier: UnitMultiplier).Should().BeTrue();
    }
}
