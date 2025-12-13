using System;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Domain;

public sealed class SanguoContractsTests
{
    [Fact]
    public void TokenMovedEventHasExpectedEventType()
    {
        SanguoTokenMoved.EventType.Should().Be("core.sanguo.board.token.moved");
    }

    [Fact]
    public void GameTurnAdvancedEventHasExpectedEventType()
    {
        SanguoGameTurnAdvanced.EventType.Should().Be("core.sanguo.game.turn.advanced");
    }

    [Fact]
    public void CanCreateMonthSettledEventWithBasicValues()
    {
        var evt = new SanguoMonthSettled(
            GameId: "game-1",
            Year: 200,
            Month: 1,
            PlayerSettlements: Array.Empty<PlayerSettlement>(),
            OccurredAt: DateTimeOffset.UtcNow,
            CorrelationId: "corr-1",
            CausationId: null
        );

        evt.GameId.Should().Be("game-1");
        evt.Year.Should().Be(200);
        evt.Month.Should().Be(1);
    }
}

