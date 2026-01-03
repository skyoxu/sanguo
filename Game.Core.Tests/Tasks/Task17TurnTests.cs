using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Ports;
using Game.Core.Services;
using Game.Core.Utilities;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task17TurnTests
{
    // ACC:T17.1
    [Fact]
    public void ShouldNotReferenceGodotAssemblies_WhenUsingTurnLoopInGameCore()
    {
        var referenced = typeof(SanguoTurnManager).Assembly.GetReferencedAssemblies();
        referenced.Should().NotContain(a => a.Name != null && a.Name.StartsWith("Godot", StringComparison.OrdinalIgnoreCase));
    }

    // ACC:T17.3
    [Fact]
    public async Task ShouldEndGameImmediately_WhenHumanPlayerIsEliminated()
    {
        var bus = new CapturingEventBus();
        var rules = SanguoEconomyRules.Default;

        var treasury = new SanguoTreasury();
        var owner = new SanguoPlayer(playerId: "npc-owner", money: 0m, positionIndex: 0, economyRules: rules);
        var human = new SanguoPlayer(playerId: "p1", money: 1m, positionIndex: 0, economyRules: rules);
        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromMajorUnits(1), baseToll: Money.FromMajorUnits(10), positionIndex: 0);

        human.TryPayTollTo(owner, city, tollMultiplier: 1.0m, treasury: treasury).Should().BeTrue();
        human.IsEliminated.Should().BeTrue();

        var boardState = new SanguoBoardState(
            players: new[] { human, owner },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city });

        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(bus, economy, boardState, treasury);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-1",
            causationId: null);

        await mgr.AdvanceTurnAsync(correlationId: "corr-2", causationId: "cmd-advance");

        bus.Published.Should().ContainSingle(e => e.Type == SanguoGameTurnStarted.EventType);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoGameEnded.EventType);

        var ended = bus.Published.Find(e => e.Type == SanguoGameEnded.EventType);
        ended.Should().NotBeNull();
        ended!.Data.Should().BeOfType<JsonElementEventData>();

        var payload = ((JsonElementEventData)ended.Data!).Value;
        payload.GetProperty("GameId").GetString().Should().Be("g1");
        payload.GetProperty("EndReason").GetString().Should().Be("human_eliminated");

        var countBefore = bus.Published.Count;
        var act = async () => await mgr.AdvanceTurnAsync(correlationId: "corr-3", causationId: "cmd-advance-again");
        await act.Should().ThrowAsync<InvalidOperationException>();
        bus.Published.Should().HaveCount(countBefore);
    }

    // ACC:T17.10
    // Turn loop must not advance date/actor until an explicit human action command is applied.
    [Fact]
    [Trait("acceptance", "ACC:T17.10")]
    public async Task ShouldNotAdvanceTurnOrDate_WhenAwaitingHumanActionCommand()
    {
        var bus = new CapturingEventBus();
        var rules = SanguoEconomyRules.Default;

        var human = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(
            players: new[] { human },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var treasury = new SanguoTreasury();
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(bus, economy, boardState, treasury);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-1",
            causationId: null);

        bus.Published.Should().ContainSingle(e => e.Type == SanguoGameTurnStarted.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoGameTurnEnded.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoGameTurnAdvanced.EventType);
        bus.Published.Should().HaveCount(1);

        var started = bus.Published.Find(e => e.Type == SanguoGameTurnStarted.EventType);
        started.Should().NotBeNull();
        started!.Data.Should().BeOfType<JsonElementEventData>();
        var payload = ((JsonElementEventData)started.Data!).Value;
        payload.GetProperty("ActivePlayerId").GetString().Should().Be("p1");
        payload.GetProperty("Year").GetInt32().Should().Be(1);
        payload.GetProperty("Month").GetInt32().Should().Be(1);
        payload.GetProperty("Day").GetInt32().Should().Be(1);
    }

    // ACC:T17.10
    [Fact]
    [Trait("acceptance", "ACC:T17.10")]
    public void ShouldPublishDiceRolledEventWithTraceIds_WhenRollingD6()
    {
        var bus = new CapturingEventBus();
        var svc = new SanguoDiceService(bus, rng: new RangeAwareFixedRng(diceValue: 6, nextDouble: 0.0));

        var value = svc.RollD6(gameId: "g1", playerId: "p1", correlationId: "corr-1", causationId: "cause-1");
        value.Should().BeInRange(1, 6);

        var evt = bus.Published.Find(e => e.Type == SanguoDiceRolled.EventType);
        evt.Should().NotBeNull();
        evt!.Data.Should().BeOfType<JsonElementEventData>();
        var payload = ((JsonElementEventData)evt.Data!).Value;
        payload.GetProperty("GameId").GetString().Should().Be("g1");
        payload.GetProperty("PlayerId").GetString().Should().Be("p1");
        payload.GetProperty("Value").GetInt32().Should().Be(value);
        payload.GetProperty("CorrelationId").GetString().Should().Be("corr-1");
        payload.GetProperty("CausationId").GetString().Should().Be("cause-1");
    }

    // ACC:T17.10
    [Fact]
    [Trait("acceptance", "ACC:T17.10")]
    public async Task ShouldRotateToNextPlayer_WhenAdvancingTurn()
    {
        var bus = new CapturingEventBus();
        var rules = SanguoEconomyRules.Default;

        var human = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: "ai-1", money: 0m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(
            players: new[] { human, ai },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var treasury = new SanguoTreasury();
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(bus, economy, boardState, treasury, rng: new RangeAwareFixedRng(diceValue: 6, nextDouble: 1.0), totalPositionsHint: 10, quarterEnvironmentEventTriggerChance: 0.0);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { human.PlayerId, ai.PlayerId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-1",
            causationId: null);

        bus.Published.Should().NotContain(e => e.Type == SanguoAiDecisionMade.EventType);

        await mgr.AdvanceTurnAsync(correlationId: "corr-2", causationId: "cmd-advance");

        var advanced = bus.Published.FindLast(e => e.Type == SanguoGameTurnAdvanced.EventType);
        advanced.Should().NotBeNull();
        var payload = ((JsonElementEventData)advanced!.Data!).Value;
        payload.GetProperty("ActivePlayerId").GetString().Should().Be(ai.PlayerId);
        payload.GetProperty("Year").GetInt32().Should().Be(1);
        payload.GetProperty("Month").GetInt32().Should().Be(1);
        payload.GetProperty("Day").GetInt32().Should().Be(2);

        bus.Published.Should().Contain(e => e.Type == SanguoAiDecisionMade.EventType);
    }

    // ACC:T17.13
    [Fact]
    [Trait("acceptance", "ACC:T17.13")]
    public async Task ShouldAlternateBetweenHumanAndAi_WhenAdvancingTurns()
    {
        const int totalPositions = 10;
        var bus = new CapturingEventBus();
        var rules = SanguoEconomyRules.Default;

        var human = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: "ai-1", money: 0m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(
            players: new[] { human, ai },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var treasury = new SanguoTreasury();
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            rng: new RangeAwareFixedRng(diceValue: 1, nextDouble: 0.0),
            totalPositionsHint: totalPositions,
            quarterEnvironmentEventTriggerChance: 0.0);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { human.PlayerId, ai.PlayerId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-1",
            causationId: null);

        bus.Published.Should().NotContain(e => e.Type == SanguoAiDecisionMade.EventType);

        var expectedActive = new[] { ai.PlayerId, human.PlayerId, ai.PlayerId, human.PlayerId };
        var aiDecisionCountsAfterEachAdvance = new[] { 1, 1, 2, 2 };

        for (var i = 0; i < expectedActive.Length; i++)
        {
            await mgr.AdvanceTurnAsync(correlationId: $"corr-{i + 2}", causationId: $"cmd-advance-{i + 1}");

            var advanced = bus.Published.FindLast(e => e.Type == SanguoGameTurnAdvanced.EventType);
            advanced.Should().NotBeNull();
            var payload = ((JsonElementEventData)advanced!.Data!).Value;
            payload.GetProperty("ActivePlayerId").GetString().Should().Be(expectedActive[i]);
            payload.GetProperty("Day").GetInt32().Should().Be(2 + i);

            var aiDecisions = bus.Published.FindAll(e => e.Type == SanguoAiDecisionMade.EventType);
            aiDecisions.Should().HaveCount(aiDecisionCountsAfterEachAdvance[i]);
        }
    }

    // ACC:T17.3
    [Fact]
    [Trait("acceptance", "ACC:T17.3")]
    public async Task ShouldSkipEliminatedAiAndReleaseOwnedCities_WhenAiGoesBankruptOnTollPayment()
    {
        var bus = new CapturingEventBus();
        var rules = SanguoEconomyRules.Default;
        var treasury = new SanguoTreasury();

        var cityOwnedByHuman = new City(
            id: "c-human",
            name: "CityHuman",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(0),
            baseToll: Money.FromMajorUnits(10),
            positionIndex: 0);

        var cityOwnedByAi = new City(
            id: "c-ai",
            name: "CityAi",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(0),
            baseToll: Money.FromMajorUnits(1),
            positionIndex: 1);

        var human = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: "ai-1", money: 1m, positionIndex: 1, economyRules: rules);

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            [cityOwnedByHuman.Id] = cityOwnedByHuman,
            [cityOwnedByAi.Id] = cityOwnedByAi,
        };

        var boardState = new SanguoBoardState(players: new[] { human, ai }, citiesById: citiesById);
        boardState.TryBuyCity(buyerId: human.PlayerId, cityId: cityOwnedByHuman.Id, priceMultiplier: 1.0m).Should().BeTrue();
        boardState.TryBuyCity(buyerId: ai.PlayerId, cityId: cityOwnedByAi.Id, priceMultiplier: 1.0m).Should().BeTrue();
        ai.OwnsCityId(cityOwnedByAi.Id).Should().BeTrue();

        var rng = new RangeAwareFixedRng(diceValue: 1, nextDouble: 1.0);
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(bus, economy, boardState, treasury, rng: rng, totalPositionsHint: 2, quarterEnvironmentEventTriggerChance: 0.0);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { ai.PlayerId, human.PlayerId },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-1",
            causationId: null);

        ai.IsEliminated.Should().BeTrue();
        ai.OwnsCityId(cityOwnedByAi.Id).Should().BeFalse();
        boardState.TryGetOwnerOfCity(cityOwnedByAi.Id, out _).Should().BeFalse();

        await mgr.AdvanceTurnAsync(correlationId: "corr-2", causationId: "cmd-advance");

        var lastStarted = bus.Published.FindLast(e => e.Type == SanguoGameTurnStarted.EventType);
        lastStarted.Should().NotBeNull();
        var lastStartedPayload = ((JsonElementEventData)lastStarted!.Data!).Value;
        lastStartedPayload.GetProperty("ActivePlayerId").GetString().Should().Be(human.PlayerId);

        bus.Published.FindAll(e => e.Type == SanguoAiDecisionMade.EventType).Should().HaveCount(1);
    }

    // ACC:T17.4
    [Fact]
    [Trait("acceptance", "ACC:T17.4")]
    public async Task ShouldCapOwnerMoneyDepositOverflowToTreasuryAndReport_WhenTollPaymentExceedsMoneyCap()
    {
        var bus = new CapturingEventBus();
        var reporter = new CapturingErrorReporter();
        var economy = new SanguoEconomyManager(bus, reporter);
        var rules = SanguoEconomyRules.Default;

        var treasury = new SanguoTreasury();
        var ownerStart = (decimal)Money.MaxMajorUnits - 1m;
        var owner = new SanguoPlayer(playerId: "owner", money: ownerStart, positionIndex: 0, economyRules: rules);
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0, economyRules: rules);

        var city = new City(
            id: "c1",
            name: "City1",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(0),
            baseToll: Money.FromMajorUnits(10),
            positionIndex: 0);

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };
        var boardState = new SanguoBoardState(players: new[] { owner, payer }, citiesById: citiesById);
        boardState.TryBuyCity(buyerId: owner.PlayerId, cityId: city.Id, priceMultiplier: 1.0m).Should().BeTrue();

        var occurredAt = new DateTimeOffset(2026, 1, 3, 0, 0, 0, TimeSpan.Zero);
        var paid = await economy.TryPayTollAndPublishEventAsync(
            gameId: "g1",
            players: new[] { owner, payer },
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: city.Id,
            tollMultiplier: 1.0m,
            treasury: treasury,
            correlationId: "corr-1",
            causationId: "cause-1",
            occurredAt: occurredAt);

        paid.Should().BeTrue();
        payer.Money.ToDecimal().Should().Be(90m);
        owner.Money.Should().Be(Money.FromMajorUnits(Money.MaxMajorUnits));
        treasury.MinorUnits.Should().Be(9 * Money.MinorUnitsPerUnit);

        reporter.Messages.Should().ContainSingle(m => m.Message == "sanguo.money.capped");
        reporter.Messages[0].Context.Should().ContainKey("correlation_id").WhoseValue.Should().Be("corr-1");
        reporter.Messages[0].Context.Should().ContainKey("causation_id").WhoseValue.Should().Be("cause-1");

        var evt = bus.Published.Find(e => e.Type == SanguoCityTollPaid.EventType);
        evt.Should().NotBeNull();
        var payload = ((JsonElementEventData)evt!.Data!).Value;
        payload.GetProperty("OwnerAmount").GetDecimal().Should().Be(1m);
        payload.GetProperty("TreasuryOverflow").GetDecimal().Should().Be(9m);
    }

    // ACC:T17.4
    [Fact]
    [Trait("acceptance", "ACC:T17.4")]
    public async Task ShouldRollbackPayerOwnerAndTreasury_WhenEventPublishFailsAfterCappedTollPayment()
    {
        var bus = new ThrowingEventBus();
        var reporter = new CapturingErrorReporter();
        var economy = new SanguoEconomyManager(bus, reporter);
        var rules = SanguoEconomyRules.Default;

        var treasury = new SanguoTreasury();
        var ownerStart = (decimal)Money.MaxMajorUnits - 1m;
        var owner = new SanguoPlayer(playerId: "owner", money: ownerStart, positionIndex: 0, economyRules: rules);
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0, economyRules: rules);

        var city = new City(
            id: "c1",
            name: "City1",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(0),
            baseToll: Money.FromMajorUnits(10),
            positionIndex: 0);

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };
        var boardState = new SanguoBoardState(players: new[] { owner, payer }, citiesById: citiesById);
        boardState.TryBuyCity(buyerId: owner.PlayerId, cityId: city.Id, priceMultiplier: 1.0m).Should().BeTrue();

        var ownerBefore = owner.Money;
        var payerBefore = payer.Money;
        var treasuryBefore = treasury.MinorUnits;

        var act = async () =>
        {
            _ = await economy.TryPayTollAndPublishEventAsync(
                gameId: "g1",
                players: new[] { owner, payer },
                citiesById: citiesById,
                payerId: payer.PlayerId,
                cityId: city.Id,
                tollMultiplier: 1.0m,
                treasury: treasury,
                correlationId: "corr-1",
                causationId: "cause-1",
                occurredAt: DateTimeOffset.UtcNow);
        };

        await act.Should().ThrowAsync<InvalidOperationException>();
        payer.Money.Should().Be(payerBefore);
        owner.Money.Should().Be(ownerBefore);
        treasury.MinorUnits.Should().Be(treasuryBefore);

        reporter.Messages.Should().BeEmpty();
    }

    // ACC:T17.2
    // ACC:T17.5
    // ACC:T17.7
    // ACC:T17.8
    [Fact]
    [Trait("acceptance", "ACC:T17.2")]
    [Trait("acceptance", "ACC:T17.5")]
    [Trait("acceptance", "ACC:T17.7")]
    [Trait("acceptance", "ACC:T17.8")]
    public async Task ShouldPublishMonthThenSeasonThenYearEvents_WhenCrossingYearBoundaryInSingleAdvance()
    {
        var bus = new CapturingEventBus();
        var rules = SanguoEconomyRules.Default;

        var city = new City(
            id: "c1",
            name: "City1",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(1),
            baseToll: Money.FromMajorUnits(10),
            positionIndex: 0);

        var player = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city });

        var treasury = new SanguoTreasury();
        var economy = new SanguoEconomyManager(bus);
        var rng = new RangeAwareFixedRng(diceValue: 6, nextDouble: 0.0);

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: rng,
            totalPositionsHint: 10,
            quarterEnvironmentEventTriggerChance: 1.0,
            quarterEnvironmentEventYieldMultiplier: 0.9m);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 12,
            day: 30,
            correlationId: "corr-1",
            causationId: null);

        await mgr.AdvanceTurnAsync(correlationId: "corr-2", causationId: "cmd-advance");

        var monthIndex = bus.Published.FindIndex(e => e.Type == SanguoMonthSettled.EventType);
        var seasonIndex = bus.Published.FindIndex(e => e.Type == SanguoSeasonEventApplied.EventType);
        var yearIndex = bus.Published.FindIndex(e => e.Type == SanguoYearPriceAdjusted.EventType);
        var advancedIndex = bus.Published.FindIndex(e => e.Type == SanguoGameTurnAdvanced.EventType);

        monthIndex.Should().BeGreaterThanOrEqualTo(0);
        seasonIndex.Should().BeGreaterThanOrEqualTo(0);
        yearIndex.Should().BeGreaterThanOrEqualTo(0);
        advancedIndex.Should().BeGreaterThanOrEqualTo(0);

        monthIndex.Should().BeLessThan(seasonIndex);
        seasonIndex.Should().BeLessThan(yearIndex);

        var advanced = bus.Published[advancedIndex];
        var advancedPayload = ((JsonElementEventData)advanced.Data!).Value;
        advancedPayload.GetProperty("Year").GetInt32().Should().Be(2);
        advancedPayload.GetProperty("Month").GetInt32().Should().Be(1);
        advancedPayload.GetProperty("Day").GetInt32().Should().Be(1);

        var month = bus.Published[monthIndex];
        var monthPayload = ((JsonElementEventData)month.Data!).Value;
        monthPayload.GetProperty("Year").GetInt32().Should().Be(1);
        monthPayload.GetProperty("Month").GetInt32().Should().Be(12);
        var settlements = monthPayload.GetProperty("PlayerSettlements");
        settlements.ValueKind.Should().Be(JsonValueKind.Array);
        settlements.EnumerateArray().Select(x => x.GetProperty("PlayerId").GetString()).Should().Contain("p1");

        var season = bus.Published[seasonIndex];
        var seasonPayload = ((JsonElementEventData)season.Data!).Value;
        seasonPayload.GetProperty("Year").GetInt32().Should().Be(2);
        seasonPayload.GetProperty("Season").GetInt32().Should().Be(1);
        seasonPayload.GetProperty("YieldMultiplier").GetDecimal().Should().Be(0.9m);
        seasonPayload.GetProperty("AffectedRegionIds").EnumerateArray().Select(x => x.GetString()).Should().Contain("r1");

        var year = bus.Published[yearIndex];
        var yearPayload = ((JsonElementEventData)year.Data!).Value;
        yearPayload.GetProperty("Year").GetInt32().Should().Be(2);
        yearPayload.GetProperty("CityId").GetString().Should().Be(city.Id);
        yearPayload.GetProperty("OldPrice").GetDecimal().Should().Be(1m);
        yearPayload.GetProperty("NewPrice").GetDecimal().Should().Be(0.5m);
    }

    // ACC:T17.6
    // ACC:T17.11
    [Fact]
    [Trait("acceptance", "ACC:T17.6")]
    [Trait("acceptance", "ACC:T17.11")]
    public async Task ShouldPublishAiDecisionAndMoveEvents_WhenStartingGameWithAiPlayer()
    {
        const int totalPositions = 10;
        var bus = new CapturingEventBus();
        var rules = SanguoEconomyRules.Default;

        var ai = new SanguoPlayer(playerId: "ai-1", money: 0m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(
            players: new[] { ai },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var treasury = new SanguoTreasury();
        var economy = new SanguoEconomyManager(bus);
        var policy = new SpyAiDecisionPolicy();
        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            aiDecisionPolicy: policy,
            rng: new RangeAwareFixedRng(diceValue: 6, nextDouble: 0.0),
            totalPositionsHint: totalPositions);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "ai-1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-1",
            causationId: null);

        policy.Seen.Should().BeTrue();
        policy.SeenSelfType.Should().Be(typeof(SanguoPlayerView));

        bus.Published.Should().Contain(e => e.Type == SanguoAiDecisionMade.EventType);
        bus.Published.Should().Contain(e => e.Type == SanguoDiceRolled.EventType);
        bus.Published.Should().Contain(e => e.Type == SanguoTokenMoved.EventType);

        var dice = bus.Published.Find(e => e.Type == SanguoDiceRolled.EventType);
        dice.Should().NotBeNull();
        var dicePayload = ((JsonElementEventData)dice!.Data!).Value;
        dicePayload.GetProperty("Value").GetInt32().Should().BeInRange(1, 6);
        dicePayload.GetProperty("CorrelationId").GetString().Should().Be("corr-1");

        var decision = bus.Published.Find(e => e.Type == SanguoAiDecisionMade.EventType);
        decision.Should().NotBeNull();
        var decisionPayload = ((JsonElementEventData)decision!.Data!).Value;
        decisionPayload.GetProperty("CorrelationId").GetString().Should().Be("corr-1");

        var moved = bus.Published.Find(e => e.Type == SanguoTokenMoved.EventType);
        moved.Should().NotBeNull();
        var movedPayload = ((JsonElementEventData)moved!.Data!).Value;
        movedPayload.GetProperty("FromIndex").GetInt32().Should().Be(0);
        var toIndex = movedPayload.GetProperty("ToIndex").GetInt32();
        toIndex.Should().Be(6);
        toIndex.Should().BeGreaterOrEqualTo(0);
        toIndex.Should().BeLessThan(totalPositions);
        movedPayload.GetProperty("Steps").GetInt32().Should().Be(6);
        movedPayload.GetProperty("PassedStart").GetBoolean().Should().BeFalse();
        movedPayload.GetProperty("CorrelationId").GetString().Should().Be("corr-1");
    }

    // ACC:T17.6
    [Fact]
    [Trait("acceptance", "ACC:T17.6")]
    public async Task ShouldWrapTokenMove_WhenAiMovesPastBoardEnd()
    {
        const int totalPositions = 10;
        const int fromIndex = 9;
        const int steps = 6;
        var expectedToIndex = (fromIndex + steps) % totalPositions;

        var bus = new CapturingEventBus();
        var rules = SanguoEconomyRules.Default;

        var ai = new SanguoPlayer(playerId: "ai-1", money: 0m, positionIndex: fromIndex, economyRules: rules);
        var boardState = new SanguoBoardState(
            players: new[] { ai },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var treasury = new SanguoTreasury();
        var economy = new SanguoEconomyManager(bus);
        var policy = new SpyAiDecisionPolicy();
        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            aiDecisionPolicy: policy,
            rng: new RangeAwareFixedRng(diceValue: steps, nextDouble: 0.0),
            totalPositionsHint: totalPositions);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "ai-1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-1",
            causationId: null);

        var moved = bus.Published.Find(e => e.Type == SanguoTokenMoved.EventType);
        moved.Should().NotBeNull();
        var payload = ((JsonElementEventData)moved!.Data!).Value;
        payload.GetProperty("FromIndex").GetInt32().Should().Be(fromIndex);
        payload.GetProperty("Steps").GetInt32().Should().Be(steps);
        payload.GetProperty("ToIndex").GetInt32().Should().Be(expectedToIndex);
        payload.GetProperty("ToIndex").GetInt32().Should().BeGreaterOrEqualTo(0);
        payload.GetProperty("ToIndex").GetInt32().Should().BeLessThan(totalPositions);
        payload.GetProperty("PassedStart").GetBoolean().Should().BeTrue();
    }

    // ACC:T17.6
    [Fact]
    [Trait("acceptance", "ACC:T17.6")]
    public async Task ShouldNotPublishDiceOrTokenMoved_WhenTotalPositionsNotConfigured()
    {
        var bus = new CapturingEventBus();
        var rules = SanguoEconomyRules.Default;

        var ai = new SanguoPlayer(playerId: "ai-1", money: 0m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(
            players: new[] { ai },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var treasury = new SanguoTreasury();
        var economy = new SanguoEconomyManager(bus);
        var policy = new SpyAiDecisionPolicy();
        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            aiDecisionPolicy: policy,
            rng: new RangeAwareFixedRng(diceValue: 6, nextDouble: 0.0),
            totalPositionsHint: 0);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "ai-1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-1",
            causationId: null);

        bus.Published.Should().Contain(e => e.Type == SanguoAiDecisionMade.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoDiceRolled.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoTokenMoved.EventType);

        ai.PositionIndex.Should().Be(0);
    }

    // ACC:T17.12
    [Fact]
    [Trait("acceptance", "ACC:T17.12")]
    public async Task ShouldAdvanceAtLeast200TurnsWithoutException_WhenUsingOnlyAiPlayers()
    {
        var bus = new CapturingEventBus();
        var rules = SanguoEconomyRules.Default;

        var ai1 = new SanguoPlayer(playerId: "ai-1", money: 0m, positionIndex: 0, economyRules: rules);
        var ai2 = new SanguoPlayer(playerId: "ai-2", money: 0m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(
            players: new[] { ai1, ai2 },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var treasury = new SanguoTreasury();
        var economy = new SanguoEconomyManager(bus);
        var mgr = new SanguoTurnManager(
            bus,
            economy,
            boardState,
            treasury,
            rng: new RangeAwareFixedRng(diceValue: 6, nextDouble: 1.0),
            totalPositionsHint: 10,
            quarterEnvironmentEventTriggerChance: 0.0);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "ai-1", "ai-2" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-1",
            causationId: null);

        const int turns = 200;
        for (var i = 0; i < turns; i++)
        {
            await mgr.AdvanceTurnAsync(correlationId: $"corr-{i + 2}", causationId: $"cmd-{i + 1}");
        }

        var advancedEvents = bus.Published.FindAll(e => e.Type == SanguoGameTurnAdvanced.EventType);
        advancedEvents.Should().HaveCount(turns);

        static int ToDayNumber(int year, int month, int day)
        {
            var y = (year - 1) * SanguoCalendarDate.MonthsPerYear * SanguoCalendarDate.DaysPerMonth;
            var m = (month - 1) * SanguoCalendarDate.DaysPerMonth;
            var d = day - 1;
            return y + m + d;
        }

        var dateNumbers = new int[advancedEvents.Count];
        var activePlayers = new string[advancedEvents.Count];
        var turnNumbers = new int[advancedEvents.Count];
        for (var i = 0; i < advancedEvents.Count; i++)
        {
            var payload = ((JsonElementEventData)advancedEvents[i].Data!).Value;
            var year = payload.GetProperty("Year").GetInt32();
            var month = payload.GetProperty("Month").GetInt32();
            var day = payload.GetProperty("Day").GetInt32();

            dateNumbers[i] = ToDayNumber(year, month, day);
            activePlayers[i] = payload.GetProperty("ActivePlayerId").GetString() ?? "";
            turnNumbers[i] = payload.GetProperty("TurnNumber").GetInt32();
        }

        for (var i = 1; i < dateNumbers.Length; i++)
            dateNumbers[i].Should().Be(dateNumbers[i - 1] + 1);

        turnNumbers[0].Should().Be(2);
        turnNumbers[^1].Should().Be(turns + 1);

        activePlayers.Should().OnlyContain(x => x == "ai-1" || x == "ai-2");
        for (var i = 1; i < activePlayers.Length; i++)
            activePlayers[i].Should().NotBe(activePlayers[i - 1]);

        ai1.IsEliminated.Should().BeFalse();
        ai2.IsEliminated.Should().BeFalse();
    }

    private sealed class CapturingEventBus : IEventBus
    {
        public List<DomainEvent> Published { get; } = new();

        public Task PublishAsync(DomainEvent evt)
        {
            Published.Add(evt);
            return Task.CompletedTask;
        }

        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => new DummySubscription();

        private sealed class DummySubscription : IDisposable
        {
            public void Dispose()
            {
            }
        }
    }

    private sealed class ThrowingEventBus : IEventBus
    {
        public Task PublishAsync(DomainEvent evt) => throw new InvalidOperationException("publish failed");
        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => new DummySubscription();

        private sealed class DummySubscription : IDisposable
        {
            public void Dispose()
            {
            }
        }
    }

    private sealed class CapturingErrorReporter : IErrorReporter
    {
        public sealed record Entry(string Level, string Message, IReadOnlyDictionary<string, string> Context);

        public List<Entry> Messages { get; } = new();

        public void CaptureMessage(string level, string message, IReadOnlyDictionary<string, string>? context = null)
        {
            Messages.Add(new Entry(level, message, context ?? new Dictionary<string, string>()));
        }

        public void CaptureException(string message, Exception ex, IReadOnlyDictionary<string, string>? context = null)
        {
            Messages.Add(new Entry("exception", message, context ?? new Dictionary<string, string>()));
        }
    }

    private sealed class SpyAiDecisionPolicy : ISanguoAiDecisionPolicy
    {
        public bool Seen { get; private set; }
        public Type? SeenSelfType { get; private set; }

        public SanguoAiDecision Decide(ISanguoPlayerView self)
        {
            Seen = true;
            SeenSelfType = self.GetType();
            return new SanguoAiDecision(SanguoAiDecisionType.RollDice);
        }
    }

    private sealed class RangeAwareFixedRng : IRandomNumberGenerator
    {
        private readonly int _diceValue;
        private readonly double _nextDouble;

        public RangeAwareFixedRng(int diceValue, double nextDouble)
        {
            _diceValue = diceValue;
            _nextDouble = nextDouble;
        }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            if (minInclusive == 1 && maxExclusive == 7)
                return _diceValue;

            return minInclusive;
        }

        public double NextDouble() => _nextDouble;
    }
}
