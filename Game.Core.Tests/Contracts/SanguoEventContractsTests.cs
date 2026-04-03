using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using System;
using System.Collections.Generic;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class SanguoEventContractsTests
{
    [Fact]
    public void ShouldExposeExpectedEventTypes_WhenReadingSanguoContractConstants()
    {
        SanguoActionCardPlayed.EventType.Should().Be("core.sanguo.action_card.played");
        SanguoRandomEventApplied.EventType.Should().Be("core.sanguo.random_event.applied");
        SanguoBuildingBuilt.EventType.Should().Be("core.sanguo.building.built");
        SanguoLootGranted.EventType.Should().Be("core.sanguo.loot.granted");
        SanguoRelicApplied.EventType.Should().Be("core.sanguo.relic.applied");
        SanguoCardLost.EventType.Should().Be("core.sanguo.card.lost");
        SanguoRegionCaptured.EventType.Should().Be("core.sanguo.region.captured");
        SanguoRegionLost.EventType.Should().Be("core.sanguo.region.lost");
    }

    [Fact]
    public void ShouldConstructEventRecords_WhenUsingValidPayloads()
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
    public void ShouldExposeExpectedEffectKindConstants_WhenReadingSanguoEffectKinds()
    {
        SanguoEffectKinds.MoneyDelta.Should().Be("moneyDelta");
        SanguoEffectKinds.EconomyStepDelta.Should().Be("economyStepDelta");
        SanguoEffectKinds.TransferOwnership.Should().Be("transferOwnership");
    }

    // ACC:T66.4
    [Fact]
    public void ShouldExposeBossChallengePromptedConstants_WhenReadingForcedChallengeContract()
    {
        SanguoBossChallengePrompted.EventType.Should().Be("core.sanguo.boss.challenge.prompted");
        SanguoBossChallengePrompted.WinRateTierLow.Should().Be("low");
        SanguoBossChallengePrompted.WinRateTierMid.Should().Be("mid");
        SanguoBossChallengePrompted.WinRateTierHigh.Should().Be("high");
        SanguoBossChallengePrompted.FailConsequenceReturnToCampAndEndRound.Should().Be("return_to_camp_end_round");

        var occurredAt = DateTimeOffset.UtcNow;
        var contract = new SanguoBossChallengePrompted(
            GameId: "g1",
            BossId: "boss_1",
            RoundNumber: 6,
            WinRateTier: SanguoBossChallengePrompted.WinRateTierMid,
            NextRoundPressureForecast: 4,
            KeyLossSummary: "camp_hp_risk",
            FailConsequence: SanguoBossChallengePrompted.FailConsequenceReturnToCampAndEndRound,
            OccurredAt: occurredAt,
            CorrelationId: "corr-1",
            CausationId: "cmd-1");

        contract.GameId.Should().Be("g1");
        contract.BossId.Should().Be("boss_1");
        contract.RoundNumber.Should().Be(6);
        contract.WinRateTier.Should().Be(SanguoBossChallengePrompted.WinRateTierMid);
        contract.NextRoundPressureForecast.Should().Be(4);
        contract.KeyLossSummary.Should().Be("camp_hp_risk");
        contract.FailConsequence.Should().Be(SanguoBossChallengePrompted.FailConsequenceReturnToCampAndEndRound);
        contract.OccurredAt.Should().Be(occurredAt);
        contract.CorrelationId.Should().Be("corr-1");
        contract.CausationId.Should().Be("cmd-1");
    }
}
