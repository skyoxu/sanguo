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

public sealed class Task57ActionCardOwnershipTransferTests
{
    // ACC:T57.7
    [Fact]
    public async Task GivenTransferOwnershipCard_WhenPlayed_ThenPublishesOwnerChangeAndConsumesCard()
    {
        var cards = BuildTransferCardsCatalog();
        var (manager, bus) = await CreateStartedTurnManagerAsync(cards);
        bus.Published.Clear();

        var ok = await manager.TryPlayHumanActionCardAsync(
            cardId: "ac_city_takeover",
            correlationId: "c-1",
            causationId: "test");

        ok.Should().BeTrue();

        bus.Published.Should().ContainSingle(e => e.Type == SanguoActionCardPlayed.EventType);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoCardLost.EventType);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoCityOwnerChanged.EventType);

        var played = bus.Published.Single(e => e.Type == SanguoActionCardPlayed.EventType);
        var playedPayload = DeserializeEventData<SanguoActionCardPlayed>(played);
        playedPayload.CardId.Should().Be("ac_city_takeover");
        playedPayload.EffectKind.Should().Be("transferOwnership");
        playedPayload.StepDelta.Should().Be(0);
        playedPayload.DurationRounds.Should().Be(1);
        playedPayload.AppliedMultipliersAfter.Should().BeNull();

        var changed = bus.Published.Single(e => e.Type == SanguoCityOwnerChanged.EventType);
        var changedPayload = DeserializeEventData<SanguoCityOwnerChanged>(changed);
        changedPayload.CityId.Should().Be("city_1");
        changedPayload.OldOwnerId.Should().Be("p2");
        changedPayload.NewOwnerId.Should().Be("p1");
        changedPayload.ReasonCode.Should().Be(SanguoCityOwnerChanged.ReasonStolen);

        manager.GetTurnAppliedMultipliersSnapshot("p1").ActionCardStepDelta.Should().Be(0);
    }

    private static T DeserializeEventData<T>(DomainEvent evt)
    {
        evt.Data.Should().NotBeNull();
        evt.Data.Should().BeOfType<JsonElementEventData>();
        var el = ((JsonElementEventData)evt.Data!).Value;
        return JsonSerializer.Deserialize<T>(el.GetRawText())!;
    }

    private static async Task<(SanguoTurnManager manager, CapturingEventBus bus)> CreateStartedTurnManagerAsync(
        SanguoActionCardsCatalog actionCardsCatalog)
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var treasury = new SanguoTreasury();

        var player1 = new SanguoPlayer(playerId: "p1", money: 10000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var player2 = new SanguoPlayer(playerId: "p2", money: 10000m, positionIndex: 2, economyRules: SanguoEconomyRules.Default);

        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["city_1"] = new City(id: "city_1", name: "City 1", regionId: "region_1", basePrice: MoneyValue.FromDecimal(1000m), baseToll: MoneyValue.FromDecimal(100m), positionIndex: 0),
            ["city_2"] = new City(id: "city_2", name: "City 2", regionId: "region_1", basePrice: MoneyValue.FromDecimal(1000m), baseToll: MoneyValue.FromDecimal(100m), positionIndex: 1),
        };

        var snapshot2 = player2.CaptureRollbackSnapshot();
        player2.RestoreRollbackSnapshot(snapshot2 with { OwnedCityIds = new[] { "city_1" } });

        var boardState = new SanguoBoardState(
            players: new[] { player1, player2 },
            citiesById: cities);

        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            totalPositionsHint: 10,
            actionCardsCatalog: actionCardsCatalog);

        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "p2" },
            year: 2026,
            month: 1,
            day: 1,
            correlationId: "c0",
            causationId: null);

        return (manager, bus);
    }

    private static SanguoActionCardsCatalog BuildTransferCardsCatalog()
    {
        return new SanguoActionCardsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Cards: Array.AsReadOnly(new[]
            {
                new SanguoActionCardCatalogEntry(
                    CardId: "ac_city_takeover",
                    NameKey: "card.ac_city_takeover.name",
                    DescriptionKey: "card.ac_city_takeover.desc",
                    EffectKind: "transferOwnership",
                    StepDelta: 0,
                    DurationRounds: 1),
            })
        );
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
