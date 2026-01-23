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

namespace Game.Core.Tests.Tasks;

public sealed class Task57ActionCardWindowTests
{
    // ACC:T57.2
    [Fact]
    public void ShouldHaveStableEventType_WhenActionCardIsPlayed()
    {
        SanguoActionCardPlayed.EventType.Should().Be("core.sanguo.action_card.played");
    }

    // ACC:T57.2
    // ACC:T57.3
    // ACC:T57.5
    // ACC:T57.6
    [Fact]
    public async Task GivenActionCardPlayed_WhenPlayingSecondActionCard_ThenSecondPlayRejectedAndStepDeltaNotStacked()
    {
        var cards = BuildDefaultCardsCatalog();
        var (manager, bus) = await CreateStartedTurnManagerAsync(actionCardsCatalog: cards);
        bus.Published.Clear();

        var first = await manager.TryPlayHumanActionCardAsync(
            cardId: "ac_step_down",
            correlationId: "c-1",
            causationId: "test");
        first.Should().BeTrue();

        var second = await manager.TryPlayHumanActionCardAsync(
            cardId: "ac_step_up",
            correlationId: "c-2",
            causationId: "test");
        second.Should().BeFalse("only one action card is allowed per turn in TurnPhase.BeforeRoll");

        bus.Published.Should().ContainSingle(e => e.Type == SanguoActionCardPlayed.EventType);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoActionCardPlayRejected.EventType);

        var played = bus.Published.Single(e => e.Type == SanguoActionCardPlayed.EventType);
        var playedPayload = DeserializeEventData<SanguoActionCardPlayed>(played);
        playedPayload.CardId.Should().Be("ac_step_down");
        playedPayload.EffectKind.Should().Be("economyStepDelta");
        playedPayload.StepDelta.Should().Be(-1);
        playedPayload.DurationRounds.Should().Be(3);
        playedPayload.AppliedMultipliersAfter.Should().NotBeNull();
        playedPayload.AppliedMultipliersAfter!.ActionCardStepDelta.Should().Be(-1);

        var rejected = bus.Published.Single(e => e.Type == SanguoActionCardPlayRejected.EventType);
        var rejectedPayload = DeserializeEventData<SanguoActionCardPlayRejected>(rejected);
        rejectedPayload.ReasonCode.Should().Be(SanguoActionCardPlayRejected.ReasonAlreadyPlayedThisTurn);

        // Explicitly verify that the second attempt did not mutate the turn-scoped step delta state.
        manager.GetTurnAppliedMultipliersSnapshot("p1").ActionCardStepDelta.Should().Be(-1);
    }

    // ACC:T57.4
    // ACC:T57.5
    [Fact]
    public async Task GivenNoActionCardPlayed_WhenRollingDice_ThenNoActionCardEventsAndActionCardDeltaIsZero()
    {
        var cards = BuildDefaultCardsCatalog();
        var (manager, bus) = await CreateStartedTurnManagerAsync(actionCardsCatalog: cards);
        bus.Published.Clear();

        manager.GetTurnAppliedMultipliersSnapshot("p1").ActionCardStepDelta.Should().Be(0);

        await manager.ExecuteHumanRollDiceAndResolveAsync(correlationId: "c-skip-roll", causationId: "test");

        bus.Published.Should().NotContain(e => e.Type == SanguoActionCardPlayed.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoActionCardPlayRejected.EventType);

        manager.GetTurnAppliedMultipliersSnapshot("p1").ActionCardStepDelta.Should().Be(0);
    }

    [Fact]
    public async Task ShouldRejectPlay_WhenCatalogIsMissing()
    {
        var (manager, bus) = await CreateStartedTurnManagerAsync(actionCardsCatalog: null);
        bus.Published.Clear();

        var ok = await manager.TryPlayHumanActionCardAsync(cardId: "any", correlationId: "c-missing", causationId: "test");

        ok.Should().BeFalse();
        var rejected = bus.Published.Single(e => e.Type == SanguoActionCardPlayRejected.EventType);
        var payload = DeserializeEventData<SanguoActionCardPlayRejected>(rejected);
        payload.ReasonCode.Should().Be(SanguoActionCardPlayRejected.ReasonCatalogMissing);
    }

    [Fact]
    public async Task ShouldRejectPlay_WhenCardIdIsUnknown()
    {
        var cards = BuildDefaultCardsCatalog();
        var (manager, bus) = await CreateStartedTurnManagerAsync(actionCardsCatalog: cards);
        bus.Published.Clear();

        var ok = await manager.TryPlayHumanActionCardAsync(cardId: "unknown", correlationId: "c-unknown", causationId: "test");

        ok.Should().BeFalse();
        var rejected = bus.Published.Single(e => e.Type == SanguoActionCardPlayRejected.EventType);
        var payload = DeserializeEventData<SanguoActionCardPlayRejected>(rejected);
        payload.ReasonCode.Should().Be(SanguoActionCardPlayRejected.ReasonUnknownCardId);
    }

    [Fact]
    public async Task ShouldRejectPlay_WhenDiceAlreadyRolledThisTurn()
    {
        var cards = BuildDefaultCardsCatalog();
        var (manager, bus) = await CreateStartedTurnManagerAsync(actionCardsCatalog: cards);
        bus.Published.Clear();

        await manager.ExecuteHumanRollDiceAndResolveAsync(correlationId: "c-roll", causationId: "test");
        bus.Published.Clear();

        var ok = await manager.TryPlayHumanActionCardAsync(cardId: "ac_step_down", correlationId: "c-after-roll", causationId: "test");

        ok.Should().BeFalse();
        var rejected = bus.Published.Single(e => e.Type == SanguoActionCardPlayRejected.EventType);
        var payload = DeserializeEventData<SanguoActionCardPlayRejected>(rejected);
        payload.ReasonCode.Should().Be(SanguoActionCardPlayRejected.ReasonNotBeforeRoll);
    }

    private static T DeserializeEventData<T>(DomainEvent evt)
    {
        evt.Data.Should().NotBeNull();
        evt.Data.Should().BeOfType<JsonElementEventData>();
        var el = ((JsonElementEventData)evt.Data!).Value;
        return JsonSerializer.Deserialize<T>(el.GetRawText())!;
    }

    private static async Task<(SanguoTurnManager manager, CapturingEventBus bus)> CreateStartedTurnManagerAsync(
        SanguoActionCardsCatalog? actionCardsCatalog)
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var treasury = new SanguoTreasury();

        var player = new SanguoPlayer(playerId: "p1", money: 10000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var boardState = new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            totalPositionsHint: 10,
            actionCardsCatalog: actionCardsCatalog);

        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 2026,
            month: 1,
            day: 1,
            correlationId: "c0",
            causationId: null);

        return (manager, bus);
    }

    private static SanguoActionCardsCatalog BuildDefaultCardsCatalog()
    {
        return new SanguoActionCardsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Cards: Array.AsReadOnly(new[]
            {
                new SanguoActionCardCatalogEntry(
                    CardId: "ac_step_down",
                    NameKey: "card.ac_step_down.name",
                    DescriptionKey: "card.ac_step_down.desc",
                    EffectKind: "economyStepDelta",
                    StepDelta: -1,
                    DurationRounds: 3),
                new SanguoActionCardCatalogEntry(
                    CardId: "ac_step_up",
                    NameKey: "card.ac_step_up.name",
                    DescriptionKey: "card.ac_step_up.desc",
                    EffectKind: "economyStepDelta",
                    StepDelta: 2,
                    DurationRounds: 3),
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
