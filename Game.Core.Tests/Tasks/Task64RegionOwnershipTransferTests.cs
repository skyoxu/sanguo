using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Services;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Xunit;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;

namespace Game.Core.Tests.Tasks;

public sealed class Task64RegionOwnershipTransferTests
{
    [Fact]
    public async Task GivenTransferOwnership_WhenApplying_ThenPublishesOwnerChangedAndRegionEvents()
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

        var assignCity1 = await manager.TransferCityOwnershipAsync(
            cityId: "c1",
            newOwnerId: "p1",
            reasonCode: SanguoCityOwnerChanged.ReasonBought,
            correlationId: "c-assign-1",
            causationId: "test",
            occurredAt: DateTimeOffset.UtcNow);
        assignCity1.Should().BeTrue();

        var assignCity2 = await manager.TransferCityOwnershipAsync(
            cityId: "c2",
            newOwnerId: "p1",
            reasonCode: SanguoCityOwnerChanged.ReasonBought,
            correlationId: "c-assign-2",
            causationId: "test",
            occurredAt: DateTimeOffset.UtcNow);
        assignCity2.Should().BeTrue();

        bus.Published.Should().Contain(e => e.Type == SanguoCityOwnerChanged.EventType);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoRegionCaptured.EventType);

        bus.Published.Clear();

        var transfer = await manager.TransferCityOwnershipAsync(
            cityId: "c1",
            newOwnerId: "p2",
            reasonCode: SanguoCityOwnerChanged.ReasonStolen,
            correlationId: "c-transfer",
            causationId: "test",
            occurredAt: DateTimeOffset.UtcNow);
        transfer.Should().BeTrue();

        bus.Published.Should().ContainSingle(e => e.Type == SanguoCityOwnerChanged.EventType);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoRegionLost.EventType);

        var ownerChanged = bus.Published.Single(e => e.Type == SanguoCityOwnerChanged.EventType);
        var payload = DeserializeEventData<SanguoCityOwnerChanged>(ownerChanged);
        payload.CityId.Should().Be("c1");
        payload.OldOwnerId.Should().Be("p1");
        payload.NewOwnerId.Should().Be("p2");
        payload.ReasonCode.Should().Be(SanguoCityOwnerChanged.ReasonStolen);
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
