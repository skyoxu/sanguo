using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Tasks;

// ADR refs: ADR-0004, ADR-0005, ADR-0020.
// Overlay ref: docs/architecture/overlays/PRD-SANGUO-V3/08/08-t52-turn-window-and-event-ordering.md.
public sealed class Task88SplitTests
{
    private sealed class RecordingEventBus : IEventBus
    {
        public List<DomainEvent> Published { get; } = new();

        public Task PublishAsync(DomainEvent evt)
        {
            Published.Add(evt);
            return Task.CompletedTask;
        }

        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => new NoopSubscription();

        private sealed class NoopSubscription : IDisposable
        {
            public void Dispose()
            {
            }
        }
    }

    private sealed class SequencedSaveDataStore : IDataStore
    {
        private readonly Queue<SaveOutcome> savePlan;
        private readonly Dictionary<string, string> persisted = new(StringComparer.Ordinal);

        public SequencedSaveDataStore(params SaveOutcome[] savePlan)
        {
            this.savePlan = new Queue<SaveOutcome>(savePlan);
        }

        public List<SaveAttempt> SaveAttempts { get; } = new();

        public Task SaveAsync(string key, string json)
        {
            var attemptNumber = SaveAttempts.Count + 1;
            SaveAttempts.Add(new SaveAttempt(key, json, attemptNumber));

            if (savePlan.Count > 0)
            {
                var outcome = savePlan.Dequeue();
                if (outcome.Exception is not null)
                {
                    throw outcome.Exception;
                }
            }

            persisted[key] = json;
            return Task.CompletedTask;
        }

        public Task<string?> LoadAsync(string key)
        {
            persisted.TryGetValue(key, out var value);
            return Task.FromResult<string?>(value);
        }

        public Task DeleteAsync(string key)
        {
            persisted.Remove(key);
            return Task.CompletedTask;
        }
    }

    private sealed record SaveAttempt(string Key, string Payload, int AttemptNumber);

    private sealed record SaveOutcome(Exception? Exception)
    {
        public static SaveOutcome Success() => new((Exception?)null);

        public static SaveOutcome Fail(string message) => new(new InvalidOperationException(message));
    }

    private static SanguoSaveSnapshot CreateSnapshot(string gameId, int turnNumber)
    {
        return new SanguoSaveSnapshot(
            GameId: gameId,
            TurnNumber: turnNumber,
            ActivePlayerIndex: 0,
            Year: 3,
            Month: 10,
            Day: 18,
            PlayerOrder: new[] { "p1", "ai-1" },
            Players: new[]
            {
                new SanguoSavePlayer("p1", Money: 310m, PositionIndex: 3, IsEliminated: false, OwnedCityIds: new[] { "c1" }),
                new SanguoSavePlayer("ai-1", Money: 205m, PositionIndex: 1, IsEliminated: false, OwnedCityIds: Array.Empty<string>()),
            },
            CityEconomy: new[]
            {
                new SanguoSaveCityEconomy("c1", BasePrice: 80m, BaseToll: 25m),
                new SanguoSaveCityEconomy("c2", BasePrice: 60m, BaseToll: 20m),
            },
            TreasuryMinorUnits: 1200,
            ContentPackId: "core_v3",
            ContentPackVersion: 14
        );
    }

    private static JsonElement ReadPayload(DomainEvent evt) => ((JsonElementEventData)evt.Data!).Value;

    // ACC:T88.1
    [Fact]
    [Trait("acceptance", "ACC:T88.1")]
    public async Task ShouldRetryExactlyOnceAndExposeDeterministicEvidence_WhenLeaveCampSaveFailsOnFirstAttempt()
    {
        var store = new SequencedSaveDataStore(
            SaveOutcome.Fail("simulated_save_failure"),
            SaveOutcome.Success());
        var bus = new RecordingEventBus();
        var service = new SanguoSaveLoadService(bus, store);
        var snapshot = CreateSnapshot(gameId: "g-t88-1", turnNumber: 8);

        Func<Task> firstAttempt = async () => await service.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-t88-1",
            correlationId: "corr-t88-1-1",
            causationId: "camp.leave");

        await firstAttempt.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("simulated_save_failure");

        service.IsSaveWarningActive.Should().BeTrue();
        service.ConsecutiveSaveFailures.Should().Be(1);
        bus.Published.Should().BeEmpty();

