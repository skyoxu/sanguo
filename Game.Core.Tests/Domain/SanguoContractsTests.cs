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
            TurnNumber: 1,
            Year: 200,
            Month: 1,
            PlayerSettlements: Array.Empty<PlayerSettlement>(),
            OccurredAt: DateTimeOffset.UtcNow,
            CorrelationId: "corr-1",
            CausationId: null,
            AppliedMultipliers: new AppliedMultipliers(
                BaseSteps: 2,
                CharacterStepDelta: 0,
                BuildingStepDelta: 0,
                EventStepDelta: 0,
                ActionCardStepDelta: 0,
                RelicStepDelta: 0,
                RegionStepDelta: 0,
                EffectiveSteps: 2)
        );

        evt.GameId.Should().Be("game-1");
        evt.Year.Should().Be(200);
        evt.Month.Should().Be(1);
    }
}
