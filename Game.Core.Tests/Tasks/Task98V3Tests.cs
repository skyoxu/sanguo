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

public sealed class Task98V3Tests
{
    private const string ExplainEventType = "core.sanguo.action.explain";

    // ACC:T98.2
    [Fact]
    [Trait("acceptance", "ACC:T98.2")]
    public async Task ShouldRefuseSecondActionAttemptAndKeepTurnStateUnchanged_WhenActionCardWasAlreadyPlayedInSameRound()
    {
        var (manager, bus) = await CreateStartedTurnManagerAsync();
        bus.Published.Clear();

        var firstAttempt = await manager.TryPlayHumanActionCardAsync(
            cardId: "ac_step_down",
            correlationId: "corr-first",
            causationId: "ut.action.first");

        var stateAfterFirst = manager.GetTurnAppliedMultipliersSnapshot("p1");
        var publishedCountBeforeSecond = bus.Published.Count;

        var secondAttempt = await manager.TryPlayHumanActionCardAsync(
            cardId: "ac_step_up",
            correlationId: "corr-second",
            causationId: "ut.action.second");

        var newEvents = bus.Published.Skip(publishedCountBeforeSecond).ToList();
        var stateAfterSecond = manager.GetTurnAppliedMultipliersSnapshot("p1");

        firstAttempt.Should().BeTrue();
        secondAttempt.Should().BeFalse("one-action-per-round must refuse second action attempts in the same round");

        stateAfterFirst.ActionCardStepDelta.Should().Be(-1);
        stateAfterSecond.ActionCardStepDelta.Should().Be(stateAfterFirst.ActionCardStepDelta);

        bus.Published.Count(e => e.Type == SanguoActionCardPlayed.EventType).Should().Be(1);
        newEvents.Should().ContainSingle(e => e.Type == SanguoActionCardPlayRejected.EventType);
        newEvents.Should().NotContain(e => e.Type == SanguoActionCardPlayed.EventType);

        var rejected = newEvents.Single(e => e.Type == SanguoActionCardPlayRejected.EventType);
        var rejectedPayload = DeserializeEventData<SanguoActionCardPlayRejected>(rejected);
        rejectedPayload.ReasonCode.Should().Be(SanguoActionCardPlayRejected.ReasonAlreadyPlayedThisTurn);
    }

    [Fact]
    public async Task ShouldAppendExplanatoryRefusalEntry_WhenSecondActionAttemptIsRefusedInSameRound()
    {
        var (manager, bus) = await CreateStartedTurnManagerAsync();
        bus.Published.Clear();

        var firstAttempt = await manager.TryPlayHumanActionCardAsync(
            cardId: "ac_step_down",
            correlationId: "corr-first",
            causationId: "ut.action.first");

        var publishedCountBeforeSecond = bus.Published.Count;

        var secondAttempt = await manager.TryPlayHumanActionCardAsync(
            cardId: "ac_step_up",
            correlationId: "corr-second",
            causationId: "ut.action.second");

        var secondAttemptEvents = bus.Published.Skip(publishedCountBeforeSecond).ToList();

        firstAttempt.Should().BeTrue();
        secondAttempt.Should().BeFalse();
        secondAttemptEvents.Should().ContainSingle(e => e.Type == SanguoActionCardPlayRejected.EventType);
        secondAttemptEvents.Should().ContainSingle(e => e.Type == ExplainEventType);
        secondAttemptEvents.Should().NotContain(e => e.Type == SanguoActionCardPlayed.EventType);

        var rejected = secondAttemptEvents.Single(e => e.Type == SanguoActionCardPlayRejected.EventType);
        var rejectedPayload = DeserializeEventData<SanguoActionCardPlayRejected>(rejected);
        rejectedPayload.ReasonCode.Should().Be(SanguoActionCardPlayRejected.ReasonAlreadyPlayedThisTurn);
        rejectedPayload.PlayerId.Should().Be("p1");
        rejectedPayload.RoundNumber.Should().Be(1);
        rejectedPayload.TurnNumber.Should().Be(1);
        rejectedPayload.CorrelationId.Should().Be("corr-second");

        var explain = secondAttemptEvents.Single(e => e.Type == ExplainEventType);
        var explainPayload = ((JsonElementEventData)explain.Data!).Value;
        explainPayload.GetProperty("ReasonCode").GetString().Should().Be(SanguoActionCardPlayRejected.ReasonAlreadyPlayedThisTurn);
        explainPayload.GetProperty("ExplainCode").GetString().Should().Be("second_action_refused");
        explainPayload.GetProperty("PlayerId").GetString().Should().Be("p1");
        explainPayload.GetProperty("RoundNumber").GetInt32().Should().Be(1);
        explainPayload.GetProperty("TurnNumber").GetInt32().Should().Be(1);
        explainPayload.GetProperty("CorrelationId").GetString().Should().Be("corr-second");
        explainPayload.GetProperty("CausationId").GetString().Should().Be("ut.action.second");
    }

    private static async Task<(SanguoTurnManager manager, CapturingEventBus bus)> CreateStartedTurnManagerAsync()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var boardState = new SanguoBoardState(
            players: new[]
            {
                new SanguoPlayer(playerId: "p1", money: 10000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default),
            },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            totalPositionsHint: 10,
            actionCardsCatalog: CreateActionCardsCatalog());

        await manager.StartNewGameAsync(
            gameId: "g-task98",
            playerOrder: new[] { "p1" },
            year: 2026,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: "ut.start");

        return (manager, bus);
    }

    private static SanguoActionCardsCatalog CreateActionCardsCatalog()
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
            }));
    }

    private static T DeserializeEventData<T>(DomainEvent evt)
    {
        evt.Data.Should().NotBeNull();
        evt.Data.Should().BeOfType<JsonElementEventData>();
        var json = ((JsonElementEventData)evt.Data!).Value.GetRawText();
        return JsonSerializer.Deserialize<T>(json)!;
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
