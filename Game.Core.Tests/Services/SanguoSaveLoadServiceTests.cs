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

namespace Game.Core.Tests.Services;

internal sealed record RecordingDataStore : IDataStore
{
    private readonly Dictionary<string, string> _dict = new(StringComparer.Ordinal);

    public List<(string Key, string Payload)> Saves { get; } = new();
    public List<string> Loads { get; } = new();
    public List<string> Deletes { get; } = new();

    public Task SaveAsync(string key, string json)
    {
        Saves.Add((key, json));
        _dict[key] = json;
        return Task.CompletedTask;
    }

    public Task<string?> LoadAsync(string key)
    {
        Loads.Add(key);
        _dict.TryGetValue(key, out var v);
        return Task.FromResult<string?>(v);
    }

    public Task DeleteAsync(string key)
    {
        Deletes.Add(key);
        _dict.Remove(key);
        return Task.CompletedTask;
    }
}

internal sealed record FlakySaveDataStore : IDataStore
{
    private readonly Dictionary<string, string> _dict = new(StringComparer.Ordinal);

    public int RemainingSaveFailures { get; set; }

    public int SaveAttempts { get; private set; }

    public FlakySaveDataStore(int remainingSaveFailures)
    {
        RemainingSaveFailures = remainingSaveFailures;
    }

    public Task SaveAsync(string key, string json)
    {
        SaveAttempts++;
        if (RemainingSaveFailures > 0)
        {
            RemainingSaveFailures--;
            throw new InvalidOperationException("simulated_save_failure");
        }

        _dict[key] = json;
        return Task.CompletedTask;
    }

    public Task<string?> LoadAsync(string key)
    {
        _dict.TryGetValue(key, out var v);
        return Task.FromResult<string?>(v);
    }

    public Task DeleteAsync(string key)
    {
        _dict.Remove(key);
        return Task.CompletedTask;
    }
}

public sealed class SanguoSaveLoadServiceTests
{
    // ACC:T184.10
    [Fact]
    public void ShouldThrowArgumentNullException_WhenConstructingWithNullBus()
    {
        var store = new RecordingDataStore();
        Action act = () => _ = new SanguoSaveLoadService(bus: null!, store: store);
        act.Should().Throw<ArgumentNullException>().WithParameterName("bus");
    }

    [Fact]
    public void ShouldThrowArgumentNullException_WhenConstructingWithNullStore()
    {
        var bus = new RecordingEventBus();
        Action act = () => _ = new SanguoSaveLoadService(bus: bus, store: null!);
        act.Should().Throw<ArgumentNullException>().WithParameterName("store");
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

    private static SanguoSaveSnapshot MakeSnapshot(string gameId, int turnNumber, int activePlayerIndex)
    {
        return new SanguoSaveSnapshot(
            GameId: gameId,
            TurnNumber: turnNumber,
            ActivePlayerIndex: activePlayerIndex,
            Year: 3,
            Month: 2,
            Day: 5,
            PlayerOrder: new[] { "p1", "ai-1" },
            Players: new[]
            {
                new SanguoSavePlayer("p1", Money: 250m, PositionIndex: 2, IsEliminated: false, OwnedCityIds: new[] { "c1" }),
                new SanguoSavePlayer("ai-1", Money: 300m, PositionIndex: 1, IsEliminated: false, OwnedCityIds: Array.Empty<string>()),
            },
            CityEconomy: new[]
            {
                new SanguoSaveCityEconomy("c1", BasePrice: 50m, BaseToll: 20m),
                new SanguoSaveCityEconomy("c2", BasePrice: 50m, BaseToll: 20m),
            },
            TreasuryMinorUnits: 0,
            ContentPackId: "core_t2",
            ContentPackVersion: 7,
            BuildingLevelsByCityId: new Dictionary<string, IReadOnlyDictionary<string, int>>(StringComparer.Ordinal)
            {
                ["c1"] = new Dictionary<string, int>(StringComparer.Ordinal)
                {
                    ["building_market"] = 2,
                    ["building_farm"] = 1,
                },
                ["c2"] = new Dictionary<string, int>(StringComparer.Ordinal)
                {
                    ["building_market"] = 3,
                },
            }
        );
    }

    // ACC:T18.3
    [Fact]
    public async Task ShouldThrowAndNotPublishLoadedEvent_WhenLoadingMissingOrCorruptedSave()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        Func<Task> actMissing = async () => await svc.LoadGameAsync(
            saveSlotId: "slot-missing",
            correlationId: "corr-load",
            causationId: "ui.hud.load");

        await actMissing.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("Save not found:*");

        bus.Published.Should().BeEmpty();

        await store.SaveAsync("sanguo-save:slot-corrupt", "{\"corrupted\":true}");

        Func<Task> actCorrupt = async () => await svc.LoadGameAsync(
            saveSlotId: "slot-corrupt",
            correlationId: "corr-load",
            causationId: "ui.hud.load");

        await actCorrupt.Should().ThrowAsync<InvalidOperationException>();
        bus.Published.Should().BeEmpty();
    }

