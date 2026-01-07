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
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class PlayerEliminationTests
{
    // ACC:T26.2
    [Fact]
    public async Task ShouldPublishGameEndedAndStopTurnRotation_WhenHumanEliminatedByToll()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var tollCity = new City("toll", "TollCity", "r1", Money.Zero, Money.FromMajorUnits(10));
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { [tollCity.Id] = tollCity };

        var rules = SanguoEconomyRules.Default;
        var human = new SanguoPlayer(playerId: "p1", money: 5m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: "ai-1", money: 0m, positionIndex: 0, economyRules: rules);

        var treasury = new SanguoTreasury();
        human.TryPayTollTo(ai, tollCity, tollMultiplier: 1.0m, treasury: treasury).Should().BeTrue();
        ai.Money.Should().Be(Money.FromDecimal(5m));
        human.Money.Should().Be(Money.Zero);
        treasury.MinorUnits.Should().Be(0);
        human.IsEliminated.Should().BeTrue();

        var boardState = new SanguoBoardState(players: new[] { human, ai }, citiesById: cities);
        var mgr = new SanguoTurnManager(bus: bus, economy: economy, boardState: boardState, treasury: treasury);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var before = bus.Published.Count;
        await mgr.AdvanceTurnAsync(correlationId: "corr-advance", causationId: "cmd-advance");

        var published = bus.Published.Skip(before).ToList();
        published.Should().Contain(e => e.Type == SanguoGameEnded.EventType);
        published.Should().NotContain(e => e.Type == SanguoGameTurnEnded.EventType);

        var ended = published.Single(e => e.Type == SanguoGameEnded.EventType);
        ended.Data.Should().BeOfType<JsonElementEventData>();
        JsonElement endedPayload = ((JsonElementEventData)ended.Data!).Value;
        endedPayload.GetProperty("EndReason").GetString().Should().Be("human_eliminated");

        var afterFirstAdvance = bus.Published.Count;
        Func<Task> act = () => mgr.AdvanceTurnAsync(correlationId: "corr-advance-2", causationId: "cmd-advance-2");
        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("*GameOver: EndReason=human_eliminated*");
        bus.Published.Count.Should().Be(afterFirstAdvance);
    }

    // ACC:T26.3
    [Fact]
    public async Task ShouldNotEndGameButShouldPruneAiAndUnownCities_WhenAiEliminatedByToll()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var ownedCity = new City("owned1", "OwnedCity", "r1", Money.FromMajorUnits(10), Money.FromMajorUnits(1));
        var tollCity = new City("toll", "TollCity", "r1", Money.Zero, Money.FromMajorUnits(10));
        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            [ownedCity.Id] = ownedCity,
            [tollCity.Id] = tollCity,
        };

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: "ai-1", money: 15m, positionIndex: 0, economyRules: rules);
        var p2 = new SanguoPlayer(playerId: "p2", money: 0m, positionIndex: 0, economyRules: rules);

        ai.TryBuyCity(ownedCity, priceMultiplier: 1.0m).Should().BeTrue();
        ai.OwnedCityIds.Should().Contain(ownedCity.Id);

        var treasury = new SanguoTreasury();
        ai.TryPayTollTo(p1, tollCity, tollMultiplier: 1.0m, treasury: treasury).Should().BeTrue();
        p1.Money.Should().Be(Money.FromDecimal(5m));
        ai.Money.Should().Be(Money.Zero);
        treasury.MinorUnits.Should().Be(0);
        ai.IsEliminated.Should().BeTrue();
        ai.OwnedCityIds.Should().BeEmpty();

        var boardState = new SanguoBoardState(players: new[] { p1, ai, p2 }, citiesById: cities);
        var mgr = new SanguoTurnManager(bus: bus, economy: economy, boardState: boardState, treasury: treasury);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1", "p2" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var before = bus.Published.Count;
        await mgr.AdvanceTurnAsync(correlationId: "corr-advance", causationId: "cmd-advance");

        var published = bus.Published.Skip(before).ToList();
        published.Should().NotContain(e => e.Type == SanguoGameEnded.EventType);

        var advanced = published.Single(e => e.Type == SanguoGameTurnAdvanced.EventType);
        advanced.Data.Should().BeOfType<JsonElementEventData>();
        JsonElement advancedPayload = ((JsonElementEventData)advanced.Data!).Value;
        advancedPayload.GetProperty("ActivePlayerId").GetString().Should().Be("p2");

        boardState.TryGetOwnerOfCity(ownedCity.Id, out var owner).Should().BeFalse();
        owner.Should().BeNull();

        for (var i = 0; i < 4; i++)
        {
            var stepBefore = bus.Published.Count;
            await mgr.AdvanceTurnAsync(correlationId: $"corr-advance-{i + 2}", causationId: $"cmd-advance-{i + 2}");

            var stepPublished = bus.Published.Skip(stepBefore).ToList();
            stepPublished.Should().NotContain(e => e.Type == SanguoGameEnded.EventType);

            var stepAdvanced = stepPublished.Single(e => e.Type == SanguoGameTurnAdvanced.EventType);
            JsonElement stepAdvancedPayload = ((JsonElementEventData)stepAdvanced.Data!).Value;
            var stepActive = stepAdvancedPayload.GetProperty("ActivePlayerId").GetString();

            stepActive.Should().NotBe("ai-1");
            stepActive.Should().BeOneOf("p1", "p2");
        }
    }

    // ACC:T26.4
    [Fact]
    public async Task ShouldReleaseOwnedCities_WhenAiEliminatedEvenIfOwnershipNotCleared()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var ownedCity = new City("owned1", "OwnedCity", "r1", Money.FromMajorUnits(10), Money.FromMajorUnits(1));
        var cities = new Dictionary<string, City>(StringComparer.Ordinal) { [ownedCity.Id] = ownedCity };

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: rules);
        var ai = new SanguoPlayer(playerId: "ai-1", money: 20m, positionIndex: 0, economyRules: rules);
        var p2 = new SanguoPlayer(playerId: "p2", money: 0m, positionIndex: 0, economyRules: rules);

        ai.TryBuyCity(ownedCity, priceMultiplier: 1.0m).Should().BeTrue();
        var snap = ai.CaptureRollbackSnapshot();
        ai.RestoreRollbackSnapshot(snap with { IsEliminated = true });
        ai.IsEliminated.Should().BeTrue();
        ai.OwnedCityIds.Should().Contain(ownedCity.Id);

        var treasury = new SanguoTreasury();
        var boardState = new SanguoBoardState(players: new[] { p1, ai, p2 }, citiesById: cities);
        var mgr = new SanguoTurnManager(bus: bus, economy: economy, boardState: boardState, treasury: treasury);

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1", "p2" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var before = bus.Published.Count;
        await mgr.AdvanceTurnAsync(correlationId: "corr-advance", causationId: "cmd-advance");

        var published = bus.Published.Skip(before).ToList();
        published.Should().NotContain(e => e.Type == SanguoGameEnded.EventType);

        var advanced = published.Single(e => e.Type == SanguoGameTurnAdvanced.EventType);
        JsonElement advancedPayload = ((JsonElementEventData)advanced.Data!).Value;
        advancedPayload.GetProperty("ActivePlayerId").GetString().Should().Be("p2");

        boardState.TryGetOwnerOfCity(ownedCity.Id, out var owner).Should().BeFalse();
        owner.Should().BeNull();
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
}
