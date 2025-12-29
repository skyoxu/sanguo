using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Xunit;
namespace Game.Core.Tests.Domain;
public class SanguoPlayerViewTests
{
    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void ShouldThrowArgumentException_WhenPlayerIdIsEmpty(string? playerId)
    {
        Action act = () => _ = new SanguoPlayerView(
            playerId: playerId!,
            money: Money.Zero,
            positionIndex: 0,
            ownedCityIds: Array.Empty<string>(),
            isEliminated: false);
        act.Should().Throw<ArgumentException>().WithParameterName("playerId");
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenPositionIndexIsNegative()
    {
        Action act = () => _ = new SanguoPlayerView(
            playerId: "p1",
            money: Money.Zero,
            positionIndex: -1,
            ownedCityIds: Array.Empty<string>(),
            isEliminated: false);
        act.Should().Throw<ArgumentOutOfRangeException>().WithParameterName("positionIndex");
    }
    [Fact]
    public void ShouldThrowArgumentNullException_WhenOwnedCityIdsIsNull()
    {
        Action act = () => _ = new SanguoPlayerView(
            playerId: "p1",
            money: Money.Zero,
            positionIndex: 0,
            ownedCityIds: null!,
            isEliminated: false);
        act.Should().Throw<ArgumentNullException>().WithParameterName("ownedCityIds");
    }

    // ACC:T11.2
    [Fact]
    public void ShouldReturnImmutableSnapshot_WhenCreatingPlayerViewFromPlayer()
    {
        var rules = SanguoEconomyRules.Default;
        var player = new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0, economyRules: rules);
        var city1 = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromMajorUnits(100), baseToll: Money.FromMajorUnits(10));
        player.TryBuyCity(city1, priceMultiplier: 1.0m).Should().BeTrue();

        var view = player.ToView();
        view.Should().BeOfType<SanguoPlayerView>();
        view.PlayerId.Should().Be("p1");
        view.PositionIndex.Should().Be(0);
        view.IsEliminated.Should().BeFalse();
        view.OwnedCityIds.Should().ContainSingle("c1");

        var city2 = new City(id: "c2", name: "City2", regionId: "r1", basePrice: Money.FromMajorUnits(1), baseToll: Money.FromMajorUnits(1));
        player.TryBuyCity(city2, priceMultiplier: 1.0m).Should().BeTrue();
        view.OwnedCityIds.Should().ContainSingle("c1", "view must not observe later domain mutations");
    }
}
