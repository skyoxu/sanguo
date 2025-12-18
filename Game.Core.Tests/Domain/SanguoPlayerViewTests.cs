using System;
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
    public void Constructor_WhenPlayerIdIsEmpty_ThrowsArgumentException(string? playerId)
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
    public void Constructor_WhenPositionIndexNegative_ThrowsArgumentOutOfRangeException()
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
    public void Constructor_WhenOwnedCityIdsNull_ThrowsArgumentNullException()
    {
        Action act = () => _ = new SanguoPlayerView(
            playerId: "p1",
            money: Money.Zero,
            positionIndex: 0,
            ownedCityIds: null!,
            isEliminated: false);

        act.Should().Throw<ArgumentNullException>().WithParameterName("ownedCityIds");
    }
}

