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
using Xunit;

namespace Game.Core.Tests.State;

public sealed class GameLoopAdvanceTurnGameOverGuardsTests
{
    // ACC:T197.6
    [Fact]
    public async Task ShouldRejectAndKeepTurnState_WhenAdvancingAfterHumanBankruptcyGameOver()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var tollCity = new City("toll", "TollCity", "r1", Money.Zero, Money.FromMajorUnits(10));
        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            [tollCity.Id] = tollCity,
        };

        var rules = SanguoEconomyRules.Default;
        var human = new SanguoPlayer(playerId: "p1", money: 5m, positionIndex: 0, economyRules: rules);
        var npc = new SanguoPlayer(playerId: "ai-1", money: 0m, positionIndex: 0, economyRules: rules);
        var treasury = new SanguoTreasury();

        human.TryPayTollTo(npc, tollCity, tollMultiplier: 1.0m, treasury: treasury).Should().BeTrue();
        human.IsEliminated.Should().BeTrue();

        var boardState = new SanguoBoardState(players: new[] { human, npc }, citiesById: cities);
        var manager = new SanguoTurnManager(bus: bus, economy: economy, boardState: boardState, treasury: treasury);

        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        var beforeGameOverEvents = bus.Published.Count;
        await manager.AdvanceTurnAsync(correlationId: "corr-gameover", causationId: "cmd-gameover");

        var gameOverEvents = bus.Published.Skip(beforeGameOverEvents).ToList();
        gameOverEvents.Should().ContainSingle(evt => evt.Type == SanguoGameEnded.EventType);
        gameOverEvents.Should().NotContain(evt => evt.Type == SanguoGameTurnAdvanced.EventType);

        var eventCountAfterGameOver = bus.Published.Count;
        var turnAdvancedCountAfterGameOver = bus.Published.Count(evt => evt.Type == SanguoGameTurnAdvanced.EventType);

        Func<Task> act = () => manager.AdvanceTurnAsync(correlationId: "corr-after-gameover", causationId: "cmd-after-gameover");

        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("*GameOver*");
        bus.Published.Count.Should().Be(eventCountAfterGameOver);
        bus.Published.Count(evt => evt.Type == SanguoGameTurnAdvanced.EventType).Should().Be(turnAdvancedCountAfterGameOver);
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
            public void Dispose()
            {
            }
        }
    }
}
