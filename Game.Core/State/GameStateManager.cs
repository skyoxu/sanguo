using System.Text.Json;
using Game.Core.Contracts;
using Game.Core.Domain;
using Game.Core.Ports;

namespace Game.Core.State;

public class GameStateManager
{
    private static readonly JsonSerializerOptions JsonDeserializeOptions = new()
    {
        MaxDepth = 32,
    };

    private readonly GameStateManagerOptions _options;
    private readonly IDataStore _store;
    private readonly ILogger? _logger;
    private readonly IErrorReporter? _reporter;
    private readonly List<Action<DomainEvent>> _callbacks = new();

    private GameState? _currentState;
    private GameConfig? _currentConfig;
    private bool _autoSaveEnabled;

    private const string IndexSuffix = ":index";

    public GameStateManager(
        IDataStore store,
        GameStateManagerOptions? options = null,
        ILogger? logger = null,
        IErrorReporter? reporter = null)
    {
        _store = store;
        _options = options ?? GameStateManagerOptions.Default;
        _logger = logger;
        _reporter = reporter;
    }

    public void SetState(GameState state, GameConfig? config = null)
    {
        _currentState = state with { };
        if (config is not null)
            _currentConfig = config with { };

        Publish(new DomainEvent(
            Type: CoreGameEvents.GameStateManagerUpdated,
            Source: nameof(GameStateManager),
            Data: JsonElementEventData.FromObject(new { state, config }),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        ));
    }

    public GameState? GetState() => _currentState is null ? null : _currentState with { };
    public GameConfig? GetConfig() => _currentConfig is null ? null : _currentConfig with { };

    private const int MaxTitleLength = 100;
    private const int MaxScreenshotChars = 2_000_000; // ~>1.5MB base64

    public async Task<string> SaveGameAsync(string? name = null, string? screenshot = null)
    {
        if (_currentState is null || _currentConfig is null)
            throw new InvalidOperationException("No game state to save");

        if (!string.IsNullOrEmpty(name) && name!.Length > MaxTitleLength)
            throw new ArgumentOutOfRangeException(nameof(name), $"Title too long (>{MaxTitleLength}).");
        if (!string.IsNullOrEmpty(screenshot) && screenshot!.Length > MaxScreenshotChars)
            throw new ArgumentOutOfRangeException(nameof(screenshot), $"Screenshot too large (>{MaxScreenshotChars} chars).");

        var saveId = $"{_options.StorageKey}-{Guid.NewGuid().ToString("N")}";
        var checksum = CalculateChecksum(_currentState);
        var now = DateTime.UtcNow;

        var save = new SaveData(
            Id: saveId,
            State: _currentState,
            Config: _currentConfig,
            Metadata: new SaveMetadata(now, now, "1.0.0", checksum),
            Screenshot: screenshot,
            Title: name
        );

        await SaveToStoreAsync(saveId, save);
        await UpdateIndexAsync(add: saveId);
        await CleanupOldSavesAsync();

        Publish(new DomainEvent(
            Type: CoreGameEvents.GameSaveCreated,
            Source: nameof(GameStateManager),
            Data: JsonElementEventData.FromObject(new { saveId }),
            Timestamp: now,
            Id: Guid.NewGuid().ToString("N")
        ));

        return saveId;
    }

