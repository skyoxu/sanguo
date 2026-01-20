using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using System;
using System.Collections.Generic;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class SanguoEventContractsTests
{
    [Fact]
    public void ShouldExposeExpectedEventTypes()
    {
        SanguoActionCardPlayed.EventType.Should().Be("core.sanguo.action_card.played");
        SanguoRandomEventApplied.EventType.Should().Be("core.sanguo.random_event.applied");
        SanguoBuildingBuilt.EventType.Should().Be("core.sanguo.building.built");
        SanguoLootGranted.EventType.Should().Be("core.sanguo.loot.granted");
        SanguoRelicApplied.EventType.Should().Be("core.sanguo.relic.applied");
    }

    [Fact]
    public void EventRecords_ShouldBeConstructible()
    {
        var now = DateTimeOffset.UtcNow;

        var started = new SanguoGameStarted(
            GameId: "g1",
            MapId: "map001",
            PlayersCount: 4,
            StartingMoneyPreset: 10000,
            GlobalEventIntervalTurns: 10,
            RandomSeed: 123,
            PlayerOrder: new[] { "p1", "ai-1", "ai-2", "ai-3" },
            CharacterAssignments: new Dictionary<string, string>
            {
                ["p1"] = "c_liu_bei",
                ["ai-1"] = "c_cao_cao",
                ["ai-2"] = "c_sun_quan",
                ["ai-3"] = "c_yuan_shao",
            },
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: "cmd-1");

        started.MapId.Should().Be("map001");
        SanguoGameStarted.EventType.Should().Be("core.sanguo.game.started");

        var actionCard = new SanguoActionCardPlayed(
            GameId: "g1",
            PlayerId: "p1",
            CardId: "card-1",
            EffectKind: SanguoEffectKinds.EconomyStepDelta,
            StepDelta: 1,
            DurationRounds: 3,
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: "cmd-2");

        actionCard.CardId.Should().Be("card-1");

        var built = new SanguoBuildingBuilt(
            GameId: "g1",
            PlayerId: "p1",
            CityId: "c1",
            BuildingId: "b_house",
            NewLevel: 1,
            EconomyStepDeltas: new SanguoEconomyStepDeltas(0, 0, 0, 0, 0),
            OccurredAt: now,
            CorrelationId: "corr-1",
            CausationId: "cmd-3");

        built.NewLevel.Should().Be(1);
    }

    [Fact]
    public void ShouldExposeExpectedEffectKindConstants()
    {
        SanguoEffectKinds.MoneyDelta.Should().Be("moneyDelta");
        SanguoEffectKinds.EconomyStepDelta.Should().Be("economyStepDelta");
    }
}

