using System;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Domain;

public sealed class SanguoContractsTests
{
    [Fact]
    public void TokenMoved_event_has_expected_event_type()
    {
        SanguoTokenMoved.EventType.Should().Be("core.sanguo.board.token.moved");
    }

    [Fact]
    public void GameTurnAdvanced_event_has_expected_event_type()
    {
        SanguoGameTurnAdvanced.EventType.Should().Be("core.sanguo.game.turn.advanced");
    }

    [Fact]
    public void Can_create_month_settled_event_with_basic_values()
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

