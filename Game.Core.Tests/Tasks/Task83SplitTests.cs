using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task83SplitTests
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
        private readonly Dictionary<string, string> _store = new(StringComparer.Ordinal);

        public Task SaveAsync(string key, string json)
        {
            _store[key] = json;
            return Task.CompletedTask;
        }

        public Task<string?> LoadAsync(string key)
        {
            _store.TryGetValue(key, out var payload);
            return Task.FromResult<string?>(payload);
        }

        public Task DeleteAsync(string key)
        {
            _store.Remove(key);
            return Task.CompletedTask;
        }
    }

    private static SanguoSaveSnapshot CreateSnapshot(string gameId)
    {
        return new SanguoSaveSnapshot(
            GameId: gameId,
            TurnNumber: 8,
            ActivePlayerIndex: 0,
            Year: 3,
            Month: 9,
            Day: 17,
            PlayerOrder: new[] { "p1", "ai-1" },
            Players: new[]
            {
                new SanguoSavePlayer("p1", Money: 300m, PositionIndex: 3, IsEliminated: false, OwnedCityIds: new[] { "c1" }),
                new SanguoSavePlayer("ai-1", Money: 200m, PositionIndex: 1, IsEliminated: false, OwnedCityIds: Array.Empty<string>()),
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

    private static string ComputeReplayTrustHash(SanguoSaveSnapshot snapshot)
    {
        var canonicalSnapshotJson = JsonSerializer.Serialize(snapshot);
        var bytes = Encoding.UTF8.GetBytes(canonicalSnapshotJson);
        var hash = SHA256.HashData(bytes);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    // ACC:T83.1
    [Fact]
    public async Task ShouldPersistReplayTrustHash_WhenSavingSnapshotForReplayEvidence()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var service = new SanguoSaveLoadService(bus, store);
        var snapshot = CreateSnapshot(gameId: "g-t83-1");
        var expectedReplayTrustHash = ComputeReplayTrustHash(snapshot);

        _ = await service.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-t83-1",
            correlationId: "corr-save-t83-1",
            causationId: "task83.save");

        var persisted = await store.LoadAsync("sanguo-save:slot-t83-1");
        persisted.Should().NotBeNullOrWhiteSpace();

        using var doc = JsonDocument.Parse(persisted!);
        var root = doc.RootElement;

        root.TryGetProperty("ReplayTrustHash", out var replayTrustHash)
            .Should()
            .BeTrue("replay trust evidence must be stored in save payload for deterministic certification");

        replayTrustHash.GetString()
            .Should()
            .Be(expectedReplayTrustHash, "replay trust hash should be computed from deterministic snapshot content");
    }

    // ACC:T83.2
    [Fact]
    public async Task ShouldPublishSaveUntrusted_WhenReplayTrustHashValidationFails()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var service = new SanguoSaveLoadService(bus, store);
        var snapshot = CreateSnapshot(gameId: "g-t83-2");
        const string saveSlotId = "slot-t83-2";
        var key = $"sanguo-save:{saveSlotId}";

        _ = await service.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: saveSlotId,
            correlationId: "corr-save-t83-2",
            causationId: "task83.save");

        var raw = await store.LoadAsync(key);
        raw.Should().NotBeNullOrWhiteSpace();

        using (var doc = JsonDocument.Parse(raw!))
        {
            var root = doc.RootElement;
            var tamperedPayload = JsonSerializer.Serialize(new
            {
                Version = root.GetProperty("Version").GetString(),
                SaveSlotId = root.GetProperty("SaveSlotId").GetString(),
                SavedAtUtc = root.GetProperty("SavedAtUtc").GetDateTimeOffset(),
                Checksum = root.GetProperty("Checksum").GetString(),
                ReplayTrustHash = "tampered-trust-hash",
                Snapshot = snapshot,
            });

            await store.SaveAsync(key, tamperedPayload);
        }

        bus.Published.Clear();

        var loaded = await service.LoadGameAsync(
            saveSlotId: saveSlotId,
            correlationId: "corr-load-t83-2",
            causationId: "task83.load");

        loaded.GameId.Should().Be("g-t83-2");

        var loadedEvent = bus.Published.Single(e => e.Type == SanguoGameLoaded.EventType);
        var loadedPayload = ((JsonElementEventData)loadedEvent.Data!).Value;

        loadedPayload.TryGetProperty("SaveUntrusted", out var saveUntrusted)
            .Should()
            .BeTrue("trust-hash mismatch path must emit save_untrusted evidence");

        saveUntrusted.GetBoolean()
            .Should()
            .BeTrue("trust-hash mismatch should mark this run context as untrusted for replay certification");
    }

    // ACC:T83.3
    [Fact]
    public async Task ShouldKeepSaveTrusted_WhenReplayTrustHashValidationSucceeds()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var service = new SanguoSaveLoadService(bus, store);
        var snapshot = CreateSnapshot(gameId: "g-t83-3");

        _ = await service.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-t83-3",
            correlationId: "corr-save-t83-3",
            causationId: "task83.save");

        bus.Published.Clear();

        var loaded = await service.LoadGameAsync(
            saveSlotId: "slot-t83-3",
            correlationId: "corr-load-t83-3",
            causationId: "task83.load");

        loaded.GameId.Should().Be("g-t83-3");

        var loadedEvent = bus.Published.Single(e => e.Type == SanguoGameLoaded.EventType);
        var loadedPayload = ((JsonElementEventData)loadedEvent.Data!).Value;

        loadedPayload.TryGetProperty("SaveUntrusted", out var saveUntrusted)
            .Should()
            .BeTrue("trusted replay path should publish explicit trusted marker");

        saveUntrusted.GetBoolean()
            .Should()
            .BeFalse("matching replay trust hash must keep the save in trusted state");
    }
}
