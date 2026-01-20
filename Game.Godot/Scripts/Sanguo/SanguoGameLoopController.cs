using Godot;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Ports;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;
using Game.Core.Services;
using Game.Godot.Adapters;
using Game.Godot.Autoloads;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;

namespace Game.Godot.Scripts.Sanguo;

/// <summary>
/// Wires Sanguo core turn loop into the Godot runtime via the global EventBus.
/// Responsibilities:
/// - Start the Sanguo game when the UI emits <c>ui.menu.start</c>.
/// - Advance the Sanguo turn loop when the UI emits <c>ui.hud.dice.roll</c>.
/// This node intentionally owns the "glue" only; the authoritative rules remain in Game.Core.
/// </summary>
public partial class SanguoGameLoopController : Node
{
    [Signal]
    public delegate void QuitRequestedEventHandler();

    private const string UiMenuStart = "ui.menu.start";
    private const string UiMenuQuit = "ui.menu.quit";
    private const string UiMenuStartFailed = "ui.menu.start.failed";
    private const string UiHudDiceRoll = "ui.hud.dice.roll";
    private const string UiHudSave = "ui.hud.save";
    private const string UiHudLoad = "ui.hud.load";
    private const string UiTileActionSelected = "ui.sanguo.tile.action.selected";
    private const string AiAutoAdvanceCausationId = "runtime.ai.auto.advance";

    private const int DefaultPlayersCount = 4;
    private const int DefaultStartingMoneyPreset = 10000;
    private const int DefaultGlobalEventIntervalTurns = 10;

    private const string DefaultUiClickSfxId = "res://Game.Godot/Assets/Audio/ui_click.wav";
    private const string DefaultMusicLoopId = "res://Game.Godot/Assets/Audio/music_loop.wav";

    [Export(PropertyHint.Range, "0,30,0.1,or_greater")]
    public double AiAutoAdvanceDelaySeconds { get; set; } = 5.0;

    [Export(PropertyHint.Range, "0,30,0.1,or_greater")]
    public double AiAutoAdvanceDelaySecondsWhenSkip { get; set; } = 5.0;

    [Export]
    public NodePath BoardViewPath { get; set; } = new NodePath("../SanguoBoardView");

    private EventBusAdapter? _bus;
    private AudioPlayerAdapter? _audio;
    private SanguoTurnManager? _turnManager;
    private bool _started;
    private bool _advanceQueued;
    private string? _activePlayerId;
    private bool _aiAutoAdvanceRequested;
    private double _aiAutoAdvanceDelaySec = 5.0;

    private SanguoMapDefinition? _map;
    private readonly Dictionary<int, string[]> _actionsByIndex = new();
    private bool _awaitingHumanTileAction;
    private string _awaitingHumanActionCorrelationId = string.Empty;
    private string _lastHumanMoveCorrelationId = string.Empty;
    private int _lastHumanMoveToIndex;
    private string _lastSaveSlotId = "quick";
    private GameStartConfig? _lastStartConfig;

    private sealed record GameStartedPayload(
        [property: JsonPropertyName("game_start_config")] GameStartConfig GameStartConfig,
        [property: JsonPropertyName("random_seed")] int RandomSeed
    );

