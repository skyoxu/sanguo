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

public sealed class Task84SplitTests
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

    private sealed class RecordingDataStore : IDataStore
    {
        private readonly Dictionary<string, string> store = new(StringComparer.Ordinal);

        public Task SaveAsync(string key, string json)
        {
            store[key] = json;
            return Task.CompletedTask;
        }

        public Task<string?> LoadAsync(string key)
        {
            store.TryGetValue(key, out var payload);
            return Task.FromResult<string?>(payload);
        }

        public Task DeleteAsync(string key)
        {
            store.Remove(key);
            return Task.CompletedTask;
        }
    }

    private static SanguoSaveSnapshot CreateSnapshot(string gameId)
    {
        return new SanguoSaveSnapshot(
            GameId: gameId,
            TurnNumber: 9,
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

    private static async Task TamperReplayTrustHashAsync(RecordingDataStore store, string saveSlotId, string tamperedReplayTrustHash)
    {
        var key = $"sanguo-save:{saveSlotId}";
        var raw = await store.LoadAsync(key);
        raw.Should().NotBeNullOrWhiteSpace();

        using var doc = JsonDocument.Parse(raw!);
        var root = doc.RootElement;
        var snapshot = JsonSerializer.Deserialize<SanguoSaveSnapshot>(root.GetProperty("Snapshot").GetRawText());
        snapshot.Should().NotBeNull();

        var tamperedPayload = JsonSerializer.Serialize(new
        {
            Version = root.GetProperty("Version").GetString(),
            SaveSlotId = root.GetProperty("SaveSlotId").GetString(),
            SavedAtUtc = root.GetProperty("SavedAtUtc").GetDateTimeOffset(),
            Checksum = root.GetProperty("Checksum").GetString(),
            ReplayTrustHash = tamperedReplayTrustHash,
            Snapshot = snapshot!,
        });

        await store.SaveAsync(key, tamperedPayload);
    }

    // ACC:T84.1
    [Fact]
    [Trait("acceptance", "ACC:T84.1")]
    public async Task ShouldEnterDefinedMismatchMode_WhenReplayTrustHashValidationFails()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var service = new SanguoSaveLoadService(bus, store);
        const string saveSlotId = "slot-t84-1";

        await service.SaveGameAsync(
            snapshot: CreateSnapshot("g-t84-1"),
            saveSlotId: saveSlotId,
            correlationId: "corr-save-t84-1",
            causationId: "task84.save");

        await TamperReplayTrustHashAsync(store, saveSlotId, "tampered-trust-hash");
        bus.Published.Clear();

        var loaded = await service.LoadGameAsync(
            saveSlotId: saveSlotId,
            correlationId: "corr-load-t84-1",
            causationId: "task84.load");

        loaded.GameId.Should().Be("g-t84-1");

        var loadedEvent = bus.Published.Single(e => e.Type == SanguoGameLoaded.EventType);
        var loadedPayload = ((JsonElementEventData)loadedEvent.Data!).Value;
        loadedPayload.GetProperty("SaveUntrusted").GetBoolean().Should().BeTrue(
            "mismatch branch should be marked as untrusted before mode policy evaluation");

        var transitionEvent = bus.Published.Single(
            e => e.Type == EventTypes.RunStateTransitioned);
        var transitionPayload = ((JsonElementEventData)transitionEvent.Data!).Value;
        transitionPayload.GetProperty("FromState").GetString().Should().Be("normal");
        transitionPayload.GetProperty("ToState").GetString().Should().Be("replay_mismatch");
        transitionPayload.GetProperty("Reason").GetString().Should().Be("replay_trust_hash_mismatch");
        transitionPayload.GetProperty("SaveSlotId").GetString().Should().Be(saveSlotId);
    }

    // ACC:T84.2
    [Fact]
    [Trait("acceptance", "ACC:T84.2")]
    public async Task ShouldKeepNormalFlowUnchanged_WhenReplayTrustHashValidationSucceeds()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var service = new SanguoSaveLoadService(bus, store);
        const string saveSlotId = "slot-t84-2";

        await service.SaveGameAsync(
            snapshot: CreateSnapshot("g-t84-2"),
            saveSlotId: saveSlotId,
            correlationId: "corr-save-t84-2",
            causationId: "task84.save");

        bus.Published.Clear();

        var loaded = await service.LoadGameAsync(
            saveSlotId: saveSlotId,
            correlationId: "corr-load-t84-2",
            causationId: "task84.load");

        loaded.GameId.Should().Be("g-t84-2");

        var loadedEvent = bus.Published.Single(e => e.Type == SanguoGameLoaded.EventType);
        var loadedPayload = ((JsonElementEventData)loadedEvent.Data!).Value;
        loadedPayload.GetProperty("SaveUntrusted").GetBoolean().Should().BeFalse(
            "non-mismatch branch should remain trusted");

        bus.Published.Should().NotContain(
            e => e.Type == EventTypes.RunStateTransitioned,
            "non-mismatch branch must not enter mismatch mode");

        bus.Published.Should().ContainSingle(
            e => e.Type == SanguoGameLoaded.EventType,
            "normal load flow should stay unchanged for the non-mismatch path");
    }
}