    public async Task<(GameState state, GameConfig config)> LoadGameAsync(string saveId)
    {
        var save = await LoadFromStoreAsync(saveId);
        var checksum = CalculateChecksum(save.State);
        if (!string.Equals(checksum, save.Metadata.Checksum, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Save file is corrupted");

        _currentState = save.State with { };
        _currentConfig = save.Config with { };

        Publish(new DomainEvent(
            Type: CoreGameEvents.GameSaveLoaded,
            Source: nameof(GameStateManager),
            Data: JsonElementEventData.FromObject(new { saveId }),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        ));

        return (_currentState, _currentConfig);
    }

    public async Task DeleteSaveAsync(string saveId)
    {
        await _store.DeleteAsync(saveId);
        await UpdateIndexAsync(remove: saveId);

        Publish(new DomainEvent(
            Type: CoreGameEvents.GameSaveDeleted,
            Source: nameof(GameStateManager),
            Data: JsonElementEventData.FromObject(new { saveId }),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        ));
    }

    public async Task<IReadOnlyList<SaveData>> GetSaveListAsync()
    {
        var ids = await ReadIndexAsync();
        var list = new List<SaveData>();
        foreach (var id in ids)
        {
            try { list.Add(await LoadFromStoreAsync(id)); }
            catch { /* ignore broken entries */ }
        }
        return list
            .OrderByDescending(s => s.Metadata.CreatedAt)
            .ToList();
    }

    public void EnableAutoSave()
    {
        if (_autoSaveEnabled) return;
        _autoSaveEnabled = true;
        Publish(new DomainEvent(
            Type: CoreGameEvents.GameAutosaveEnabled,
            Source: nameof(GameStateManager),
            Data: JsonElementEventData.FromObject(new { interval = _options.AutoSaveInterval.TotalMilliseconds }),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        ));
    }

    public void DisableAutoSave()
    {
        if (!_autoSaveEnabled) return;
        _autoSaveEnabled = false;
        Publish(new DomainEvent(
            Type: CoreGameEvents.GameAutosaveDisabled,
            Source: nameof(GameStateManager),
            Data: null,
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        ));
    }

    // For tests or scheduler to trigger
    public async Task AutoSaveTickAsync()
    {
        if (_autoSaveEnabled && _currentState is not null && _currentConfig is not null)
        {
            await SaveGameAsync($"auto-save-{Guid.NewGuid().ToString("N")}");
            Publish(new DomainEvent(
                Type: CoreGameEvents.GameAutosaveCompleted,
                Source: nameof(GameStateManager),
                Data: JsonElementEventData.FromObject(new { interval = _options.AutoSaveInterval.TotalMilliseconds }),
                Timestamp: DateTime.UtcNow,
                Id: Guid.NewGuid().ToString("N")
            ));
        }
    }

    public void OnEvent(Action<DomainEvent> callback) => _callbacks.Add(callback);
    public void OffEvent(Action<DomainEvent> callback) => _callbacks.Remove(callback);

    public void Destroy()
    {
        _callbacks.Clear();
        _currentState = null;
        _currentConfig = null;
        _autoSaveEnabled = false;
    }

    private async Task SaveToStoreAsync(string key, SaveData data)
    {
        var json = JsonSerializer.Serialize(data);
        if (_options.EnableCompression)
        {
            var compressed = CompressToBase64(json);
            await _store.SaveAsync(key, "gz:" + compressed);
        }
        else
        {
            await _store.SaveAsync(key, json);
        }
    }

    private async Task<SaveData> LoadFromStoreAsync(string key)
    {
        var raw = await _store.LoadAsync(key) ?? throw new InvalidOperationException($"Save not found: {key}");
        string json;
        if (raw.StartsWith("gz:"))
        {
            json = DecompressFromBase64(raw.Substring(3));
        }
        else
        {
            json = raw;
        }
        return JsonSerializer.Deserialize<SaveData>(json, JsonDeserializeOptions)
            ?? throw new InvalidOperationException("Save data is invalid.");
    }

    private async Task UpdateIndexAsync(string? add = null, string? remove = null)
    {
        var key = _options.StorageKey + IndexSuffix;
        var json = await _store.LoadAsync(key);
        var ids = json is null
            ? new List<string>()
            : (JsonSerializer.Deserialize<List<string>>(json, JsonDeserializeOptions) ?? new List<string>());
        if (add is not null) ids.Insert(0, add);
        if (remove is not null) ids.Remove(remove);
        var outJson = JsonSerializer.Serialize(ids.Distinct().ToList());
        await _store.SaveAsync(key, outJson);
    }

    private async Task CleanupOldSavesAsync()
    {
        var key = _options.StorageKey + IndexSuffix;
        var json = await _store.LoadAsync(key);
        if (json is null) return;
        var ids = JsonSerializer.Deserialize<List<string>>(json, JsonDeserializeOptions) ?? new List<string>();
        if (ids.Count <= _options.MaxSaves) return;
        var toDelete = ids.Skip(_options.MaxSaves).ToList();
        foreach (var id in toDelete)
        {
            await _store.DeleteAsync(id);
            ids.Remove(id);
        }
        await _store.SaveAsync(key, JsonSerializer.Serialize(ids));
    }

    private async Task<List<string>> ReadIndexAsync()
    {
        var key = _options.StorageKey + IndexSuffix;
        var json = await _store.LoadAsync(key);
        return json is null
            ? new List<string>()
            : (JsonSerializer.Deserialize<List<string>>(json, JsonDeserializeOptions) ?? new List<string>());
    }

    private static string CalculateChecksum(GameState state)
    {
        var json = JsonSerializer.Serialize(state);
        long hash = 0;
        foreach (var ch in json)
        {
            hash = ((hash << 5) - hash) + ch;
            hash &= 0xFFFFFFFF; // clamp to 32-bit
        }
        return hash.ToString("X");
    }

    private void Publish(DomainEvent evt)
    {
        foreach (var cb in _callbacks.ToArray())
        {
            try
            {
                cb(evt);
            }
            catch (Exception ex)
            {
                try
                {
                    _logger?.Error($"GameStateManager callback failed (type={evt.Type} source={evt.Source} id={evt.Id})", ex);
                }
                catch { }

                try
                {
                    var ctx = new Dictionary<string, string>
                    {
                        ["event_type"] = evt.Type,
                        ["event_source"] = evt.Source,
                        ["event_id"] = evt.Id,
                        ["callback"] = cb.Method.Name,
                        ["callback_type"] = cb.Method.DeclaringType?.FullName ?? "unknown",
                    };
                    _reporter?.CaptureException("gamestatemanager.callback.exception", ex, ctx);
                }
                catch { }
            }
        }
    }

    private static string CompressToBase64(string text)
    {
        var bytes = System.Text.Encoding.UTF8.GetBytes(text);
        using var ms = new MemoryStream();
        using (var gz = new System.IO.Compression.GZipStream(ms, System.IO.Compression.CompressionLevel.SmallestSize, true))
        {
            gz.Write(bytes, 0, bytes.Length);
        }
        return Convert.ToBase64String(ms.ToArray());
    }

    private static string DecompressFromBase64(string base64)
    {
        var bytes = Convert.FromBase64String(base64);
        using var ms = new MemoryStream(bytes);
        using var gz = new System.IO.Compression.GZipStream(ms, System.IO.Compression.CompressionMode.Decompress);
        using var outMs = new MemoryStream();
        gz.CopyTo(outMs);
        return System.Text.Encoding.UTF8.GetString(outMs.ToArray());
    }
}