    private static readonly JsonSerializerOptions UiJsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = false,
    };

    private static bool IsQuitSuppressed()
        => string.Equals(System.Environment.GetEnvironmentVariable("GD_DISABLE_QUIT"), "1", StringComparison.Ordinal);

    public override void _Ready()
    {
        var debug = string.Equals(System.Environment.GetEnvironmentVariable("SC_E2E_DEBUG_ARGS"), "1", StringComparison.Ordinal);
        _bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        _audio = GetNodeOrNull<AudioPlayerAdapter>("../Audio");
        if (_bus == null)
        {
            if (debug)
            {
                GD.Print("[E2E_SAVELOAD] SanguoGameLoopController: EventBus missing");
            }
            GD.PushWarning("SanguoGameLoopController: EventBus not found at /root/EventBus");
            return;
        }
        if (debug)
        {
            GD.Print("[E2E_SAVELOAD] SanguoGameLoopController: ready");
        }

        var callable = new Callable(this, nameof(OnDomainEventEmitted));
        if (!_bus.IsConnected(EventBusAdapter.SignalName.DomainEventEmitted, callable))
        {
            _bus.Connect(EventBusAdapter.SignalName.DomainEventEmitted, callable);
        }

        TryRunSaveLoadE2eFromCmdline();
    }

    public override void _ExitTree()
    {
        if (_bus != null)
        {
            var callable = new Callable(this, nameof(OnDomainEventEmitted));
            if (_bus.IsConnected(EventBusAdapter.SignalName.DomainEventEmitted, callable))
            {
                _bus.Disconnect(EventBusAdapter.SignalName.DomainEventEmitted, callable);
            }
        }

        _bus = null;
        _audio = null;
        _turnManager = null;
        _started = false;
        _advanceQueued = false;
        _activePlayerId = null;
    }

    private void OnDomainEventEmitted(string type, string source, string dataJson, string id, string specVersion, string dataContentType, string timestampIso)
    {
        if (type == SanguoGameEnded.EventType)
        {
            _started = false;
            _turnManager = null;
            _advanceQueued = false;
            _activePlayerId = null;
            _aiAutoAdvanceRequested = false;
            _awaitingHumanTileAction = false;
            _awaitingHumanActionCorrelationId = string.Empty;
            _lastHumanMoveCorrelationId = string.Empty;
            return;
        }

        if (type == UiHudSave)
        {
            if (!_started || _turnManager == null || _bus == null)
            {
                return;
            }

            if (_advanceQueued)
            {
                return;
            }

            var correlationId = SanguoGlueJson.TryExtractCorrelationId(dataJson) ?? Guid.NewGuid().ToString("N");
            var saveSlotId = SanguoGlueJson.TryExtractSaveSlotId(dataJson) ?? _lastSaveSlotId;
            _lastSaveSlotId = saveSlotId;
            _advanceQueued = true;
            CallDeferred(nameof(SaveGameDeferred), correlationId, saveSlotId);
            return;
        }

        if (type == UiHudLoad)
        {
            if (_bus == null)
            {
                return;
            }

            if (_advanceQueued)
            {
                return;
            }

            var correlationId = SanguoGlueJson.TryExtractCorrelationId(dataJson) ?? Guid.NewGuid().ToString("N");
            var saveSlotId = SanguoGlueJson.TryExtractSaveSlotId(dataJson) ?? _lastSaveSlotId;
            _lastSaveSlotId = saveSlotId;
            _advanceQueued = true;
            CallDeferred(nameof(LoadGameDeferred), correlationId, saveSlotId);
            return;
        }

        if (type == SanguoGameTurnStarted.EventType)
        {
            _activePlayerId = SanguoGlueJson.TryExtractActivePlayerId(dataJson);
            return;
        }

        if (type == SanguoTokenMoved.EventType)
        {
            var pid = SanguoGlueJson.TryExtractPlayerId(dataJson);
            if (!SanguoGlueJson.IsAiPlayerId(pid) && !string.IsNullOrWhiteSpace(pid))
            {
                _lastHumanMoveCorrelationId = SanguoGlueJson.TryExtractCorrelationId(dataJson) ?? string.Empty;
                _lastHumanMoveToIndex = SanguoGlueJson.TryExtractIntProperty(dataJson, "ToIndex") ?? 0;
            }
            return;
        }

        if (type == SanguoAiDecisionMade.EventType)
        {
            var decisionType = SanguoGlueJson.TryExtractAiDecisionType(dataJson);
            _aiAutoAdvanceRequested = true;
            _aiAutoAdvanceDelaySec = string.Equals(decisionType, "Skip", StringComparison.OrdinalIgnoreCase)
                ? AiAutoAdvanceDelaySecondsWhenSkip
                : AiAutoAdvanceDelaySeconds;

            TryQueueAiAutoAdvanceIfNeeded();
            return;
        }

        if (type == UiTileActionSelected)
        {
            if (!_started || _turnManager == null)
            {
                return;
            }

            if (!_awaitingHumanTileAction)
            {
                return;
            }

            var corr = SanguoGlueJson.TryExtractCorrelationId(dataJson) ?? string.Empty;
            if (string.IsNullOrWhiteSpace(corr) || !string.Equals(corr, _awaitingHumanActionCorrelationId, StringComparison.Ordinal))
            {
                return;
            }

            var action = SanguoGlueJson.TryExtractAction(dataJson) ?? string.Empty;
            _advanceQueued = true;
            CallDeferred(nameof(AdvanceAfterHumanTileActionDeferred), corr, action);
            return;
        }

        if (type == UiMenuQuit)
        {
            _audio?.PlaySfx(DefaultUiClickSfxId, 1f);
            EmitSignal(SignalName.QuitRequested);
            if (!IsQuitSuppressed())
            {
                GetTree().Quit();
            }
            return;
        }

        if (type == UiMenuStart)
        {
            if (_started)
            {
                return;
            }

            _audio?.PlaySfx(DefaultUiClickSfxId, 1f);
            _audio?.PlayMusic(DefaultMusicLoopId, 0.6f, true);

            var correlationId = Guid.NewGuid().ToString("N");
            CallDeferred(nameof(StartGameDeferred), correlationId);
            return;
        }

        if (type == UiHudDiceRoll)
        {
            _audio?.PlaySfx(DefaultUiClickSfxId, 1f);

            if (!_started || _turnManager == null)
            {
                return;
            }

            if (_advanceQueued)
            {
                return;
            }

            var playerId = SanguoGlueJson.TryExtractPlayerId(dataJson);
            if (!string.IsNullOrWhiteSpace(_activePlayerId) && !string.IsNullOrWhiteSpace(playerId) && !string.Equals(_activePlayerId, playerId, StringComparison.Ordinal))
            {
                return;
            }

            if (SanguoGlueJson.IsAiPlayerId(_activePlayerId) || SanguoGlueJson.IsAiPlayerId(playerId))
            {
                return;
            }

            var correlationId = SanguoGlueJson.TryExtractCorrelationId(dataJson) ?? Guid.NewGuid().ToString("N");
            _advanceQueued = true;
            CallDeferred(nameof(AdvanceTurnDeferred), correlationId);
        }
    }

    private async void SaveGameDeferred(string correlationId, string saveSlotId)
    {
        try
        {
            if (!_started || _turnManager == null || _bus == null)
            {
                return;
            }

            var store = ResolveDataStore();
            if (store == null)
            {
                GD.PushWarning("SanguoGameLoopController: DataStore not found; cannot save game.");
                return;
            }

            var service = new SanguoSaveLoadService(_bus, store);
            var snapshot = _turnManager.ExportSaveSnapshot();
            await service.SaveGameAsync(snapshot: snapshot, saveSlotId: saveSlotId, correlationId: correlationId, causationId: UiHudSave);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SanguoGameLoopController: failed to save game: {ex.Message}");
        }
        finally
        {
            _advanceQueued = false;
        }
    }

    private async void LoadGameDeferred(string correlationId, string saveSlotId)
    {
        try
        {
            if (_bus == null)
            {
                return;
            }

            var store = ResolveDataStore();
            if (store == null)
            {
                GD.PushWarning("SanguoGameLoopController: DataStore not found; cannot load game.");
                return;
            }

            if (_map == null)
            {
                var loader = ResolveResourceLoader();
                if (loader == null)
                {
                    GD.PushWarning("SanguoGameLoopController: ResourceLoaderPort not found; cannot load map config.");
                    return;
                }

                if (!SanguoMapConfigLoader.TryLoadMap(loader, correlationId, out var map, out var mapSourcePath, out var mapError))
                {
                    GD.PushWarning($"SanguoGameLoopController: map config load failed (source='{mapSourcePath}', error='{mapError}').");
                    return;
                }

                _map = map;
                LoadMapActions(map);

                var boardView = GetNodeOrNull<SanguoBoardView>(BoardViewPath);
                boardView?.ApplyMapDefinition(map);
            }

            if (_map == null)
            {
                return;
            }

            if (_turnManager == null)
            {
                _turnManager = CreateNewTurnManager(_map);
            }

            var service = new SanguoSaveLoadService(_bus, store);
            var snapshot = await service.LoadGameAsync(saveSlotId: saveSlotId, correlationId: correlationId, causationId: UiHudLoad);

            _turnManager.RestoreFromSaveSnapshot(snapshot);
            _started = true;
            _aiAutoAdvanceRequested = false;
            _awaitingHumanTileAction = false;
            _awaitingHumanActionCorrelationId = string.Empty;
            _lastHumanMoveCorrelationId = string.Empty;

            await _turnManager.PublishStateSnapshotAsync(correlationId: correlationId, causationId: UiHudLoad);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SanguoGameLoopController: failed to load game: {ex.Message}");
        }
        finally
        {
            _advanceQueued = false;
        }

        TryQueueAiAutoAdvanceIfNeeded();
    }

    private async void StartGameDeferred(string correlationId)
    {
        if (_started)
        {
            return;
        }

        if (_bus == null)
        {
            return;
        }

        _advanceQueued = true;
        try
        {
            var (ok, reason) = await TryStartNewGameAsync(correlationId: correlationId, causationId: UiMenuStart);
            if (!ok)
            {
                PublishMenuStartFailed(correlationId, reason);
            }
        }
        finally
        {
            _advanceQueued = false;
        }
    }

    private async Task<(bool ok, string reason)> TryStartNewGameAsync(string correlationId, string causationId)
    {
        if (_started)
        {
            return (true, "already_started");
        }

        if (_bus == null)
        {
            return (false, "event_bus_missing");
        }

        var loader = ResolveResourceLoader();
        if (loader == null)
        {
            GD.PushWarning("SanguoGameLoopController: ResourceLoaderPort not found; cannot load map config.");
            return (false, "resource_loader_missing");
        }

        if (!SanguoMapConfigLoader.TryLoadMap(loader, correlationId, out var map, out var mapSourcePath, out var mapError))
        {
            GD.PushWarning($"SanguoGameLoopController: map config load failed (source='{mapSourcePath}', error='{mapError}').");
            return (false, "map_config_load_failed");
        }

        _map = map;
        LoadMapActions(map);

        var boardView = GetNodeOrNull<SanguoBoardView>(BoardViewPath);
        boardView?.ApplyMapDefinition(map);

        var startConfig = CreateDefaultGameStartConfig(map);
        if (!GameStartConfigValidator.TryValidate(startConfig, out var startConfigErrors))
        {
            GD.PushWarning($"SanguoGameLoopController: start config invalid: {string.Join(" | ", startConfigErrors)}");
            return (false, "invalid_start_config");
        }

        _lastStartConfig = startConfig;
        _turnManager = CreateNewTurnManager(map, startConfig);

        try
        {
            await _turnManager.StartNewGameAsync(
                gameId: "g1",
                playerOrder: BuildDefaultPlayerOrder(startConfig.PlayersCount),
                year: 3,
                month: 2,
                day: 1,
                correlationId: correlationId,
                causationId: causationId);
            _started = true;

            PublishGameStarted(startConfig);
            TryQueueAiAutoAdvanceIfNeeded();
            return (true, string.Empty);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SanguoGameLoopController: failed to start game: {ex.Message}");
            _turnManager = null;
            _started = false;
            return (false, "exception:" + ex.GetType().Name);
        }
    }

    private static string[] BuildDefaultPlayerOrder(int playersCount)
    {
        if (playersCount <= 0)
        {
            return Array.Empty<string>();
        }

        var ids = new List<string>(capacity: playersCount)
        {
            "p1",
        };

        for (var i = 1; i < playersCount; i++)
        {
            ids.Add($"ai-{i}");
        }

        return ids.ToArray();
    }

    private static GameStartConfig CreateDefaultGameStartConfig(SanguoMapDefinition map)
    {
        var randomSeed = unchecked((int)(DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() & 0x7fffffff));
        var playerOrder = BuildDefaultPlayerOrder(DefaultPlayersCount);

        var characterPool = new[]
        {
            "c_liu_bei",
            "c_cao_cao",
            "c_sun_quan",
            "c_yuan_shao",
            "c_guan_yu",
            "c_zhang_fei",
            "c_zhao_yun",
            "c_diao_chan",
        };

        var assignments = new Dictionary<string, string>(StringComparer.Ordinal);
        for (var i = 0; i < playerOrder.Length; i++)
        {
            assignments[playerOrder[i]] = characterPool[i % characterPool.Length];
        }

        return new GameStartConfig(
            MapId: map.MapId,
            PlayersCount: DefaultPlayersCount,
            StartingMoneyPreset: DefaultStartingMoneyPreset,
            GlobalEventIntervalTurns: DefaultGlobalEventIntervalTurns,
            RandomSeed: randomSeed,
            CharacterAssignments: assignments
        );
    }

    private void PublishGameStarted(GameStartConfig cfg)
    {
        if (_bus == null)
        {
            return;
        }

        var payload = new GameStartedPayload(cfg, cfg.RandomSeed);
        var dataJson = JsonSerializer.Serialize(payload);
        _bus.PublishSimple(SanguoGameStarted.EventType, nameof(SanguoGameLoopController), dataJson);
    }

    private void TryRunSaveLoadE2eFromCmdline()
    {
        try
        {
            var debug = string.Equals(System.Environment.GetEnvironmentVariable("SC_E2E_DEBUG_ARGS"), "1", StringComparison.Ordinal);

            var userArgs = OS.GetCmdlineUserArgs();
            var cmdArgs = OS.GetCmdlineArgs();

            var args = userArgs;
            if (args is null || args.Length == 0)
            {
                args = cmdArgs;
            }
            if (args is null || args.Length == 0)
            {
                if (debug)
                {
                    GD.Print("[E2E_SAVELOAD] cmdline args empty");
                }
                return;
            }

            var mode = TryGetCmdArg(args, "--sc-saveload-mode");
            if (string.IsNullOrWhiteSpace(mode))
            {
                if (debug)
                {
                    GD.Print($"[E2E_SAVELOAD] mode not found; user_args={string.Join(' ', userArgs ?? Array.Empty<string>())} cmd_args={string.Join(' ', cmdArgs ?? Array.Empty<string>())}");
                }
                return;
            }

            var slot = TryGetCmdArg(args, "--sc-saveload-slot") ?? "e2e";
            var correlationId = TryGetCmdArg(args, "--sc-saveload-correlation") ?? Guid.NewGuid().ToString("N");

            if (string.Equals(mode, "save", StringComparison.OrdinalIgnoreCase))
            {
                CallDeferred(nameof(E2eSaveDeferred), correlationId, slot);
                return;
            }

            if (string.Equals(mode, "load", StringComparison.OrdinalIgnoreCase))
            {
                CallDeferred(nameof(E2eLoadDeferred), correlationId, slot);
            }
        }
        catch
        {
        }
    }

    private static string? TryGetCmdArg(string[] args, string key)
    {
        for (var i = 0; i < args.Length; i++)
        {
            if (!string.Equals(args[i], key, StringComparison.OrdinalIgnoreCase))
                continue;
            if (i + 1 >= args.Length)
                return null;
            return args[i + 1];
        }
        return null;
    }

    private async void E2eSaveDeferred(string correlationId, string saveSlotId)
    {
        try
        {
            var (started, _) = await TryStartNewGameAsync(correlationId: correlationId, causationId: "e2e.saveload.save");
            if (!started)
            {
                GD.Print("[E2E_SAVELOAD] failed mode=save reason=start_failed");
                return;
            }

            var store = ResolveDataStore();
            if (store == null || _bus == null || _turnManager == null)
            {
                GD.Print("[E2E_SAVELOAD] failed mode=save reason=missing_ports");
                return;
            }

            var service = new SanguoSaveLoadService(_bus, store);
            var snapshot = _turnManager.ExportSaveSnapshot();
            await service.SaveGameAsync(snapshot: snapshot, saveSlotId: saveSlotId, correlationId: correlationId, causationId: "e2e.saveload.save");

            GD.Print($"[E2E_SAVELOAD] saved slot={saveSlotId} turn={snapshot.TurnNumber} active_index={snapshot.ActivePlayerIndex} date={snapshot.Year:D4}-{snapshot.Month:D2}-{snapshot.Day:D2}");
        }
        catch (Exception ex)
        {
            GD.Print($"[E2E_SAVELOAD] failed mode=save error={ex.Message}");
        }
        finally
        {
            GetTree().Quit();
        }
    }

    private async void E2eLoadDeferred(string correlationId, string saveSlotId)
    {
        try
        {
            if (_bus == null)
            {
                GD.Print("[E2E_SAVELOAD] failed mode=load reason=missing_bus");
                return;
            }

            var store = ResolveDataStore();
            if (store == null)
            {
                GD.Print("[E2E_SAVELOAD] failed mode=load reason=missing_store");
                return;
            }

            if (_map == null)
            {
                var loader = ResolveResourceLoader();
                if (loader == null)
                {
                    GD.Print("[E2E_SAVELOAD] failed mode=load reason=missing_loader");
                    return;
                }

                if (!SanguoMapConfigLoader.TryLoadMap(loader, correlationId, out var map, out _, out _))
                {
                    GD.Print("[E2E_SAVELOAD] failed mode=load reason=map_load_failed");
                    return;
                }

                _map = map;
                LoadMapActions(map);
            }

            _turnManager ??= CreateNewTurnManager(_map!);

            var service = new SanguoSaveLoadService(_bus, store);
            var snapshot = await service.LoadGameAsync(saveSlotId: saveSlotId, correlationId: correlationId, causationId: "e2e.saveload.load");
            _turnManager.RestoreFromSaveSnapshot(snapshot);
            _started = true;

            GD.Print($"[E2E_SAVELOAD] loaded slot={saveSlotId} turn={snapshot.TurnNumber} active_index={snapshot.ActivePlayerIndex} date={snapshot.Year:D4}-{snapshot.Month:D2}-{snapshot.Day:D2}");
        }
        catch (Exception ex)
        {
            GD.Print($"[E2E_SAVELOAD] failed mode=load error={ex.Message}");
        }
        finally
        {
            GetTree().Quit();
        }
    }

    private SanguoTurnManager CreateNewTurnManager(SanguoMapDefinition map, GameStartConfig? startConfig = null)
    {
        var economyRules = SanguoEconomyRules.Default;
        var playerOrder = startConfig != null
            ? BuildDefaultPlayerOrder(startConfig.PlayersCount)
            : new[] { "p1", "ai-1" };
        var startingMoney = startConfig?.StartingMoneyPreset ?? 300;
        var players = playerOrder
            .Select(id => new SanguoPlayer(playerId: id, money: startingMoney, positionIndex: 0, economyRules: economyRules))
            .ToArray();

        var citiesById = BuildCitiesByIdFromMap(map);

        var boardState = new SanguoBoardState(players: players, citiesById: citiesById);
        var treasury = new SanguoTreasury();
        var economy = new SanguoEconomyManager(_bus!);

        return new SanguoTurnManager(
            bus: _bus!,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            totalPositionsHint: map.TileCount);
    }

    private IResourceLoader? ResolveResourceLoader()
    {
        try
        {
            var root = GetNodeOrNull<Node>("/root/CompositionRoot");
            if (root is CompositionRoot cr && cr.ResourceLoader != null)
            {
                return cr.ResourceLoader;
            }
        }
        catch
        {
        }

        var portNode = GetNodeOrNull<Node>("/root/CompositionRoot/ResourceLoaderPort");
        if (portNode is IResourceLoader port)
        {
            return port;
        }

        // Fallback for minimal scenes/tests where CompositionRoot is not available.
        return new ResourceLoaderAdapter();
    }

    private void PublishMenuStartFailed(string correlationId, string reason)
    {
        if (_bus == null)
        {
            return;
        }

        try
        {
            var data = JsonSerializer.Serialize(new Dictionary<string, string>
            {
                ["correlationId"] = correlationId ?? string.Empty,
                ["reason"] = reason ?? string.Empty,
            }, UiJsonOptions);

            _bus.PublishSimple(UiMenuStartFailed, "runtime", data);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SanguoGameLoopController: failed to publish ui.menu.start.failed: {ex.Message}");
        }
    }

    private IDataStore? ResolveDataStore()
    {
        try
        {
            var root = GetNodeOrNull<Node>("/root/CompositionRoot");
            if (root is CompositionRoot cr && cr.DataStore != null)
            {
                return cr.DataStore;
            }
        }
        catch
        {
        }

        var store = GetNodeOrNull<DataStoreAdapter>("/root/DataStore");
        return store;
    }

    private static Dictionary<string, City> BuildCitiesByIdFromMap(SanguoMapDefinition map)
    {
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal);
        foreach (var tile in map.Tiles)
        {
            var tileType = (tile.TileType ?? string.Empty).Trim();
            if (!string.Equals(tileType, SanguoTileDefinition.TileTypeCity, StringComparison.OrdinalIgnoreCase))
                continue;

            citiesById[tile.TileId] = new City(
                id: tile.TileId,
                name: tile.Name,
                regionId: tile.StateId,
                basePrice: MoneyValue.FromDecimal(tile.PurchasePrice),
                baseToll: MoneyValue.FromDecimal(tile.TollPrice),
                positionIndex: tile.PositionIndex);
        }

        return citiesById;
    }

    private async void AdvanceTurnDeferred(string correlationId)
    {
        try
        {
            if (_turnManager == null)
            {
                return;
            }

            await _turnManager.ExecuteHumanRollDiceAndResolveAsync(correlationId: correlationId, causationId: UiHudDiceRoll);
            if (ShouldWaitForHumanTileAction(correlationId))
            {
                _awaitingHumanTileAction = true;
                _awaitingHumanActionCorrelationId = correlationId;
                return;
            }

            await _turnManager.AdvanceTurnAsync(correlationId: correlationId, causationId: UiHudDiceRoll);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SanguoGameLoopController: failed to advance turn: {ex.Message}");
        }
        finally
        {
            if (!_awaitingHumanTileAction)
            {
                _advanceQueued = false;
            }
        }

        TryQueueAiAutoAdvanceIfNeeded();
    }

    private bool ShouldWaitForHumanTileAction(string correlationId)
    {
        if (_map == null || _actionsByIndex.Count == 0)
        {
            return false;
        }

        if (string.IsNullOrWhiteSpace(correlationId))
        {
            return false;
        }

        if (!string.Equals(_lastHumanMoveCorrelationId, correlationId, StringComparison.Ordinal))
        {
            return false;
        }

        if (!_actionsByIndex.TryGetValue(_lastHumanMoveToIndex, out var actions))
        {
            return false;
        }

        return actions.Length > 0;
    }

    private async void AdvanceAfterHumanTileActionDeferred(string correlationId, string action)
    {
        try
        {
            if (!_started || _turnManager == null)
            {
                return;
            }

            await _turnManager.ExecuteHumanTileActionAsync(action: action, correlationId: correlationId, causationId: UiTileActionSelected);
            await _turnManager.AdvanceTurnAsync(correlationId: correlationId, causationId: UiTileActionSelected);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SanguoGameLoopController: failed to apply tile action: {ex.Message}");
        }
        finally
        {
            _awaitingHumanTileAction = false;
            _awaitingHumanActionCorrelationId = string.Empty;
            _advanceQueued = false;
        }

        TryQueueAiAutoAdvanceIfNeeded();
    }

    private void TryQueueAiAutoAdvanceIfNeeded()
    {
        if (!_started || _turnManager == null)
            return;

        if (_advanceQueued)
            return;

        if (!SanguoGlueJson.IsAiPlayerId(_activePlayerId))
            return;

        if (!_aiAutoAdvanceRequested)
            return;

        _advanceQueued = true;
        _aiAutoAdvanceRequested = false;
        var correlationId = Guid.NewGuid().ToString("N");
        CallDeferred(nameof(AdvanceAiTurnDeferred), correlationId, _aiAutoAdvanceDelaySec);
    }

    private async void AdvanceAiTurnDeferred(string correlationId, double delaySec)
    {
        try
        {
            if (!_started || _turnManager == null)
                return;

        if (!SanguoGlueJson.IsAiPlayerId(_activePlayerId))
            return;

            // Give the board view time to animate AI moves (if any) before the next turn starts.
            var timer = GetTree().CreateTimer(delaySec <= 0 ? AiAutoAdvanceDelaySeconds : delaySec);
            await ToSignal(timer, SceneTreeTimer.SignalName.Timeout);

            await _turnManager.AdvanceTurnAsync(correlationId: correlationId, causationId: AiAutoAdvanceCausationId);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SanguoGameLoopController: failed to auto-advance AI turn: {ex.Message}");
        }
        finally
        {
            _advanceQueued = false;
        }

        // In case multiple AIs exist, keep advancing until a non-AI player becomes active.
        TryQueueAiAutoAdvanceIfNeeded();
    }

    private void LoadMapActions(SanguoMapDefinition map)
    {
        _actionsByIndex.Clear();
        foreach (var tile in map.Tiles)
        {
            if (tile.Actions is null)
            {
                _actionsByIndex[tile.PositionIndex] = Array.Empty<string>();
                continue;
            }

            var list = new List<string>();
            foreach (var a in tile.Actions)
            {
                var v = (a ?? string.Empty).Trim();
                if (!string.IsNullOrWhiteSpace(v))
                {
                    list.Add(v);
                }
            }

            _actionsByIndex[tile.PositionIndex] = list.ToArray();
        }
    }

}
