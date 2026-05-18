using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Ports;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class SanguoEconomyManagerTollPaymentGuardsAndPublishFailureTests
{
    // ACC:T188.13 ACC:T188.14
    [Fact]
    public async Task ShouldThrowArgumentValidationErrors_WhenTryPayTollAndPublishEventAsyncReceivesInvalidArguments()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var city = new City(
            id: "c1",
            name: "City1",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(10),
            baseToll: Money.FromMajorUnits(10),
            positionIndex: 0);
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };

        var rules = SanguoEconomyRules.Default;
        var owner = new SanguoPlayer(playerId: "owner", money: 100m, positionIndex: 0, economyRules: rules);
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0, economyRules: rules);
        owner.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        await Assert.ThrowsAsync<ArgumentException>(() => economy.TryPayTollAndPublishEventAsync(
            gameId: "",
            turnNumber: 1,
            players: new[] { owner, payer },
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: city.Id,
            tollMultiplier: 1.0m,
            treasury: new SanguoTreasury(),
            correlationId: "corr",
            causationId: null,
            occurredAt: DateTimeOffset.UtcNow));

        await Assert.ThrowsAsync<ArgumentOutOfRangeException>(() => economy.TryPayTollAndPublishEventAsync(
            gameId: "g1",
            turnNumber: 0,
            players: new[] { owner, payer },
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: city.Id,
            tollMultiplier: 1.0m,
            treasury: new SanguoTreasury(),
            correlationId: "corr",
            causationId: null,
            occurredAt: DateTimeOffset.UtcNow));

        await Assert.ThrowsAsync<ArgumentException>(() => economy.TryPayTollAndPublishEventAsync(
            gameId: "g1",
            turnNumber: 1,
            players: new[] { owner, payer },
            citiesById: citiesById,
            payerId: "",
            cityId: city.Id,
            tollMultiplier: 1.0m,
            treasury: new SanguoTreasury(),
            correlationId: "corr",
            causationId: null,
            occurredAt: DateTimeOffset.UtcNow));

        await Assert.ThrowsAsync<ArgumentException>(() => economy.TryPayTollAndPublishEventAsync(
            gameId: "g1",
            turnNumber: 1,
            players: new[] { owner, payer },
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: "",
            tollMultiplier: 1.0m,
            treasury: new SanguoTreasury(),
            correlationId: "corr",
            causationId: null,
            occurredAt: DateTimeOffset.UtcNow));

        await Assert.ThrowsAsync<ArgumentException>(() => economy.TryPayTollAndPublishEventAsync(
            gameId: "g1",
            turnNumber: 1,
            players: new[] { owner, payer },
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: city.Id,
            tollMultiplier: 1.0m,
            treasury: new SanguoTreasury(),
            correlationId: "",
            causationId: null,
            occurredAt: DateTimeOffset.UtcNow));
    }

    [Fact]
    public async Task ShouldReturnFalse_WhenTryPayTollAndPublishEventAsyncHitsCommonGuardConditions()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var city = new City(
            id: "c1",
            name: "City1",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(10),
            baseToll: Money.FromMajorUnits(10),
            positionIndex: 0);
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };

        var rules = SanguoEconomyRules.Default;
        var owner = new SanguoPlayer(playerId: "owner", money: 100m, positionIndex: 0, economyRules: rules);
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0, economyRules: rules);
        owner.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var treasury = new SanguoTreasury();
        var occurredAt = DateTimeOffset.UtcNow;

        (await economy.TryPayTollAndPublishEventAsync(
            gameId: "g1",
            turnNumber: 1,
            players: new[] { owner, payer },
            citiesById: citiesById,
            payerId: "missing",
            cityId: city.Id,
            tollMultiplier: 1.0m,
            treasury: treasury,
            correlationId: "corr",
            causationId: null,
            occurredAt: occurredAt)).Should().BeFalse();

        (await economy.TryPayTollAndPublishEventAsync(
            gameId: "g1",
            turnNumber: 1,
            players: new[] { owner, payer },
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: "missing-city",
            tollMultiplier: 1.0m,
            treasury: treasury,
            correlationId: "corr",
            causationId: null,
            occurredAt: occurredAt)).Should().BeFalse();

        payer.MoveToPosition(positionIndex: 1);
        (await economy.TryPayTollAndPublishEventAsync(
            gameId: "g1",
            turnNumber: 1,
            players: new[] { owner, payer },
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: city.Id,
            tollMultiplier: 1.0m,
            treasury: treasury,
            correlationId: "corr",
            causationId: null,
            occurredAt: occurredAt)).Should().BeFalse();

        payer.MoveToPosition(positionIndex: 0);
        (await economy.TryPayTollAndPublishEventAsync(
            gameId: "g1",
            turnNumber: 1,
            players: new[] { owner, payer },
            citiesById: citiesById,
            payerId: owner.PlayerId,
            cityId: city.Id,
            tollMultiplier: 1.0m,
            treasury: treasury,
            correlationId: "corr",
            causationId: null,
            occurredAt: occurredAt)).Should().BeFalse();

        var ownerSnap = owner.CaptureRollbackSnapshot();
        owner.RestoreRollbackSnapshot(ownerSnap with { IsEliminated = true });
        (await economy.TryPayTollAndPublishEventAsync(
            gameId: "g1",
            turnNumber: 1,
            players: new[] { owner, payer },
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: city.Id,
            tollMultiplier: 1.0m,
            treasury: treasury,
            correlationId: "corr",
            causationId: null,
            occurredAt: occurredAt)).Should().BeFalse();

        var unownedCity = new City(
            id: "c2",
            name: "City2",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(10),
            baseToll: Money.FromMajorUnits(10),
            positionIndex: 0);
        var citiesWithUnowned = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            [city.Id] = city,
            [unownedCity.Id] = unownedCity,
        };
        (await economy.TryPayTollAndPublishEventAsync(
            gameId: "g1",
            turnNumber: 1,
            players: new[] { owner, payer },
            citiesById: citiesWithUnowned,
            payerId: payer.PlayerId,
            cityId: unownedCity.Id,
            tollMultiplier: 1.0m,
            treasury: treasury,
            correlationId: "corr",
            causationId: null,
            occurredAt: occurredAt)).Should().BeFalse();
    }

    [Fact]
    public async Task ShouldThrowInvalidOperationException_WhenTryPayTollAndPublishEventAsyncDetectsCorruptedOwnerResolutionState()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var city = new City(
            id: "c1",
            name: "City1",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(10),
            baseToll: Money.FromMajorUnits(10),
            positionIndex: 0);
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };

        var rules = SanguoEconomyRules.Default;
        var owner1 = new SanguoPlayer(playerId: "owner-1", money: 100m, positionIndex: 0, economyRules: rules);
        var owner2 = new SanguoPlayer(playerId: "owner-2", money: 100m, positionIndex: 0, economyRules: rules);
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0, economyRules: rules);

        var snap1 = owner1.CaptureRollbackSnapshot();
        owner1.RestoreRollbackSnapshot(snap1 with { OwnedCityIds = new[] { city.Id } });
        var snap2 = owner2.CaptureRollbackSnapshot();
        owner2.RestoreRollbackSnapshot(snap2 with { OwnedCityIds = new[] { city.Id } });

        Func<Task> act = () => economy.TryPayTollAndPublishEventAsync(
            gameId: "g1",
            turnNumber: 1,
            players: new[] { owner1, owner2, payer },
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: city.Id,
            tollMultiplier: 1.0m,
            treasury: new SanguoTreasury(),
            correlationId: "corr",
            causationId: null,
            occurredAt: DateTimeOffset.UtcNow);

        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("*Invalid board state while resolving city owner*");
    }

    [Fact]
    public async Task ShouldRollbackAndThrow_WhenTryPayTollAndPublishEventAsyncCannotPublishTollEvent()
    {
        var bus = new AlwaysFailEventBus();
        var economy = new SanguoEconomyManager(bus);

        var city = new City(
            id: "c1",
            name: "City1",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(10),
            baseToll: Money.FromMajorUnits(10),
            positionIndex: 0);
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };

        var rules = SanguoEconomyRules.Default;
        var owner = new SanguoPlayer(playerId: "owner", money: 100m, positionIndex: 0, economyRules: rules);
        var payer = new SanguoPlayer(playerId: "payer", money: 100m, positionIndex: 0, economyRules: rules);
        owner.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var payerSnapshot = payer.CaptureRollbackSnapshot();
        var ownerSnapshot = owner.CaptureRollbackSnapshot();
        var treasury = new SanguoTreasury();
        var treasurySnapshot = treasury.CaptureRollbackSnapshot();

        Func<Task> act = () => economy.TryPayTollAndPublishEventAsync(
            gameId: "g1",
            turnNumber: 1,
            players: new[] { owner, payer },
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: city.Id,
            tollMultiplier: 1.0m,
            treasury: treasury,
            correlationId: "corr",
            causationId: null,
            occurredAt: DateTimeOffset.UtcNow);

        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("*Event publish failed after toll payment*");

        var payerAfter = payer.CaptureRollbackSnapshot();
        payerAfter.Money.Should().Be(payerSnapshot.Money);
        payerAfter.PositionIndex.Should().Be(payerSnapshot.PositionIndex);
        payerAfter.IsEliminated.Should().Be(payerSnapshot.IsEliminated);
        payerAfter.OwnedCityIds.Should().BeEquivalentTo(payerSnapshot.OwnedCityIds);

        var ownerAfter = owner.CaptureRollbackSnapshot();
        ownerAfter.Money.Should().Be(ownerSnapshot.Money);
        ownerAfter.PositionIndex.Should().Be(ownerSnapshot.PositionIndex);
        ownerAfter.IsEliminated.Should().Be(ownerSnapshot.IsEliminated);
        ownerAfter.OwnedCityIds.Should().BeEquivalentTo(ownerSnapshot.OwnedCityIds);
        treasury.CaptureRollbackSnapshot().Should().Be(treasurySnapshot);
    }

    [Fact]
    public async Task ShouldNotThrow_WhenTryPayTollAndPublishEventAsyncFailsToPublishEliminatedAuditEvent()
    {
        var bus = new FailOnlyOnTypeEventBus(SanguoPlayerEliminated.EventType);
        var reporter = new CapturingErrorReporter();
        var economy = new SanguoEconomyManager(bus, reporter);

        var tollCity = new City(
            id: "toll",
            name: "TollCity",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(100),
            baseToll: Money.FromMajorUnits(20),
            positionIndex: 0);
        var ownedCity = new City(
            id: "owned1",
            name: "OwnedCity",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(10),
            baseToll: Money.FromMajorUnits(1),
            positionIndex: 0);
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            [tollCity.Id] = tollCity,
            [ownedCity.Id] = ownedCity,
        };

        var rules = SanguoEconomyRules.Default;
        var owner = new SanguoPlayer(playerId: "owner", money: 200m, positionIndex: 0, economyRules: rules);
        var payer = new SanguoPlayer(playerId: "payer", money: 60m, positionIndex: 0, economyRules: rules);
        owner.TryBuyCity(tollCity, priceMultiplier: 1.0m).Should().BeTrue();
        payer.TryBuyCity(ownedCity, priceMultiplier: 1.0m).Should().BeTrue();

        var treasury = new SanguoTreasury();
        var occurredAt = DateTimeOffset.UtcNow;
        var paid = await economy.TryPayTollAndPublishEventAsync(
            gameId: "g1",
            turnNumber: 1,
            players: new[] { owner, payer },
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: tollCity.Id,
            tollMultiplier: 3.0m,
            treasury: treasury,
            correlationId: "corr",
            causationId: "cmd-1",
            occurredAt: occurredAt);

        paid.Should().BeTrue();
        payer.IsEliminated.Should().BeTrue();
        bus.Published.Should().Contain(e => e.Type == SanguoCityTollPaid.EventType);
        reporter.CapturedExceptions.Should().ContainSingle(e => e.Message == "sanguo.player.eliminated.publish_failed");
    }

    private sealed class RecordingEventBus : IEventBus
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

    private sealed class AlwaysFailEventBus : IEventBus
    {
        public Task PublishAsync(DomainEvent evt) => throw new InvalidOperationException("fail");
        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => new DummySubscription();

        private sealed class DummySubscription : IDisposable
        {
            public void Dispose()
            {
            }
        }
    }

    private sealed class FailOnlyOnTypeEventBus : IEventBus
    {
        private readonly string _failType;
        public List<DomainEvent> Published { get; } = new();

        public FailOnlyOnTypeEventBus(string failType)
        {
            _failType = failType;
        }

        public Task PublishAsync(DomainEvent evt)
        {
            if (string.Equals(evt.Type, _failType, StringComparison.Ordinal))
                throw new InvalidOperationException("fail");

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

    private sealed class CapturingErrorReporter : IErrorReporter
    {
        public List<(string Message, Exception Ex)> CapturedExceptions { get; } = new();

        public void CaptureMessage(string level, string message, IReadOnlyDictionary<string, string>? context = null)
        {
        }

        public void CaptureException(string message, Exception ex, IReadOnlyDictionary<string, string>? context = null)
        {
            CapturedExceptions.Add((message, ex));
        }
    }
}
