// Acceptance anchors:
// ACC:T9.4

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
}
