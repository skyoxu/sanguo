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

namespace Game.Core.Tests.Services;

public sealed class SanguoTurnManagerSaveSnapshotTests
{
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
        private readonly Queue<int> _ints;

        public FixedRng(params int[] ints)
        {
            _ints = new Queue<int>(ints ?? Array.Empty<int>());
        }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            if (_ints.Count == 0)
                return minInclusive;

            var v = _ints.Dequeue();
            if (v < minInclusive)
                return minInclusive;
            if (v >= maxExclusive)
                return maxExclusive - 1;
            return v;
        }

        public double NextDouble() => 0.0;
    }

    private static SanguoTurnManager CreateTurnManager(RecordingEventBus bus, IRandomNumberGenerator rng)
    {
        var economyRules = SanguoEconomyRules.Default;
        var players = new[]
        {
            new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: economyRules),
            new SanguoPlayer(playerId: "ai-1", money: 300m, positionIndex: 0, economyRules: economyRules),
        };

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City-1", "s1", Money.FromDecimal(50m), Money.FromDecimal(20m), positionIndex: 2),
            ["c2"] = new City("c2", "City-2", "s1", Money.FromDecimal(50m), Money.FromDecimal(20m), positionIndex: 4),
        };

        var boardState = new SanguoBoardState(players: players, citiesById: citiesById);
        var treasury = new SanguoTreasury();
        var economy = new SanguoEconomyManager(bus);
        return new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: rng,
            totalPositionsHint: 8);
    }

    [Fact]
    public async Task ExportSaveSnapshot_ShouldCaptureTurnDatePlayersCityEconomyAndTreasury()
    {
        var bus = new RecordingEventBus();
        var tm = CreateTurnManager(bus, rng: new FixedRng(2));

        await tm.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var snapshot = tm.ExportSaveSnapshot();

        snapshot.GameId.Should().Be("g1");
        snapshot.TurnNumber.Should().Be(1);
        snapshot.ActivePlayerIndex.Should().Be(0);
        snapshot.Year.Should().Be(3);
        snapshot.Month.Should().Be(2);
        snapshot.Day.Should().Be(1);
        snapshot.PlayerOrder.Should().BeEquivalentTo(new[] { "p1", "ai-1" }, o => o.WithStrictOrdering());
        snapshot.Players.Should().HaveCount(2);
        snapshot.CityEconomy.Should().HaveCount(2);
        snapshot.TreasuryMinorUnits.Should().Be(0);
    }

    [Fact]
    public async Task RestoreFromSaveSnapshot_ShouldRoundTripState()
    {
        var bus = new RecordingEventBus();
        var tm = CreateTurnManager(bus, rng: new FixedRng(2));

        await tm.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        await tm.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-roll", causationId: "ui.hud.dice.roll");
        var saved = tm.ExportSaveSnapshot();

        await tm.AdvanceTurnAsync(correlationId: "corr-adv", causationId: "ui.hud.dice.roll");
        var changed = tm.ExportSaveSnapshot();
        changed.Should().NotBeEquivalentTo(saved);

        tm.RestoreFromSaveSnapshot(saved);
        var restored = tm.ExportSaveSnapshot();
        restored.Should().BeEquivalentTo(saved);
    }

    [Fact]
    public async Task RestoreFromSaveSnapshot_GivenUnknownCityOwnership_ThenThrowsAndDoesNotMutateState()
    {
        var bus = new RecordingEventBus();
        var tm = CreateTurnManager(bus, rng: new FixedRng(2));

        await tm.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        await tm.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-roll", causationId: "ui.hud.dice.roll");
        var baseline = tm.ExportSaveSnapshot();

        var invalidPlayers = baseline.Players
            .Select(p => p.PlayerId == "p1"
                ? p with { OwnedCityIds = p.OwnedCityIds.Concat(new[] { "unknown-city" }).ToArray() }
                : p)
            .ToArray();

        var invalid = baseline with { Players = invalidPlayers };

        Action act = () => tm.RestoreFromSaveSnapshot(invalid);
        act.Should().Throw<ArgumentException>();

        tm.ExportSaveSnapshot().Should().BeEquivalentTo(baseline);
    }

    [Fact]
    public async Task PublishStateSnapshotAsync_ShouldPublishTurnStartedBeforeActivePlayerStateChanged()
    {
        var bus = new RecordingEventBus();
        var tm = CreateTurnManager(bus, rng: new FixedRng(2));

        await tm.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        bus.Published.Clear();

        await tm.PublishStateSnapshotAsync(correlationId: "corr-snap", causationId: "ui.hud.load");

        bus.Published.Should().NotBeEmpty();
        var types = bus.Published.Select(e => e.Type).ToList();

        types[0].Should().Be(SanguoGameTurnStarted.EventType);
        types.Should().Contain(SanguoPlayerStateChanged.EventType);
        types.Should().Contain(SanguoTokenMoved.EventType);
    }

    [Fact]
    public async Task RestoreFromSaveSnapshot_GivenDuplicatePlayerOrder_ThenThrows()
    {
        var bus = new RecordingEventBus();
        var tm = CreateTurnManager(bus, rng: new FixedRng(2));

        await tm.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var baseline = tm.ExportSaveSnapshot();
        var invalid = baseline with { PlayerOrder = new[] { "p1", "p1" } };

        Action act = () => tm.RestoreFromSaveSnapshot(invalid);
        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public async Task RestoreFromSaveSnapshot_GivenDuplicateCityOwnershipClaims_ThenThrows()
    {
        var bus = new RecordingEventBus();
        var tm = CreateTurnManager(bus, rng: new FixedRng(2));

        await tm.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var baseline = tm.ExportSaveSnapshot();
        var invalidPlayers = new[]
        {
            baseline.Players.Single(p => p.PlayerId == "p1") with { OwnedCityIds = new[] { "c1" } },
            baseline.Players.Single(p => p.PlayerId == "ai-1") with { OwnedCityIds = new[] { "c1" } },
        };

        var invalid = baseline with { Players = invalidPlayers };

        Action act = () => tm.RestoreFromSaveSnapshot(invalid);
        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public async Task RestoreFromSaveSnapshot_GivenUnknownCityEconomyEntry_ThenThrows()
    {
        var bus = new RecordingEventBus();
        var tm = CreateTurnManager(bus, rng: new FixedRng(2));

        await tm.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var baseline = tm.ExportSaveSnapshot();
        var invalidEconomy = baseline.CityEconomy.Concat(new[] { new SanguoSaveCityEconomy("unknown-city", 1m, 1m) }).ToArray();
        var invalid = baseline with { CityEconomy = invalidEconomy };

        Action act = () => tm.RestoreFromSaveSnapshot(invalid);
        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void ExportSaveSnapshot_BeforeStart_ThenThrows()
    {
        var bus = new RecordingEventBus();
        var tm = CreateTurnManager(bus, rng: new FixedRng(2));

        Action act = () => tm.ExportSaveSnapshot();
        act.Should().Throw<InvalidOperationException>();
    }

    [Fact]
    public async Task RestoreFromSaveSnapshot_GivenInvalidTurnNumber_ThenThrows()
    {
        var bus = new RecordingEventBus();
        var tm = CreateTurnManager(bus, rng: new FixedRng(2));

        await tm.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var baseline = tm.ExportSaveSnapshot();
        var invalid = baseline with { TurnNumber = 0 };

        Action act = () => tm.RestoreFromSaveSnapshot(invalid);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public async Task RestoreFromSaveSnapshot_GivenOutOfRangeActivePlayerIndex_ThenThrows()
    {
        var bus = new RecordingEventBus();
        var tm = CreateTurnManager(bus, rng: new FixedRng(2));

        await tm.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var baseline = tm.ExportSaveSnapshot();
        var invalid = baseline with { ActivePlayerIndex = 999 };

        Action act = () => tm.RestoreFromSaveSnapshot(invalid);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public async Task RestoreFromSaveSnapshot_GivenNegativeTreasuryMinorUnits_ThenThrows()
    {
        var bus = new RecordingEventBus();
        var tm = CreateTurnManager(bus, rng: new FixedRng(2));

        await tm.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        var baseline = tm.ExportSaveSnapshot();
        var invalid = baseline with { TreasuryMinorUnits = -1 };

        Action act = () => tm.RestoreFromSaveSnapshot(invalid);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public async Task PublishStateSnapshotAsync_GivenEmptyCorrelationId_ThenThrows()
    {
        var bus = new RecordingEventBus();
        var tm = CreateTurnManager(bus, rng: new FixedRng(2));

        await tm.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ui.menu.start");

        Func<Task> act = async () => await tm.PublishStateSnapshotAsync(correlationId: "", causationId: "ui.hud.load");
        await act.Should().ThrowAsync<ArgumentException>();
    }
}
