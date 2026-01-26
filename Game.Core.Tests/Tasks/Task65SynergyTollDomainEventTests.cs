using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Game.Core.Utilities;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task65SynergyTollDomainEventTests
{
    // ACC:T65.5
    [Fact]
    public async Task ShouldPublishSynergyTollEventWithBreakdown_WhenLandingOnOwnedCityWithMultipleCitiesInSameRegion()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City 1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10), positionIndex: 2),
            ["c2"] = new City("c2", "City 2", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(20), positionIndex: 4),
        };

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 500m, positionIndex: 0, economyRules: rules);
        var owner = new SanguoPlayer(playerId: "p2", money: 500m, positionIndex: 0, economyRules: rules);
        var players = new[] { p1, owner };
        var payerMoneyBefore = p1.Money.ToDecimal();
        var ownerMoneyBefore = owner.Money.ToDecimal();

        var ownerSnapshot = owner.CaptureRollbackSnapshot();
        owner.RestoreRollbackSnapshot(ownerSnapshot with { OwnedCityIds = new[] { "c1", "c2" } });

        var boardState = new SanguoBoardState(players: players, citiesById: cities);
        var treasury = new SanguoTreasury();

        var rng = new FixedRng(fixedNextInt: 2, fixedNextDouble: 1.0);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: rng,
            totalPositionsHint: 10,
            quarterEnvironmentEventTriggerChance: 0.0);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "p2" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-turn", causationId: "ui.hud.dice.roll");
        var published = bus.Published.Skip(before).ToList();

        published.Count(e => e.Type == SanguoCityTollPaid.EventType).Should().Be(2);
        published.Count(e => e.Type == SanguoCityTollSynergyPaid.EventType).Should().Be(1);

        var synergyEvt = published.Single(e => e.Type == SanguoCityTollSynergyPaid.EventType);
        var payload = ((JsonElementEventData)synergyEvt.Data!).Value;

        payload.GetProperty("GameId").GetString().Should().Be("g1");
        payload.GetProperty("TurnNumber").GetInt32().Should().Be(1);
        payload.GetProperty("PayerId").GetString().Should().Be("p1");
        payload.GetProperty("OwnerId").GetString().Should().Be("p2");
        payload.GetProperty("LandingCityId").GetString().Should().Be("c1");
        payload.GetProperty("RegionId").GetString().Should().Be("r1");
        payload.GetProperty("ExpectedCitiesCount").GetInt32().Should().Be(2);
        payload.GetProperty("PaidCitiesCount").GetInt32().Should().Be(2);
        payload.GetProperty("ExpectedTotalAmount").GetDecimal().Should().Be(30m);
        payload.GetProperty("PaidTotalAmount").GetDecimal().Should().Be(30m);

        var breakdown = payload.GetProperty("Breakdown").EnumerateArray().ToList();
        breakdown.Should().HaveCount(2);

        breakdown.Select(x => x.GetProperty("CityId").GetString()).Should().Equal(new[] { "c1", "c2" });
        breakdown.Select(x => x.GetProperty("Amount").GetDecimal()).Should().Equal(new[] { 10m, 20m });

        foreach (var item in breakdown)
        {
            item.TryGetProperty("AppliedMultipliers", out _).Should().BeTrue("synergy breakdown must carry AppliedMultipliers for UI snapshots");
        }

        var payerMoneyAfter = p1.Money.ToDecimal();
        var ownerMoneyAfter = owner.Money.ToDecimal();
        (payerMoneyBefore - payerMoneyAfter).Should().Be(30m);
        (ownerMoneyAfter - ownerMoneyBefore).Should().Be(30m);
    }

    // ACC:T65.5
    [Fact]
    public async Task ShouldNotPublishSynergyTollEvent_WhenLandingOnOwnedCityWithSingleCityInSameRegion()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City 1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10), positionIndex: 2),
        };

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 500m, positionIndex: 0, economyRules: rules);
        var owner = new SanguoPlayer(playerId: "p2", money: 500m, positionIndex: 0, economyRules: rules);
        var players = new[] { p1, owner };

        var ownerSnapshot = owner.CaptureRollbackSnapshot();
        owner.RestoreRollbackSnapshot(ownerSnapshot with { OwnedCityIds = new[] { "c1" } });

        var boardState = new SanguoBoardState(players: players, citiesById: cities);
        var treasury = new SanguoTreasury();

        var rng = new FixedRng(fixedNextInt: 2, fixedNextDouble: 1.0);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: rng,
            totalPositionsHint: 10,
            quarterEnvironmentEventTriggerChance: 0.0);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "p2" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-turn", causationId: "ui.hud.dice.roll");
        var published = bus.Published.Skip(before).ToList();

        published.Count(e => e.Type == SanguoCityTollPaid.EventType).Should().Be(1);
        published.Count(e => e.Type == SanguoCityTollSynergyPaid.EventType).Should().Be(0);
    }

    // ACC:T65.3
    [Fact]
    public async Task ShouldNotPublishSynergyTollEvent_WhenSynergyTollIsBypassedByPolicy()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City 1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10), positionIndex: 2),
            ["c2"] = new City("c2", "City 2", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(20), positionIndex: 4),
        };

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 500m, positionIndex: 0, economyRules: rules);
        var owner = new SanguoPlayer(playerId: "p2", money: 500m, positionIndex: 0, economyRules: rules);
        var players = new[] { p1, owner };

        var ownerSnapshot = owner.CaptureRollbackSnapshot();
        owner.RestoreRollbackSnapshot(ownerSnapshot with { OwnedCityIds = new[] { "c1", "c2" } });

        var boardState = new SanguoBoardState(players: players, citiesById: cities);
        var treasury = new SanguoTreasury();

        var rng = new FixedRng(fixedNextInt: 2, fixedNextDouble: 1.0);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            regionSynergyTollBypassPolicy: new AlwaysBypassSynergyTollPolicy(),
            rng: rng,
            totalPositionsHint: 10,
            quarterEnvironmentEventTriggerChance: 0.0);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "p2" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var before = bus.Published.Count;
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-turn", causationId: "ui.hud.dice.roll");
        var published = bus.Published.Skip(before).ToList();

        published.Count(e => e.Type == SanguoCityTollPaid.EventType).Should().Be(0);
        published.Count(e => e.Type == SanguoCityTollSynergyPaid.EventType).Should().Be(0);
    }

    // ACC:T65.4
    [Fact]
    public async Task ShouldThrowAndNotPublishSynergyTollEvent_WhenSynergyInputsAreCorrupted()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City 1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10), positionIndex: 2),
            ["c2"] = new City("c2", "City 2", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(20), positionIndex: 4),
        };

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 500m, positionIndex: 0, economyRules: rules);
        var owner = new SanguoPlayer(playerId: "p2", money: 500m, positionIndex: 0, economyRules: rules);
        var players = new[] { p1, owner };

        var ownerSnapshot = owner.CaptureRollbackSnapshot();
        owner.RestoreRollbackSnapshot(ownerSnapshot with { OwnedCityIds = new[] { "c1", "c2" } });

        var boardState = new SanguoBoardState(players: players, citiesById: cities);
        var treasury = new SanguoTreasury();

        var rng = new FixedRng(fixedNextInt: 2, fixedNextDouble: 1.0);
        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: rng,
            totalPositionsHint: 10,
            quarterEnvironmentEventTriggerChance: 0.0);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "p2" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var ownerAfterStart = owner.CaptureRollbackSnapshot();
        owner.RestoreRollbackSnapshot(ownerAfterStart with { OwnedCityIds = new[] { "c1", "c2", "missing-city" } });

        var before = bus.Published.Count;
        Func<Task> act = async () => await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-turn", causationId: "ui.hud.dice.roll");
        await act.Should().ThrowAsync<InvalidOperationException>();

        var published = bus.Published.Skip(before).ToList();
        published.Count(e => e.Type == SanguoCityTollPaid.EventType).Should().Be(0);
        published.Count(e => e.Type == SanguoCityTollSynergyPaid.EventType).Should().Be(0);
    }

    private sealed class AlwaysBypassSynergyTollPolicy : ISanguoRegionSynergyTollBypassPolicy
    {
        public bool ShouldBypass(SanguoRegionSynergyTollContext context) => true;
    }

    private sealed class RecordingEventBus : IEventBus
    {
        public List<DomainEvent> Published { get; } = new();

        public Task PublishAsync(DomainEvent evt)
        {
            Published.Add(evt);
            return Task.CompletedTask;
        }

        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => new NoopDisposable();

        private sealed class NoopDisposable : IDisposable
        {
            public void Dispose() { }
        }
    }

    private sealed class FixedRng : IRandomNumberGenerator
    {
        private readonly int _fixedNextInt;
        private readonly double _fixedNextDouble;

        public FixedRng(int fixedNextInt, double fixedNextDouble)
        {
            _fixedNextInt = fixedNextInt;
            _fixedNextDouble = fixedNextDouble;
        }

        public int NextInt(int minInclusive, int maxExclusive) => _fixedNextInt;

        public double NextDouble() => _fixedNextDouble;
    }
}
