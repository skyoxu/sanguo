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

namespace Game.Core.Tests.Domain;

public sealed class SanguoSaveLoadEventsTests
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

    private sealed class FlakySaveDataStore : IDataStore
    {
        private readonly Dictionary<string, string> persisted = new(StringComparer.Ordinal);

        public int RemainingSaveFailures { get; set; }

        public FlakySaveDataStore(int remainingSaveFailures)
        {
            RemainingSaveFailures = remainingSaveFailures;
        }

        public Task SaveAsync(string key, string json)
        {
            if (RemainingSaveFailures > 0)
            {
                RemainingSaveFailures--;
                throw new InvalidOperationException("simulated_save_failure");
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

    private static SanguoSaveSnapshot CreateSnapshot(string gameId, int turnNumber)
    {
        return new SanguoSaveSnapshot(
            GameId: gameId,
            TurnNumber: turnNumber,
            ActivePlayerIndex: 0,
            Year: 3,
            Month: 3,
            Day: 9,
            PlayerOrder: new[] { "p1", "ai-1" },
            Players: new[]
            {
                new SanguoSavePlayer("p1", Money: 220m, PositionIndex: 2, IsEliminated: false, OwnedCityIds: new[] { "c1" }),
                new SanguoSavePlayer("ai-1", Money: 180m, PositionIndex: 1, IsEliminated: false, OwnedCityIds: Array.Empty<string>()),
            },
            CityEconomy: new[]
            {
                new SanguoSaveCityEconomy("c1", BasePrice: 70m, BaseToll: 25m),
                new SanguoSaveCityEconomy("c2", BasePrice: 65m, BaseToll: 22m),
            },
            TreasuryMinorUnits: 800,
            ContentPackId: "core_v3",
            ContentPackVersion: 14
        );
    }

    // ACC:T18.5
    [Fact]
    public void ShouldExposeStableEventTypeConstants_WhenSavingAndLoading()
    {
        SanguoGameSaved.EventType.Should().Be("core.sanguo.game.saved");
        SanguoGameLoaded.EventType.Should().Be("core.sanguo.game.loaded");
    }

    // ACC:T18.5
    [Fact]
    public void ShouldHaveNonEmptyDistinctEventTypes_WhenComparingSavedAndLoaded()
    {
        var saved = SanguoGameSaved.EventType;
        var loaded = SanguoGameLoaded.EventType;

        saved.Should().NotBeNullOrWhiteSpace();
        loaded.Should().NotBeNullOrWhiteSpace();
        saved.Should().NotBe(loaded);
        saved.Should().Contain("sanguo");
        loaded.Should().Contain("sanguo");
    }

    // ACC:T88.2
    [Fact]
    [Trait("acceptance", "ACC:T88.2")]
    public async Task ShouldToggleWarningStateForLeaveCampOutcomes_WhenRetryClearsFailure()
    {
        var store = new FlakySaveDataStore(remainingSaveFailures: 1);
        var bus = new RecordingEventBus();
        var service = new SanguoSaveLoadService(bus, store);
        var snapshot = CreateSnapshot(gameId: "g-t88-2", turnNumber: 6);

        Func<Task> firstAttempt = async () => await service.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-t88-2",
            correlationId: "corr-t88-2-1",
            causationId: "camp.leave");

        await firstAttempt.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("simulated_save_failure");

        service.IsSaveWarningActive.Should().BeTrue("failed leave-camp save should trigger warning state");
        service.ConsecutiveSaveFailures.Should().Be(1);
        bus.Published.Should().BeEmpty();

        var slotId = await service.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-t88-2",
            correlationId: "corr-t88-2-2",
            causationId: "camp.leave.retry");

        slotId.Should().Be("slot-t88-2");
        service.IsSaveWarningActive.Should().BeFalse("successful leave-camp retry should clear warning state");
        service.ConsecutiveSaveFailures.Should().Be(0);
        bus.Published.Should().ContainSingle(evt => evt.Type == SanguoGameSaved.EventType);
        var payload = ((JsonElementEventData)bus.Published.Single(evt => evt.Type == SanguoGameSaved.EventType).Data!).Value;
        payload.GetProperty("CausationId").GetString().Should().Be("camp.leave.retry");
    }

    [Fact]
    public async Task ShouldKeepWarningInactive_WhenLeaveCampSaveSucceedsOnFirstAttempt()
    {
        var store = new FlakySaveDataStore(remainingSaveFailures: 0);
        var bus = new RecordingEventBus();
        var service = new SanguoSaveLoadService(bus, store);
        var snapshot = CreateSnapshot(gameId: "g-t88-2-success", turnNumber: 7);

        var slotId = await service.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-t88-2-success",
            correlationId: "corr-t88-2-success",
            causationId: "camp.leave");

        slotId.Should().Be("slot-t88-2-success");
        service.IsSaveWarningActive.Should().BeFalse("successful first leave-camp save is a non-trigger condition");
        service.ConsecutiveSaveFailures.Should().Be(0);
        bus.Published.Should().ContainSingle(evt => evt.Type == SanguoGameSaved.EventType);
        var payload = ((JsonElementEventData)bus.Published.Single(evt => evt.Type == SanguoGameSaved.EventType).Data!).Value;
        payload.GetProperty("CausationId").GetString().Should().Be("camp.leave");
    }
}
