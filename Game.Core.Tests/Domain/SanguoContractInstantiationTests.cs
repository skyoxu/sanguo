using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Domain;

public sealed class SanguoContractInstantiationTests
{
    [Fact]
    public void CanInstantiateBoardEvents()
    {
        var now = DateTimeOffset.UtcNow;

        var moved = new SanguoTokenMoved(
            GameId: "game-1",
            PlayerId: "p1",
            FromIndex: 0,
            ToIndex: 3,
            Steps: 3,
            PassedStart: false,
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );

        moved.GameId.Should().Be("game-1");
        moved.PlayerId.Should().Be("p1");
        moved.FromIndex.Should().Be(0);
        moved.ToIndex.Should().Be(3);
        moved.Steps.Should().Be(3);
        moved.PassedStart.Should().BeFalse();
        moved.OccurredAt.Should().Be(now);
        moved.CorrelationId.Should().Be("corr-1");
        moved.CausationId.Should().BeNull();

        var rolled = new SanguoDiceRolled(
            GameId: "game-1",
            PlayerId: "p1",
            Value: 6,
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );

        rolled.GameId.Should().Be("game-1");
        rolled.PlayerId.Should().Be("p1");
        rolled.Value.Should().Be(6);
        rolled.OccurredAt.Should().Be(now);
        rolled.CorrelationId.Should().Be("corr-1");
        rolled.CausationId.Should().BeNull();
    }

    [Fact]
    public void CanInstantiateGameEvents()
    {
        var now = DateTimeOffset.UtcNow;

        var started = new SanguoGameTurnStarted(
            GameId: "game-1",
            TurnNumber: 1,
            ActivePlayerId: "p1",
            Year: 200,
            Month: 1,
            Day: 1,
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );
        started.GameId.Should().Be("game-1");
        started.TurnNumber.Should().Be(1);
        started.ActivePlayerId.Should().Be("p1");
        started.Year.Should().Be(200);
        started.Month.Should().Be(1);
        started.Day.Should().Be(1);
        started.OccurredAt.Should().Be(now);
        started.CorrelationId.Should().Be("corr-1");
        started.CausationId.Should().BeNull();

        var ended = new SanguoGameTurnEnded(
            GameId: "game-1",
            TurnNumber: 1,
            ActivePlayerId: "p1",
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );
        ended.GameId.Should().Be("game-1");
        ended.TurnNumber.Should().Be(1);
        ended.ActivePlayerId.Should().Be("p1");
        ended.OccurredAt.Should().Be(now);
        ended.CorrelationId.Should().Be("corr-1");
        ended.CausationId.Should().BeNull();

        var advanced = new SanguoGameTurnAdvanced(
            GameId: "game-1",
            TurnNumber: 2,
            ActivePlayerId: "p2",
            Year: 200,
            Month: 1,
            Day: 2,
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );
        advanced.GameId.Should().Be("game-1");
        advanced.TurnNumber.Should().Be(2);
        advanced.ActivePlayerId.Should().Be("p2");
        advanced.Year.Should().Be(200);
        advanced.Month.Should().Be(1);
        advanced.Day.Should().Be(2);
        advanced.OccurredAt.Should().Be(now);
        advanced.CorrelationId.Should().Be("corr-1");
        advanced.CausationId.Should().BeNull();

        var saved = new SanguoGameSaved(
            GameId: "game-1",
            SaveSlotId: "slot-1",
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );
        saved.GameId.Should().Be("game-1");
        saved.SaveSlotId.Should().Be("slot-1");
        saved.OccurredAt.Should().Be(now);
        saved.CorrelationId.Should().Be("corr-1");
        saved.CausationId.Should().BeNull();

        var loaded = new SanguoGameLoaded(
            GameId: "game-1",
            SaveSlotId: "slot-1",
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );
        loaded.GameId.Should().Be("game-1");
        loaded.SaveSlotId.Should().Be("slot-1");
        loaded.OccurredAt.Should().Be(now);
        loaded.CorrelationId.Should().Be("corr-1");
        loaded.CausationId.Should().BeNull();

        var gameEnded = new SanguoGameEnded(
            GameId: "game-1",
            EndReason: "bankrupt",
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );
        gameEnded.GameId.Should().Be("game-1");
        gameEnded.EndReason.Should().Be("bankrupt");
        gameEnded.OccurredAt.Should().Be(now);
        gameEnded.CorrelationId.Should().Be("corr-1");
        gameEnded.CausationId.Should().BeNull();
    }

