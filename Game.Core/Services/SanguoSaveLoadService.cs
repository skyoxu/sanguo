using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using System;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace Game.Core.Services;

public sealed class SanguoSaveLoadService
{
    private const int MaxSlotIdLength = 64;
    private const int MaxGameIdLength = 64;
    private const int MaxSerializedChars = 2_000_000;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        MaxDepth = 32,
    };

    private readonly IEventBus _bus;
    private readonly IDataStore _store;

    public bool IsSaveWarningActive { get; private set; }

    public int ConsecutiveSaveFailures { get; private set; }

    public SanguoSaveLoadService(IEventBus bus, IDataStore store)
    {
        _bus = bus ?? throw new ArgumentNullException(nameof(bus));
        _store = store ?? throw new ArgumentNullException(nameof(store));
    }

    public async Task<string> SaveGameAsync(
        SanguoSaveSnapshot snapshot,
        string saveSlotId,
        string correlationId,
        string? causationId)
    {
        ArgumentNullException.ThrowIfNull(snapshot, nameof(snapshot));

        if (string.IsNullOrWhiteSpace(snapshot.GameId))
            throw new ArgumentException("GameId is required.", nameof(snapshot));
        if (snapshot.GameId.Length > MaxGameIdLength)
            throw new ArgumentOutOfRangeException(nameof(snapshot), $"GameId too long (>{MaxGameIdLength}).");

        if (string.IsNullOrWhiteSpace(saveSlotId))
            throw new ArgumentException("SaveSlotId is required.", nameof(saveSlotId));
        if (saveSlotId.Length > MaxSlotIdLength)
            throw new ArgumentOutOfRangeException(nameof(saveSlotId), $"SaveSlotId too long (>{MaxSlotIdLength}).");

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId is required.", nameof(correlationId));

        var nowUtc = DateTime.UtcNow;
        var checksum = CalculateChecksum(snapshot);
        var replayTrustHash = CalculateReplayTrustHash(snapshot);

        var saveFile = new SanguoSaveFile(
            Version: "1.0.0",
            SaveSlotId: saveSlotId,
            SavedAtUtc: new DateTimeOffset(nowUtc),
            Checksum: checksum,
            ReplayTrustHash: replayTrustHash,
            Snapshot: snapshot
        );

        var json = JsonSerializer.Serialize(saveFile, JsonOptions);
        if (json.Length > MaxSerializedChars)
            throw new InvalidOperationException($"Save payload too large ({json.Length} chars).");

        try
        {
            await _store.SaveAsync(BuildKey(saveSlotId), json);
            IsSaveWarningActive = false;
            ConsecutiveSaveFailures = 0;
        }
        catch
        {
            IsSaveWarningActive = true;
            ConsecutiveSaveFailures++;
            throw;
        }

        var evt = new SanguoGameSaved(
            GameId: snapshot.GameId,
            SaveSlotId: saveSlotId,
            ContentPackId: snapshot.ContentPackId ?? string.Empty,
            ContentPackVersion: snapshot.ContentPackVersion,
            OccurredAt: new DateTimeOffset(nowUtc),
            CorrelationId: correlationId,
            CausationId: causationId);

        await _bus.PublishAsync(new DomainEvent(
            Type: SanguoGameSaved.EventType,
            Source: nameof(SanguoSaveLoadService),
            Data: JsonElementEventData.FromObject(evt),
            Timestamp: nowUtc,
            Id: Guid.NewGuid().ToString("N")
        ));

        return saveSlotId;
    }

    public async Task<SanguoSaveSnapshot> LoadGameAsync(
        string saveSlotId,
        string correlationId,
        string? causationId)
    {
        if (string.IsNullOrWhiteSpace(saveSlotId))
            throw new ArgumentException("SaveSlotId is required.", nameof(saveSlotId));
        if (saveSlotId.Length > MaxSlotIdLength)
            throw new ArgumentOutOfRangeException(nameof(saveSlotId), $"SaveSlotId too long (>{MaxSlotIdLength}).");

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId is required.", nameof(correlationId));

        var raw = await _store.LoadAsync(BuildKey(saveSlotId)) ?? throw new InvalidOperationException($"Save not found: {saveSlotId}");
        var file = JsonSerializer.Deserialize<SanguoSaveFile>(raw, JsonOptions) ?? throw new InvalidOperationException("Save data is invalid.");

        if (file.Snapshot is null || string.IsNullOrWhiteSpace(file.Version) || string.IsNullOrWhiteSpace(file.Checksum))
            throw new InvalidOperationException("Save file is corrupted");

        var checksum = CalculateChecksum(file.Snapshot);
        if (!string.Equals(checksum, file.Checksum, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Save file is corrupted");

        var expectedReplayTrustHash = CalculateReplayTrustHash(file.Snapshot);
        var saveUntrusted = !string.Equals(expectedReplayTrustHash, file.ReplayTrustHash, StringComparison.OrdinalIgnoreCase);

        var nowUtc = DateTime.UtcNow;
        var evt = new SanguoGameLoaded(
            GameId: file.Snapshot.GameId,
            SaveSlotId: saveSlotId,
            ContentPackId: file.Snapshot.ContentPackId ?? string.Empty,
            ContentPackVersion: file.Snapshot.ContentPackVersion,
            OccurredAt: new DateTimeOffset(nowUtc),
            CorrelationId: correlationId,
            CausationId: causationId,
            SaveUntrusted: saveUntrusted);

        await _bus.PublishAsync(new DomainEvent(
            Type: SanguoGameLoaded.EventType,
            Source: nameof(SanguoSaveLoadService),
            Data: JsonElementEventData.FromObject(evt),
            Timestamp: nowUtc,
            Id: Guid.NewGuid().ToString("N")
        ));

        return file.Snapshot;
    }

    private static string BuildKey(string saveSlotId) => $"sanguo-save:{saveSlotId}";

    private static string CalculateChecksum(SanguoSaveSnapshot snapshot)
    {
        var json = JsonSerializer.Serialize(snapshot, JsonOptions);
        long hash = 0;
        foreach (var ch in json)
        {
            hash = ((hash << 5) - hash) + ch;
            hash &= 0xFFFFFFFF;
        }
        return hash.ToString("X");
    }

    private static string CalculateReplayTrustHash(SanguoSaveSnapshot snapshot)
    {
        var canonicalSnapshotJson = JsonSerializer.Serialize(snapshot, JsonOptions);
        var bytes = Encoding.UTF8.GetBytes(canonicalSnapshotJson);
        var hash = SHA256.HashData(bytes);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    private sealed record SanguoSaveFile(
        string Version,
        string SaveSlotId,
        DateTimeOffset SavedAtUtc,
        string Checksum,
        string ReplayTrustHash,
        SanguoSaveSnapshot Snapshot
    );
}