        var slotId = await service.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-t88-1",
            correlationId: "corr-t88-1-2",
            causationId: "camp.leave.retry");

        slotId.Should().Be("slot-t88-1");
        service.IsSaveWarningActive.Should().BeFalse();
        service.ConsecutiveSaveFailures.Should().Be(0);
        store.SaveAttempts.Select(attempt => attempt.AttemptNumber).Should().Equal(1, 2);
        bus.Published.Should().ContainSingle(evt => evt.Type == SanguoGameSaved.EventType);
        var savedEvent = bus.Published.Single(evt => evt.Type == SanguoGameSaved.EventType);
        var savedPayload = ReadPayload(savedEvent);
        savedPayload.GetProperty("CorrelationId").GetString().Should().Be("corr-t88-1-2");
        savedPayload.GetProperty("CausationId").GetString().Should().Be("camp.leave.retry");
    }

    [Fact]
    public async Task ShouldKeepWarningActiveAndAvoidSuccessEvidence_WhenLeaveCampRetryFailsAgain()
    {
        var store = new SequencedSaveDataStore(
            SaveOutcome.Fail("simulated_save_failure"),
            SaveOutcome.Fail("simulated_save_failure"));
        var bus = new RecordingEventBus();
        var service = new SanguoSaveLoadService(bus, store);
        var snapshot = CreateSnapshot(gameId: "g-t88-2", turnNumber: 9);

        Func<Task> firstAttempt = async () => await service.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-t88-2",
            correlationId: "corr-t88-2-1",
            causationId: "camp.leave");
        Func<Task> retryAttempt = async () => await service.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-t88-2",
            correlationId: "corr-t88-2-2",
            causationId: "camp.leave.retry");

        await firstAttempt.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("simulated_save_failure");
        await retryAttempt.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("simulated_save_failure");

        service.IsSaveWarningActive.Should().BeTrue();
        service.ConsecutiveSaveFailures.Should().Be(2);
        store.SaveAttempts.Select(attempt => attempt.AttemptNumber).Should().Equal(1, 2);
        (await store.LoadAsync("sanguo-save:slot-t88-2")).Should().BeNull();
        bus.Published.Should().BeEmpty();
    }

    // ACC:T88.3
    [Fact]
    [Trait("acceptance", "ACC:T88.3")]
    public async Task ShouldKeepRetryEvidenceScopedToLeaveCampClosure_WhenAutosaveRecoverySucceedsOutsideCampLeave()
    {
        var store = new SequencedSaveDataStore(
            SaveOutcome.Fail("simulated_save_failure"),
            SaveOutcome.Success());
        var bus = new RecordingEventBus();
        var service = new SanguoSaveLoadService(bus, store);
        var snapshot = CreateSnapshot(gameId: "g-t88-3", turnNumber: 10);

        Func<Task> autosaveAttempt = async () => await service.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-t88-3",
            correlationId: "corr-t88-3-1",
            causationId: "camp.autosave");

        await autosaveAttempt.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("simulated_save_failure");

        service.IsSaveWarningActive.Should().BeTrue();
        service.ConsecutiveSaveFailures.Should().Be(1);
        bus.Published.Should().BeEmpty();

        var slotId = await service.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-t88-3",
            correlationId: "corr-t88-3-2",
            causationId: "camp.autosave.retry");

        slotId.Should().Be("slot-t88-3");
        service.IsSaveWarningActive.Should().BeFalse();
        service.ConsecutiveSaveFailures.Should().Be(0);
        store.SaveAttempts.Select(attempt => attempt.AttemptNumber).Should().Equal(1, 2);
        (await store.LoadAsync("sanguo-save:slot-t88-3")).Should().NotBeNullOrWhiteSpace();

        bus.Published.Should().ContainSingle(evt => evt.Type == SanguoGameSaved.EventType);
        var savedEvent = bus.Published.Single(evt => evt.Type == SanguoGameSaved.EventType);
        var savedPayload = ReadPayload(savedEvent);
        savedPayload.GetProperty("CorrelationId").GetString().Should().Be("corr-t88-3-2");
        savedPayload.GetProperty("CausationId").GetString().Should().Be("camp.autosave.retry");
        savedPayload.GetProperty("SaveSlotId").GetString().Should().Be("slot-t88-3");

        bus.Published
            .Where(evt => evt.Type == SanguoGameSaved.EventType)
            .Select(evt => ReadPayload(evt).GetProperty("CausationId").GetString())
            .Should().NotContain(
                "camp.leave.retry",
                "non leave-camp recovery must not satisfy leave-camp split acceptance");
    }
}