    // ACC:T18.4
    [Fact]
    public async Task ShouldPersistReadableJsonAndReturnSlotId_WhenSavingSnapshot()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var snapshot = MakeSnapshot(gameId: "g1", turnNumber: 3, activePlayerIndex: 0);
        var slotId = await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-1",
            correlationId: "corr-save",
            causationId: "ui.hud.save");

        slotId.Should().Be("slot-1");
        store.Saves.Should().ContainSingle();
        store.Saves[0].Key.Should().Be("sanguo-save:slot-1");

        var raw = store.Saves[0].Payload;
        using var doc = JsonDocument.Parse(raw);
        var root = doc.RootElement;
        root.TryGetProperty("Version", out _).Should().BeTrue();
        root.TryGetProperty("SaveSlotId", out var slotProp).Should().BeTrue();
        slotProp.GetString().Should().Be("slot-1");
        root.TryGetProperty("Checksum", out _).Should().BeTrue();
        root.TryGetProperty("Snapshot", out var snapProp).Should().BeTrue();
        snapProp.GetProperty("GameId").GetString().Should().Be("g1");
        snapProp.GetProperty("ContentPackId").GetString().Should().Be("core_t2");
        snapProp.GetProperty("ContentPackVersion").GetInt32().Should().Be(7);
        snapProp.TryGetProperty("BuildingLevelsByCityId", out var buildingLevelsProp).Should().BeTrue();
        buildingLevelsProp.GetProperty("c1").GetProperty("building_market").GetInt32().Should().Be(2);
        buildingLevelsProp.GetProperty("c1").GetProperty("building_farm").GetInt32().Should().Be(1);
        buildingLevelsProp.GetProperty("c2").GetProperty("building_market").GetInt32().Should().Be(3);

        bus.Published.Should().ContainSingle(e => e.Type == SanguoGameSaved.EventType);
    }

    // ACC:T18.5
    [Fact]
    public async Task ShouldReturnSnapshotAndPublishSavedAndLoadedEvents_WhenLoadingSavedSnapshot()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var snapshot = MakeSnapshot(gameId: "g1", turnNumber: 4, activePlayerIndex: 1);
        var saveId = await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-evt",
            correlationId: "corr-save",
            causationId: "ui.hud.save");

        saveId.Should().Be("slot-evt");

        var loaded = await svc.LoadGameAsync(
            saveSlotId: saveId,
            correlationId: "corr-load",
            causationId: "ui.hud.load");

        loaded.Should().BeEquivalentTo(snapshot);

        bus.Published.Should().ContainSingle(e => e.Type == SanguoGameSaved.EventType);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoGameLoaded.EventType);

        var savedEvt = bus.Published.Single(e => e.Type == SanguoGameSaved.EventType);
        var savedPayload = ((JsonElementEventData)savedEvt.Data!).Value;
        savedPayload.GetProperty("GameId").GetString().Should().Be("g1");
        savedPayload.GetProperty("SaveSlotId").GetString().Should().Be(saveId);
        savedPayload.GetProperty("CorrelationId").GetString().Should().Be("corr-save");
        savedPayload.GetProperty("CausationId").GetString().Should().Be("ui.hud.save");
        savedPayload.GetProperty("ContentPackId").GetString().Should().Be("core_t2");
        savedPayload.GetProperty("ContentPackVersion").GetInt32().Should().Be(7);

        var loadedEvt = bus.Published.Single(e => e.Type == SanguoGameLoaded.EventType);
        var loadedPayload = ((JsonElementEventData)loadedEvt.Data!).Value;
        loadedPayload.GetProperty("GameId").GetString().Should().Be("g1");
        loadedPayload.GetProperty("SaveSlotId").GetString().Should().Be(saveId);
        loadedPayload.GetProperty("CorrelationId").GetString().Should().Be("corr-load");
        loadedPayload.GetProperty("CausationId").GetString().Should().Be("ui.hud.load");
        loadedPayload.GetProperty("ContentPackId").GetString().Should().Be("core_t2");
        loadedPayload.GetProperty("ContentPackVersion").GetInt32().Should().Be(7);
    }

    // ACC:T18.6
    [Fact]
    public async Task ShouldRoundTripSnapshot_WhenSavingThenLoadingSavedSnapshot()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var original = MakeSnapshot(gameId: "g1", turnNumber: 10, activePlayerIndex: 0);
        var slotId = await svc.SaveGameAsync(
            snapshot: original,
            saveSlotId: "slot-roundtrip",
            correlationId: "corr-save",
            causationId: "ui.hud.save");

        var loaded = await svc.LoadGameAsync(
            saveSlotId: slotId,
            correlationId: "corr-load",
            causationId: "ui.hud.load");

        loaded.Should().BeEquivalentTo(original);
        loaded.BuildingLevelsByCityId.Should().NotBeNull();
        loaded.BuildingLevelsByCityId!["c1"]["building_market"].Should().Be(2);
        loaded.BuildingLevelsByCityId!["c1"]["building_farm"].Should().Be(1);
        loaded.BuildingLevelsByCityId!["c2"]["building_market"].Should().Be(3);
    }

    // ACC:T18.7
    [Fact]
    public async Task ShouldFailAndNotPublishLoadedEvent_WhenLoadingIncompatibleSave()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var snapshot = MakeSnapshot(gameId: "g1", turnNumber: 1, activePlayerIndex: 0);
        var json = JsonSerializer.Serialize(new
        {
            Version = "",
            SaveSlotId = "slot-bad",
            SavedAtUtc = DateTimeOffset.UtcNow,
            Checksum = "",
            Snapshot = snapshot,
        });
        await store.SaveAsync("sanguo-save:slot-bad", json);

        Func<Task> act = async () => await svc.LoadGameAsync(
            saveSlotId: "slot-bad",
            correlationId: "corr-load",
            causationId: "ui.hud.load");

        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("Save file is corrupted");

        bus.Published.Should().BeEmpty();
    }

    [Theory]
    [InlineData("")]
    [InlineData("  ")]
    public async Task ShouldThrowArgumentException_WhenSavingGameWithEmptyCorrelationId(string correlationId)
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var snapshot = MakeSnapshot(gameId: "g1", turnNumber: 1, activePlayerIndex: 0);
        Func<Task> act = async () => await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-1",
            correlationId: correlationId,
            causationId: "ui.hud.save");

        await act.Should().ThrowAsync<ArgumentException>();
        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task ShouldThrowArgumentException_WhenSavingGameWithEmptySnapshotGameId()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var snapshot = MakeSnapshot(gameId: "g1", turnNumber: 1, activePlayerIndex: 0) with { GameId = "" };
        Func<Task> act = async () => await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-1",
            correlationId: "corr-save",
            causationId: "ui.hud.save");

        await act.Should().ThrowAsync<ArgumentException>();
        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task ShouldThrowAndNotPublishLoadedEvent_WhenLoadingGameWithChecksumMismatch()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var snapshot = MakeSnapshot(gameId: "g1", turnNumber: 4, activePlayerIndex: 1);
        _ = await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-mismatch",
            correlationId: "corr-save",
            causationId: "ui.hud.save");

        var raw = await store.LoadAsync("sanguo-save:slot-mismatch");
        raw.Should().NotBeNullOrWhiteSpace();

        using var doc = JsonDocument.Parse(raw!);
        var root = doc.RootElement;
        var corruptedSnapshot = snapshot with { TurnNumber = snapshot.TurnNumber + 1 };
        var mutated = JsonSerializer.Serialize(new
        {
            Version = root.GetProperty("Version").GetString(),
            SaveSlotId = root.GetProperty("SaveSlotId").GetString(),
            SavedAtUtc = root.GetProperty("SavedAtUtc").GetString(),
            Checksum = root.GetProperty("Checksum").GetString(),
            Snapshot = corruptedSnapshot,
        });
        await store.SaveAsync("sanguo-save:slot-mismatch", mutated);

        bus.Published.Clear();

        Func<Task> act = async () => await svc.LoadGameAsync(
            saveSlotId: "slot-mismatch",
            correlationId: "corr-load",
            causationId: "ui.hud.load");

        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("Save file is corrupted");

        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task ShouldThrowArgumentOutOfRangeException_WhenSavingGameWithTooLongSaveSlotId()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var snapshot = MakeSnapshot(gameId: "g1", turnNumber: 1, activePlayerIndex: 0);
        var slotId = new string('a', 65);

        Func<Task> act = async () => await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: slotId,
            correlationId: "corr-save",
            causationId: "ui.hud.save");

        await act.Should().ThrowAsync<ArgumentOutOfRangeException>();
        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task ShouldThrowArgumentOutOfRangeException_WhenSavingGameWithTooLongGameId()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var longGameId = new string('g', 65);
        var snapshot = MakeSnapshot(gameId: "g1", turnNumber: 1, activePlayerIndex: 0) with { GameId = longGameId };

        Func<Task> act = async () => await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-1",
            correlationId: "corr-save",
            causationId: "ui.hud.save");

        await act.Should().ThrowAsync<ArgumentOutOfRangeException>();
        bus.Published.Should().BeEmpty();
    }

    [Theory]
    [InlineData("")]
    [InlineData("  ")]
    public async Task ShouldThrowArgumentException_WhenLoadingGameWithEmptyCorrelationId(string correlationId)
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        Func<Task> act = async () => await svc.LoadGameAsync(
            saveSlotId: "slot-1",
            correlationId: correlationId,
            causationId: "ui.hud.load");

        await act.Should().ThrowAsync<ArgumentException>();
        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task ShouldThrowArgumentException_WhenSavingGameWithEmptySaveSlotId()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var snapshot = MakeSnapshot(gameId: "g1", turnNumber: 1, activePlayerIndex: 0);
        Func<Task> act = async () => await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "",
            correlationId: "corr-save",
            causationId: "ui.hud.save");

        await act.Should().ThrowAsync<ArgumentException>();
        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task ShouldThrowArgumentException_WhenLoadingGameWithEmptySaveSlotId()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        Func<Task> act = async () => await svc.LoadGameAsync(
            saveSlotId: "",
            correlationId: "corr-load",
            causationId: "ui.hud.load");

        await act.Should().ThrowAsync<ArgumentException>();
        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task ShouldThrowArgumentOutOfRangeException_WhenLoadingGameWithTooLongSaveSlotId()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var slotId = new string('a', 65);
        Func<Task> act = async () => await svc.LoadGameAsync(
            saveSlotId: slotId,
            correlationId: "corr-load",
            causationId: "ui.hud.load");

        await act.Should().ThrowAsync<ArgumentOutOfRangeException>();
        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task ShouldThrowSaveDataInvalid_WhenLoadingGameWithJsonNull()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        await store.SaveAsync("sanguo-save:slot-null", "null");

        Func<Task> act = async () => await svc.LoadGameAsync(
            saveSlotId: "slot-null",
            correlationId: "corr-load",
            causationId: "ui.hud.load");

        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("Save data is invalid.");

        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task ShouldThrowSaveFileCorrupted_WhenLoadingGameWithNullSnapshot()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var json = JsonSerializer.Serialize(new
        {
            Version = "1.0.0",
            SaveSlotId = "slot-null-snap",
            SavedAtUtc = DateTimeOffset.UtcNow,
            Checksum = "DEADBEEF",
            Snapshot = (object?)null,
        });
        await store.SaveAsync("sanguo-save:slot-null-snap", json);

        Func<Task> act = async () => await svc.LoadGameAsync(
            saveSlotId: "slot-null-snap",
            correlationId: "corr-load",
            causationId: "ui.hud.load");

        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("Save file is corrupted");

        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task ShouldThrowInvalidOperationException_WhenSavingGameWithOversizedPayload()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var huge = new string('x', 2_000_100);
        var snapshot = MakeSnapshot(gameId: "g1", turnNumber: 1, activePlayerIndex: 0) with
        {
            Players = new[]
            {
                new SanguoSavePlayer("p1", Money: 1m, PositionIndex: 0, IsEliminated: false, OwnedCityIds: new[] { huge }),
                new SanguoSavePlayer("ai-1", Money: 1m, PositionIndex: 0, IsEliminated: false, OwnedCityIds: Array.Empty<string>()),
            },
        };

        Func<Task> act = async () => await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-big",
            correlationId: "corr-save",
            causationId: "ui.hud.save");

        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("Save payload too large*");
        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task ShouldThrowSaveFileCorrupted_WhenLoadingGameWithMissingChecksum()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var snapshot = MakeSnapshot(gameId: "g1", turnNumber: 1, activePlayerIndex: 0);
        var json = JsonSerializer.Serialize(new
        {
            Version = "1.0.0",
            SaveSlotId = "slot-missing-checksum",
            SavedAtUtc = DateTimeOffset.UtcNow,
            Checksum = "",
            Snapshot = snapshot,
        });
        await store.SaveAsync("sanguo-save:slot-missing-checksum", json);

        Func<Task> act = async () => await svc.LoadGameAsync(
            saveSlotId: "slot-missing-checksum",
            correlationId: "corr-load",
            causationId: "ui.hud.load");

        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("Save file is corrupted");
        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task ShouldThrowSaveFileCorrupted_WhenLoadingGameWithMissingVersion()
    {
        var store = new RecordingDataStore();
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);

        var snapshot = MakeSnapshot(gameId: "g1", turnNumber: 1, activePlayerIndex: 0);
        var json = JsonSerializer.Serialize(new
        {
            Version = "",
            SaveSlotId = "slot-missing-version",
            SavedAtUtc = DateTimeOffset.UtcNow,
            Checksum = "DEADBEEF",
            Snapshot = snapshot,
        });
        await store.SaveAsync("sanguo-save:slot-missing-version", json);

        Func<Task> act = async () => await svc.LoadGameAsync(
            saveSlotId: "slot-missing-version",
            correlationId: "corr-load",
            causationId: "ui.hud.load");

        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("Save file is corrupted");
        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task ShouldAllowRetrySaveAfterFailure_WhenCallerRetriesBeforeLeavingCamp()
    {
        var store = new FlakySaveDataStore(remainingSaveFailures: 1);
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);
        var snapshot = MakeSnapshot(gameId: "g-a003", turnNumber: 2, activePlayerIndex: 0);

        Func<Task> firstAttempt = async () => await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-a003",
            correlationId: "corr-a003-1",
            causationId: "camp.leave");

        await firstAttempt.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("simulated_save_failure");

        svc.IsSaveWarningActive.Should().BeTrue();
        svc.ConsecutiveSaveFailures.Should().Be(1);

        var slotId = await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-a003",
            correlationId: "corr-a003-2",
            causationId: "camp.leave.retry");

        slotId.Should().Be("slot-a003");
        svc.IsSaveWarningActive.Should().BeFalse();
        svc.ConsecutiveSaveFailures.Should().Be(0);
        store.SaveAttempts.Should().Be(2);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoGameSaved.EventType);
    }

    [Fact]
    public async Task ShouldRemainCallable_WhenRetryStillFailsAndLaterAttemptSucceeds()
    {
        var store = new FlakySaveDataStore(remainingSaveFailures: 2);
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);
        var snapshot = MakeSnapshot(gameId: "g-a004", turnNumber: 2, activePlayerIndex: 0);

        Func<Task> firstAttempt = async () => await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-a004",
            correlationId: "corr-a004-1",
            causationId: "camp.leave");
        Func<Task> secondAttempt = async () => await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-a004",
            correlationId: "corr-a004-2",
            causationId: "camp.leave.retry");

        await firstAttempt.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("simulated_save_failure");
        await secondAttempt.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("simulated_save_failure");

        svc.IsSaveWarningActive.Should().BeTrue();
        svc.ConsecutiveSaveFailures.Should().Be(2);
        store.SaveAttempts.Should().Be(2);

        var slotId = await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-a004",
            correlationId: "corr-a004-3",
            causationId: "camp.leave.final");

        slotId.Should().Be("slot-a004");
        svc.IsSaveWarningActive.Should().BeFalse();
        svc.ConsecutiveSaveFailures.Should().Be(0);
        store.SaveAttempts.Should().Be(3);
    }

    [Fact]
    public async Task ShouldKeepSaveWarningActive_WhenNextSaveSucceeds()
    {
        var store = new FlakySaveDataStore(remainingSaveFailures: 2);
        var bus = new RecordingEventBus();
        var svc = new SanguoSaveLoadService(bus, store);
        var snapshot = MakeSnapshot(gameId: "g-a005", turnNumber: 5, activePlayerIndex: 1);

        for (var attempt = 1; attempt <= 2; attempt++)
        {
            Func<Task> act = async () => await svc.SaveGameAsync(
                snapshot: snapshot,
                saveSlotId: "slot-a005",
                correlationId: $"corr-a005-{attempt}",
                causationId: "camp.autosave");

            await act.Should().ThrowAsync<InvalidOperationException>()
                .WithMessage("simulated_save_failure");

            svc.IsSaveWarningActive.Should().BeTrue();
            svc.ConsecutiveSaveFailures.Should().Be(attempt);
        }

        bus.Published.Should().BeEmpty();

        _ = await svc.SaveGameAsync(
            snapshot: snapshot,
            saveSlotId: "slot-a005",
            correlationId: "corr-a005-3",
            causationId: "camp.autosave.retry");

        svc.IsSaveWarningActive.Should().BeFalse();
        svc.ConsecutiveSaveFailures.Should().Be(0);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoGameSaved.EventType);
    }
}
