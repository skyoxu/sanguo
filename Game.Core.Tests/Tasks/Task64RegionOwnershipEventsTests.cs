using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Services;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task64RegionOwnershipEventsTests
{
    [Fact]
    public async Task GivenRegionOwnershipChanges_WhenApplyingOwnershipChange_ThenPublishCapturedAndLostEvents()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var treasury = new SanguoTreasury();

        var player1 = new SanguoPlayer(playerId: "p1", money: 10000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var player2 = new SanguoPlayer(playerId: "p2", money: 10000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City(id: "c1", name: "City1", regionId: "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m), positionIndex: 1),
            ["c2"] = new City(id: "c2", name: "City2", regionId: "r1", basePrice: MoneyValue.FromDecimal(100m), baseToll: MoneyValue.FromDecimal(10m), positionIndex: 2),
        };

        var boardState = new SanguoBoardState(players: new[] { player1, player2 }, citiesById: cities);

        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            totalPositionsHint: 10);

        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "p2" },
            year: 2026,
            month: 1,
            day: 1,
            correlationId: "c-start",
            causationId: null);

        bus.Published.Clear();

        var captured = await manager.ApplyOwnershipChangeAsync(
            () =>
            {
                var snapshot = player1.CaptureRollbackSnapshot();
                player1.RestoreRollbackSnapshot(snapshot with { OwnedCityIds = new[] { "c1", "c2" } });
                return true;
            },
            triggerCityId: "c2",
            occurredAt: DateTimeOffset.UtcNow,
            correlationId: "c-cap",
            causationId: "test");

        captured.Should().BeTrue();
        bus.Published.Should().ContainSingle(e => e.Type == SanguoRegionCaptured.EventType);

        var capturedEvent = bus.Published.Single(e => e.Type == SanguoRegionCaptured.EventType);
        var capturedPayload = DeserializeEventData<SanguoRegionCaptured>(capturedEvent);
        capturedPayload.RegionId.Should().Be("r1");
        capturedPayload.OwnerId.Should().Be("p1");
        capturedPayload.CityIds.Should().BeEquivalentTo(new[] { "c1", "c2" });

        bus.Published.Clear();

        var lost = await manager.ApplyOwnershipChangeAsync(
            () =>
            {
                var snapshot = player1.CaptureRollbackSnapshot();
                player1.RestoreRollbackSnapshot(snapshot with { OwnedCityIds = Array.Empty<string>() });
                return true;
            },
            triggerCityId: "c1",
            occurredAt: DateTimeOffset.UtcNow,
            correlationId: "c-lost",
            causationId: "test");

        lost.Should().BeTrue();
        bus.Published.Should().ContainSingle(e => e.Type == SanguoRegionLost.EventType);

        var lostEvent = bus.Published.Single(e => e.Type == SanguoRegionLost.EventType);
        var lostPayload = DeserializeEventData<SanguoRegionLost>(lostEvent);
        lostPayload.RegionId.Should().Be("r1");
        lostPayload.OwnerId.Should().Be("p1");
        lostPayload.ReasonCode.Should().Be(SanguoRegionLost.ReasonLostLastCity);
        lostPayload.TriggerCityId.Should().Be("c1");
    }

    private static T DeserializeEventData<T>(DomainEvent evt)
    {
        evt.Data.Should().NotBeNull();
        evt.Data.Should().BeOfType<JsonElementEventData>();
        var el = ((JsonElementEventData)evt.Data!).Value;
        return JsonSerializer.Deserialize<T>(el.GetRawText())!;
    }

    private sealed class CapturingEventBus : IEventBus
    {
        public List<DomainEvent> Published { get; } = new();

        public Task PublishAsync(DomainEvent evt)
        {
            Published.Add(evt);
            return Task.CompletedTask;
        }

        public IDisposable Subscribe(Func<DomainEvent, Task> handler)
            => throw new NotSupportedException();
    }
}