    [Fact]
    public void CanInstantiatePlayerAndAiEvents()
    {
        var now = DateTimeOffset.UtcNow;

        var stateChanged = new SanguoPlayerStateChanged(
            GameId: "game-1",
            PlayerId: "p1",
            Money: 123.45m,
            PositionIndex: 7,
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );
        stateChanged.GameId.Should().Be("game-1");
        stateChanged.PlayerId.Should().Be("p1");
        stateChanged.Money.Should().Be(123.45m);
        stateChanged.PositionIndex.Should().Be(7);
        stateChanged.OccurredAt.Should().Be(now);
        stateChanged.CorrelationId.Should().Be("corr-1");
        stateChanged.CausationId.Should().BeNull();

        var decision = new SanguoAiDecisionMade(
            GameId: "game-1",
            AiPlayerId: "ai-1",
            DecisionType: "buy",
            TargetCityId: "city-1",
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );
        decision.GameId.Should().Be("game-1");
        decision.AiPlayerId.Should().Be("ai-1");
        decision.DecisionType.Should().Be("buy");
        decision.TargetCityId.Should().Be("city-1");
        decision.OccurredAt.Should().Be(now);
        decision.CorrelationId.Should().Be("corr-1");
        decision.CausationId.Should().BeNull();
    }

    [Fact]
    public void CanInstantiateEconomyEvents()
    {
        var now = DateTimeOffset.UtcNow;

        var settlements = new List<PlayerSettlement>
        {
            new(PlayerId: "p1", AmountDelta: 100m),
            new(PlayerId: "p2", AmountDelta: -50m),
        };
        settlements[0].PlayerId.Should().Be("p1");
        settlements[0].AmountDelta.Should().Be(100m);
        settlements[1].PlayerId.Should().Be("p2");
        settlements[1].AmountDelta.Should().Be(-50m);

        var month = new SanguoMonthSettled(
            GameId: "game-1",
            Year: 200,
            Month: 1,
            PlayerSettlements: settlements,
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );
        month.GameId.Should().Be("game-1");
        month.Year.Should().Be(200);
        month.Month.Should().Be(1);
        month.PlayerSettlements.Should().HaveCount(2);
        month.OccurredAt.Should().Be(now);
        month.CorrelationId.Should().Be("corr-1");
        month.CausationId.Should().BeNull();

        var season = new SanguoSeasonEventApplied(
            GameId: "game-1",
            Year: 200,
            Season: 1,
            AffectedRegionIds: new[] { "r1", "r2" },
            YieldMultiplier: 0.9m,
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );
        season.GameId.Should().Be("game-1");
        season.Year.Should().Be(200);
        season.Season.Should().Be(1);
        season.AffectedRegionIds.Should().HaveCount(2);
        season.YieldMultiplier.Should().Be(0.9m);
        season.OccurredAt.Should().Be(now);
        season.CorrelationId.Should().Be("corr-1");
        season.CausationId.Should().BeNull();

        var priceAdjusted = new SanguoYearPriceAdjusted(
            GameId: "game-1",
            Year: 200,
            CityId: "c1",
            OldPrice: 1000m,
            NewPrice: 1200m,
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );
        priceAdjusted.GameId.Should().Be("game-1");
        priceAdjusted.Year.Should().Be(200);
        priceAdjusted.CityId.Should().Be("c1");
        priceAdjusted.OldPrice.Should().Be(1000m);
        priceAdjusted.NewPrice.Should().Be(1200m);
        priceAdjusted.OccurredAt.Should().Be(now);
        priceAdjusted.CorrelationId.Should().Be("corr-1");
        priceAdjusted.CausationId.Should().BeNull();

        var cityBought = new SanguoCityBought(
            GameId: "game-1",
            BuyerId: "p1",
            CityId: "c1",
            Price: 1200m,
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );
        cityBought.GameId.Should().Be("game-1");
        cityBought.BuyerId.Should().Be("p1");
        cityBought.CityId.Should().Be("c1");
        cityBought.Price.Should().Be(1200m);
        cityBought.OccurredAt.Should().Be(now);
        cityBought.CorrelationId.Should().Be("corr-1");
        cityBought.CausationId.Should().BeNull();

        var tollPaid = new SanguoCityTollPaid(
            GameId: "game-1",
            PayerId: "p2",
            OwnerId: "p1",
            CityId: "c1",
            Amount: 50m,
            OwnerAmount: 50m,
            TreasuryOverflow: 0m,
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: null
        );
        tollPaid.GameId.Should().Be("game-1");
        tollPaid.PayerId.Should().Be("p2");
        tollPaid.OwnerId.Should().Be("p1");
        tollPaid.CityId.Should().Be("c1");
        tollPaid.Amount.Should().Be(50m);
        tollPaid.OwnerAmount.Should().Be(50m);
        tollPaid.TreasuryOverflow.Should().Be(0m);
        tollPaid.OccurredAt.Should().Be(now);
        tollPaid.CorrelationId.Should().Be("corr-1");
        tollPaid.CausationId.Should().BeNull();
    }
}
