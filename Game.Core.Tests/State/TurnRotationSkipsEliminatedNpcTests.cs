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
using Game.Core.Utilities;
using Xunit;

namespace Game.Core.Tests.State;

public sealed class TurnRotationSkipsEliminatedNpcTests
{
    // ACC:T197.8
    [Fact]
    public async Task ShouldNeverSelectEliminatedNpcAndKeepStateLocked_WhenAdvancingTurnsAfterNpcBankruptcy()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var tollCity = new City(
            id: "c-toll",
            name: "TollCity",
            regionId: "r1",
            basePrice: Money.FromMajorUnits(100),
            baseToll: Money.FromMajorUnits(10),
            positionIndex: 2);
        var cities = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            [tollCity.Id] = tollCity,
        };

        var rules = SanguoEconomyRules.Default;
        var human = new SanguoPlayer(playerId: "p1", money: 500m, positionIndex: 0, economyRules: rules);
        var npc = new SanguoPlayer(playerId: "ai-1", money: 5m, positionIndex: 0, economyRules: rules);
        var secondHuman = new SanguoPlayer(playerId: "p2", money: 500m, positionIndex: 0, economyRules: rules);
        human.TryBuyCity(tollCity, priceMultiplier: 1.0m).Should().BeTrue();

        var treasury = new SanguoTreasury();
        var boardState = new SanguoBoardState(players: new[] { human, npc, secondHuman }, citiesById: cities);
        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new FixedRng(fixedNextInt: 2),
            totalPositionsHint: 10);

        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "ai-1", "p2" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);

        await manager.AdvanceTurnAsync(correlationId: "corr-to-npc", causationId: "cmd-to-npc");
        npc.IsEliminated.Should().BeTrue();

        var afterBankruptcyEventCount = bus.Published.Count;
        var observedActivePlayerIds = new List<string>();

        for (var turn = 0; turn < 4; turn++)
        {
            await manager.AdvanceTurnAsync(correlationId: $"corr-after-bankruptcy-{turn}", causationId: $"cmd-after-bankruptcy-{turn}");
            npc.IsEliminated.Should().BeTrue();
        }

        var postBankruptcyEvents = bus.Published.Skip(afterBankruptcyEventCount).ToList();
        observedActivePlayerIds.AddRange(postBankruptcyEvents.SelectMany(ReadActivePlayerIds));

        postBankruptcyEvents.Should().NotContain(evt => evt.Type == SanguoGameEnded.EventType);
        observedActivePlayerIds.Should().NotContain("ai-1", "an eliminated NPC must stay out of turn lifecycle selection");
        observedActivePlayerIds.Should().Contain(new[] { "p1", "p2" });
        npc.IsEliminated.Should().BeTrue("bankruptcy elimination must stay locked across repeated turn advancement");
    }

    private static IEnumerable<string> ReadActivePlayerIds(DomainEvent evt)
    {
        if (evt.Data is not JsonElementEventData data)
            yield break;

        if (!data.Value.TryGetProperty("ActivePlayerId", out var activePlayerId))
            yield break;

        if (activePlayerId.ValueKind != JsonValueKind.String)
            yield break;

        var value = activePlayerId.GetString();
        if (!string.IsNullOrWhiteSpace(value))
            yield return value;
    }

    private sealed class FixedRng : IRandomNumberGenerator
    {
        private readonly int _fixedNextInt;

        public FixedRng(int fixedNextInt)
        {
            _fixedNextInt = fixedNextInt;
        }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            if (_fixedNextInt < minInclusive)
                return minInclusive;
            if (_fixedNextInt >= maxExclusive)
                return maxExclusive - 1;
            return _fixedNextInt;
        }

        public double NextDouble() => 0.0;
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
