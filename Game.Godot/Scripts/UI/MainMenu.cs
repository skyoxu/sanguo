using Godot;
using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using Game.Core.Services.Sanguo;
using Game.Godot.Adapters;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

public partial class MainMenu : Control
{
    private const string EmptyJsonObject = "{}";
    private const string UiMenuStart = "ui.menu.start";
    private const string UiMenuSettings = "ui.menu.settings";
    private const string UiMenuQuit = "ui.menu.quit";
    private const string UiMenuLoad = "ui.menu.load";
    private const string UiMenuStartFailed = "ui.menu.start.failed";
    private const string UiMenuHelp = "ui.menu.help";

    private const string TurnStarted = "core.sanguo.game.turn.started";
    private const string HelpTutorialGroup = "help_tutorial";
    private const string HelpTutorialScenePath = "res://Game.Godot/Scenes/UI/HelpTutorial.tscn";

    private static readonly int[] AllowedPlayersCounts = { 2, 3, 4 };
    private static readonly int[] AllowedStartingMoneyPresets = { 5000, 10000, 20000 };
    private static readonly int[] AllowedGlobalEventIntervals = { 5, 10, 20 };

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 16,
    };

    private Button _btnPlay = default!;
    private Button _btnLoad = default!;
    private Button _btnSettings = default!;
    private Button? _btnHelp;
    private Button _btnQuit = default!;
    private Control _loadPanel = default!;
    private Label _statusLabel = default!;

    private OptionButton _mapOption = default!;
    private OptionButton _playersOption = default!;
    private OptionButton _characterOption = default!;
    private OptionButton _startingMoneyOption = default!;
    private OptionButton _globalEventIntervalOption = default!;
    private Label _aiFillLabel = default!;
    private ResourceLoaderAdapter? _fallbackResourceLoader;

    private EventBusAdapter? _bus;
    private bool _startPending;
    private bool _newGameConfigReady;

    public override void _Ready()
    {
        _btnPlay = GetNode<Button>("VBox/BtnPlay");
        _btnLoad = GetNode<Button>("VBox/BtnLoad");
        _btnSettings = GetNode<Button>("VBox/BtnSettings");
        _btnHelp = GetNodeOrNull<Button>("VBox/BtnHelp");
        _btnQuit = GetNode<Button>("VBox/BtnQuit");
        _loadPanel = GetNode<Control>("LoadPanel");
        _statusLabel = GetNode<Label>("StatusLabel");

        _mapOption = GetNode<OptionButton>("NewGameConfig/VBox/MapOption");
        _playersOption = GetNode<OptionButton>("NewGameConfig/VBox/PlayersOption");
        _characterOption = GetNode<OptionButton>("NewGameConfig/VBox/CharacterOption");
        _startingMoneyOption = GetNode<OptionButton>("NewGameConfig/VBox/StartingMoneyOption");
        _globalEventIntervalOption = GetNode<OptionButton>("NewGameConfig/VBox/GlobalEventIntervalOption");
        _aiFillLabel = GetNode<Label>("NewGameConfig/VBox/AiFillLabel");

        _bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (_bus != null)
        {
            var callable = new Callable(this, nameof(OnDomainEventEmitted));
            if (!_bus.IsConnected(EventBusAdapter.SignalName.DomainEventEmitted, callable))
            {
                _bus.Connect(EventBusAdapter.SignalName.DomainEventEmitted, callable);
            }
        }

        _btnPlay.Pressed += OnPlayPressed;
        _btnLoad.Pressed += OnLoadPressed;
        _btnSettings.Pressed += OnSettingsPressed;
        if (_btnHelp != null)
        {
            _btnHelp.Pressed += OnHelpPressed;
        }
        _btnQuit.Pressed += OnQuitPressed;

        _loadPanel.Visible = false;
        _statusLabel.Visible = false;
        _statusLabel.Text = string.Empty;
        _startPending = false;

        WireNewGameConfigControls();
        PopulateNewGameConfigControls();
        RefreshStartAvailability();
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
        _fallbackResourceLoader = null;
    }

    public void ShowMenu() => Visible = true;
    public void HideMenu() => Visible = false;

    private void SetButtonsEnabled(bool enabled)
    {
        _btnPlay.Disabled = !enabled;
        _btnLoad.Disabled = !enabled;
        _btnSettings.Disabled = !enabled;
        if (_btnHelp != null)
        {
            _btnHelp.Disabled = !enabled;
        }
        _btnQuit.Disabled = !enabled;
    }

    private void ShowStatus(string message)
    {
        _statusLabel.Text = message ?? string.Empty;
        _statusLabel.Visible = !string.IsNullOrWhiteSpace(_statusLabel.Text);
    }

    private void ClearStatus()
    {
        _statusLabel.Text = string.Empty;
        _statusLabel.Visible = false;
    }

    private void Publish(string type, string source, string dataJson = EmptyJsonObject)
    {
        _bus?.PublishSimple(type, source, dataJson);
    }

    private void OnPlayPressed()
    {
        if (_startPending)
        {
            return;
        }

        string? startConfigJson = null;
        if (_newGameConfigReady)
        {
            if (!TryBuildStartConfigJson(out startConfigJson, out var error))
            {
                // Do not block the start event on data/resource issues. The runtime glue publishes
                // ui.menu.start.failed with a deterministic reason when it cannot start.
                //
                // We still block for clearly user-driven missing selections to avoid starting with defaults silently.
                if (string.Equals(error, "map_missing", StringComparison.Ordinal) ||
                    string.Equals(error, "character_missing", StringComparison.Ordinal) ||
                    string.Equals(error, "players_count_invalid", StringComparison.Ordinal))
                {
                    _startPending = false;
                    SetButtonsEnabled(true);
                    ShowMenu();
                    ShowStatus("Invalid setup: " + error);
                    return;
                }

                startConfigJson = "{}";
            }
        }

        _startPending = true;
        ClearStatus();
        ShowStatus("Starting...");
        SetButtonsEnabled(false);
        Publish(UiMenuStart, "ui", startConfigJson ?? "{}");
    }

    private void OnSettingsPressed()
    {
        Publish(UiMenuSettings, "ui");
    }

    private void OnLoadPressed()
    {
        Publish(UiMenuLoad, "ui");
        _loadPanel.Visible = true;
    }

    private void OnQuitPressed()
    {
        Publish(UiMenuQuit, "ui");
    }

    private void OnHelpPressed()
    {
        Publish(UiMenuHelp, "ui");
        ToggleHelpTutorial();
    }

    public void ToggleHelpTutorial()
    {
        var nodes = GetTree().GetNodesInGroup(HelpTutorialGroup);
        if (nodes.Count > 0)
        {
            var anyVisible = false;
            foreach (var node in nodes)
            {
                if (node is CanvasItem ci && ci.Visible)
                {
                    anyVisible = true;
                    break;
                }
            }

            var newVisible = !anyVisible;
            foreach (var node in nodes)
            {
                if (node is CanvasItem ci)
                {
                    ci.Visible = newVisible;
                }
            }

            return;
        }

        if (!ResourceLoader.Exists(HelpTutorialScenePath))
        {
            return;
        }

        var packed = GD.Load<PackedScene>(HelpTutorialScenePath);
        var instance = packed?.Instantiate();
        if (instance is CanvasItem canvas)
        {
            GetTree().Root.AddChild(canvas);
            canvas.Visible = true;
        }
    }

    private void OnDomainEventEmitted(string type, string _source, string dataJson, string _id, string _specVersion, string _dataContentType, string _timestampIso)
    {
        if (!_startPending)
        {
            return;
        }

        if (string.Equals(type, TurnStarted, StringComparison.Ordinal))
        {
            _startPending = false;
            ClearStatus();
            SetButtonsEnabled(true);
            HideMenu();
            return;
        }

        if (string.Equals(type, UiMenuStartFailed, StringComparison.Ordinal))
        {
            _startPending = false;
            SetButtonsEnabled(true);
            ShowMenu();
            ShowStatus("Start failed: " + (TryExtractStartFailedReason(dataJson) ?? "unknown"));
        }
    }

    private void WireNewGameConfigControls()
    {
        _playersOption.ItemSelected += _ => RefreshStartAvailability();
        _characterOption.ItemSelected += _ => RefreshStartAvailability();
        _startingMoneyOption.ItemSelected += _ => RefreshStartAvailability();
        _globalEventIntervalOption.ItemSelected += _ => RefreshStartAvailability();
        _mapOption.ItemSelected += _ => RefreshStartAvailability();
    }

    private void PopulateNewGameConfigControls()
    {
        _newGameConfigReady = false;

        try
        {
            _playersOption.Clear();
            foreach (var n in AllowedPlayersCounts)
            {
                _playersOption.AddItem(n.ToString(), n);
            }

            _startingMoneyOption.Clear();
            foreach (var n in AllowedStartingMoneyPresets)
            {
                _startingMoneyOption.AddItem(n.ToString(), n);
            }

            _globalEventIntervalOption.Clear();
            foreach (var n in AllowedGlobalEventIntervals)
            {
                _globalEventIntervalOption.AddItem(n.ToString(), n);
            }

            _mapOption.Clear();
            var loader = ResolveResourceLoader();
            var pack = ResolveContentPack(loader);
            if (SanguoMapsCatalogLoader.TryLoadMapsCatalog(loader, pack, out var maps, out _))
            {
                foreach (var entry in maps.Maps.OrderBy(m => m.NameKey, StringComparer.Ordinal))
                {
                    var label = string.IsNullOrWhiteSpace(entry.NameKey) ? entry.MapId : entry.NameKey;
                    var idx = _mapOption.ItemCount;
                    _mapOption.AddItem(label);
                    _mapOption.SetItemMetadata(idx, entry.MapId);
                }
            }

            if (_mapOption.ItemCount == 0)
            {
                var idx = _mapOption.ItemCount;
                _mapOption.AddItem("map001");
                _mapOption.SetItemMetadata(idx, "map001");
            }

            _characterOption.Clear();
            if (SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, pack, out var chars, out _))
            {
                foreach (var c in chars.Characters.OrderBy(x => x.NameKey, StringComparer.Ordinal))
                {
                    var label = string.IsNullOrWhiteSpace(c.NameKey) ? c.CharacterId : c.NameKey;
                    var idx = _characterOption.ItemCount;
                    _characterOption.AddItem(label);
                    _characterOption.SetItemMetadata(idx, c.CharacterId);
                }
            }

            if (_characterOption.ItemCount == 0)
            {
                var idx = _characterOption.ItemCount;
                _characterOption.AddItem("c1");
                _characterOption.SetItemMetadata(idx, "c1");
            }

            _playersOption.Select(0);
            _startingMoneyOption.Select(1);
            _globalEventIntervalOption.Select(1);
            _mapOption.Select(0);
            _characterOption.Select(0);

            _newGameConfigReady = true;
        }
        catch (Exception ex)
        {
            GD.PushWarning($"MainMenu: failed to initialize new-game config controls: {ex.Message}");
            _newGameConfigReady = false;
        }
    }

    private void RefreshStartAvailability()
    {
        var playersCount = GetSelectedPlayersCount();
        _aiFillLabel.Text = playersCount > 0 ? $"AI slots: {Math.Max(0, playersCount - 1)}" : "AI slots: -";

        if (_startPending)
        {
            return;
        }

        if (!_newGameConfigReady)
        {
            _btnPlay.Disabled = false;
            return;
        }

        _btnPlay.Disabled = !TryBuildStartConfigJson(out _, out _);
    }

    private bool TryBuildStartConfigJson(out string? json, out string error)
    {
        json = null;
        error = string.Empty;

        var mapId = GetSelectedMapId();
        if (string.IsNullOrWhiteSpace(mapId))
        {
            error = "map_missing";
            return false;
        }

        var playersCount = GetSelectedPlayersCount();
        var startingMoney = GetSelectedStartingMoneyPreset();
        var interval = GetSelectedGlobalEventIntervalTurns();
        var playerCharacterId = GetSelectedCharacterId();
        if (string.IsNullOrWhiteSpace(playerCharacterId))
        {
            error = "character_missing";
            return false;
        }

        var seed = unchecked((int)(Time.GetTicksMsec() % int.MaxValue));

        var loader = ResolveResourceLoader();
        var pack = ResolveContentPack(loader);
        var assigns = BuildCharacterAssignments(loader, pack, playersCount, playerCharacterId, seed, out var assignsError);
        if (assigns == null)
        {
            error = assignsError;
            return false;
        }

        var cfg = new GameStartConfig(
            MapId: mapId,
            PlayersCount: playersCount,
            StartingMoneyPreset: startingMoney,
            GlobalEventIntervalTurns: interval,
            RandomSeed: seed,
            CharacterAssignments: assigns);

        if (!GameStartConfigValidator.TryValidate(cfg, out var errors))
        {
            error = string.Join(" | ", errors.Take(3));
            return false;
        }

        json = JsonSerializer.Serialize(cfg);
        return true;
    }

    private static IReadOnlyDictionary<string, string>? BuildCharacterAssignments(
        IResourceLoader loader,
        SanguoContentPackPaths? pack,
        int playersCount,
        string playerCharacterId,
        int seed,
        out string error)
    {
        error = string.Empty;

        if (!SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, pack, out var catalog, out var loadError))
        {
            error = loadError;
            return null;
        }

        var ids = catalog.Characters.Select(c => c.CharacterId).ToArray();
        if (!SanguoCharacterAssignmentsGenerator.TryBuildAssignments(ids, playersCount, playerCharacterId, seed, out var assigns, out error))
        {
            return null;
        }

        return assigns;
    }

    private IResourceLoader ResolveResourceLoader()
    {
        var portNode = GetNodeOrNull<Node>("/root/CompositionRoot/ResourceLoaderPort");
        if (portNode is IResourceLoader port)
        {
            return port;
        }

        if (_fallbackResourceLoader != null && GodotObject.IsInstanceValid(_fallbackResourceLoader))
        {
            return _fallbackResourceLoader;
        }

        _fallbackResourceLoader = new ResourceLoaderAdapter { Name = "ResourceLoaderFallback" };
        AddChild(_fallbackResourceLoader);
        return _fallbackResourceLoader;
    }

    private static SanguoContentPackPaths? ResolveContentPack(IResourceLoader loader)
    {
        return SanguoContentPackResolver.TryResolveDefaultPack(loader, out var pack, out _)
            ? pack
            : null;
    }

    private string GetSelectedMapId()
    {
        if (_mapOption.ItemCount == 0)
        {
            return string.Empty;
        }

        var meta = _mapOption.GetItemMetadata(_mapOption.Selected);
        return meta.VariantType == Variant.Type.String ? meta.AsString() : string.Empty;
    }

    private string GetSelectedCharacterId()
    {
        if (_characterOption.ItemCount == 0)
        {
            return string.Empty;
        }

        var meta = _characterOption.GetItemMetadata(_characterOption.Selected);
        return meta.VariantType == Variant.Type.String ? meta.AsString() : string.Empty;
    }

    private int GetSelectedPlayersCount()
    {
        if (_playersOption.ItemCount == 0)
        {
            return 0;
        }

        var value = _playersOption.GetItemId(_playersOption.Selected);
        return value > 0 ? value : 0;
    }

    private int GetSelectedStartingMoneyPreset()
    {
        if (_startingMoneyOption.ItemCount == 0)
        {
            return 0;
        }

        var value = _startingMoneyOption.GetItemId(_startingMoneyOption.Selected);
        return value > 0 ? value : 0;
    }

    private int GetSelectedGlobalEventIntervalTurns()
    {
        if (_globalEventIntervalOption.ItemCount == 0)
        {
            return 0;
        }

        var value = _globalEventIntervalOption.GetItemId(_globalEventIntervalOption.Selected);
        return value > 0 ? value : 0;
    }

    private static string? TryExtractStartFailedReason(string dataJson)
    {
        if (string.IsNullOrWhiteSpace(dataJson))
        {
            return null;
        }

        if (dataJson.Length > 65536)
        {
            return null;
        }

        try
        {
            using var doc = JsonDocument.Parse(dataJson, new JsonDocumentOptions
            {
                AllowTrailingCommas = true,
                CommentHandling = JsonCommentHandling.Skip,
                MaxDepth = 16,
            });

            if (doc.RootElement.ValueKind != JsonValueKind.Object)
            {
                return null;
            }

            if (doc.RootElement.TryGetProperty("reason", out var reason) && reason.ValueKind == JsonValueKind.String)
            {
                return reason.GetString();
            }

            if (doc.RootElement.TryGetProperty("message", out var msg) && msg.ValueKind == JsonValueKind.String)
            {
                return msg.GetString();
            }
        }
        catch
        {
        }

        try
        {
            var dict = JsonSerializer.Deserialize<System.Collections.Generic.Dictionary<string, object>>(dataJson, JsonOptions);
            if (dict == null) return null;
            if (dict.TryGetValue("reason", out var r) && r != null) return r.ToString();
            if (dict.TryGetValue("message", out var m) && m != null) return m.ToString();
        }
        catch
        {
        }

        return null;
    }
}
