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
    private const string UiMenuReturn = "ui.menu.return";
    private const string UiMenuStartFailed = "ui.menu.start.failed";
    private const string UiMenuHelp = "ui.menu.help";
    private const string StartButtonLabelKey = "ui.menu.start_game";
    private const string MenuPlayLabelKey = "ui.menu.play";
    private const string MenuLoadLabelKey = "ui.menu.load";
    private const string MenuSettingsLabelKey = "ui.menu.settings";
    private const string MenuHelpLabelKey = "ui.menu.help";
    private const string MenuQuitLabelKey = "ui.menu.quit";
    private const string MenuNewGameLabelKey = "ui.menu.new_game";
    private const string MenuMapLabelKey = "ui.menu.map";
    private const string MenuPlayersLabelKey = "ui.menu.players";
    private const string MenuCharacterLabelKey = "ui.menu.character";
    private const string MenuStartingMoneyLabelKey = "ui.menu.starting_money";
    private const string MenuGlobalEventIntervalLabelKey = "ui.menu.global_event_interval";
    private const string MenuActiveStrategemLabelKey = "ui.menu.active_strategem";
    private const string MenuPassiveStrategemLabelKey = "ui.menu.passive_strategem";
    private const string MenuAiSlotsLabelKey = "ui.menu.ai_slots";
    private const string MenuBackLabelKey = "ui.menu.back";
    private const string MenuStatusStartingKey = "ui.menu.status.starting";
    private const string MenuStatusInvalidSetupKey = "ui.menu.status.invalid_setup";
    private const string MenuStatusStartFailedKey = "ui.menu.status.start_failed";
    private const string MenuErrorMapMissingKey = "ui.menu.error.map_missing";
    private const string MenuErrorCharacterMissingKey = "ui.menu.error.character_missing";
    private const string MenuErrorPlayersInvalidKey = "ui.menu.error.players_invalid";

    private const string TurnStarted = SanguoGameTurnStarted.EventType;
    private const string GameLoaded = SanguoGameLoaded.EventType;
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
    private Button _btnStart = default!;
    private Button _btnBack = default!;
    private Button _btnCharPrev = default!;
    private Button _btnCharNext = default!;
    private Button[] _characterSlots = Array.Empty<Button>();
    private Control _loadPanel = default!;
    private Label _statusLabel = default!;
    private Control _newGameConfig = default!;
    private Control _configCenter = default!;
    private Label _titleLabel = default!;
    private Label _mapLabel = default!;
    private Label _playersLabel = default!;
    private Label _characterLabel = default!;
    private Label _moneyLabel = default!;
    private Label _globalEventLabel = default!;
    private Label _activeStrategemLabel = default!;
    private Label _passiveStrategemLabel = default!;
    private TextureRect _characterPortrait = default!;
    private Label _characterName = default!;
    private Label _characterDesc = default!;
    private Label _combatKey = default!;
    private Label _startMoneyStepKey = default!;
    private Label _buyStepKey = default!;
    private Label _tollStepKey = default!;
    private Label _incomeStepKey = default!;
    private Label _buildStepKey = default!;
    private Label _upgradeStepKey = default!;
    private Label _combatValue = default!;
    private Label _startMoneyStepValue = default!;
    private Label _buyStepValue = default!;
    private Label _tollStepValue = default!;
    private Label _incomeStepValue = default!;
    private Label _buildStepValue = default!;
    private Label _upgradeStepValue = default!;

    private OptionButton _mapOption = default!;
    private OptionButton _playersOption = default!;
    private OptionButton _startingMoneyOption = default!;
    private OptionButton _globalEventIntervalOption = default!;
    private OptionButton _activeStrategemOption = default!;
    private OptionButton _passiveStrategemOption = default!;
    private Label _aiFillLabel = default!;
    private ResourceLoaderAdapter? _fallbackResourceLoader;

    private EventBusAdapter? _bus;
    private bool _startPending;
    private bool _loadPending;
    private bool _newGameConfigReady;
    private string _aiSlotsLabel = "AI slots";
    private List<SanguoCharacterDefinition> _characters = new();
    private string _selectedCharacterId = string.Empty;
    private int _characterCarouselOffset;

    public override void _Ready()
    {
        _btnPlay = GetNode<Button>("MenuRow/MenuBox/BtnPlay");
        _btnLoad = GetNode<Button>("MenuRow/MenuBox/BtnLoad");
        _btnSettings = GetNode<Button>("MenuRow/MenuBox/BtnSettings");
        _btnHelp = GetNodeOrNull<Button>("MenuRow/MenuBox/BtnHelp");
        _btnQuit = GetNode<Button>("MenuRow/MenuBox/BtnQuit");
        _loadPanel = GetNode<Control>("LoadPanel");
        _statusLabel = GetNode<Label>("StatusLabel");
        _configCenter = GetNode<Control>("ConfigCenter");
        _newGameConfig = GetNode<Control>("ConfigCenter/NewGameConfig");
        _btnStart = GetNode<Button>("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart");
        _btnBack = GetNode<Button>("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnBack");
        _btnCharPrev = GetNode<Button>("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/CharacterCarousel/BtnCharPrev");
        _btnCharNext = GetNode<Button>("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/CharacterCarousel/BtnCharNext");
        _characterSlots = new[]
        {
            GetNode<Button>("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/CharacterCarousel/CharacterGrid/CharSlot0"),
            GetNode<Button>("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/CharacterCarousel/CharacterGrid/CharSlot1"),
            GetNode<Button>("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/CharacterCarousel/CharacterGrid/CharSlot2"),
            GetNode<Button>("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/CharacterCarousel/CharacterGrid/CharSlot3"),
            GetNode<Button>("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/CharacterCarousel/CharacterGrid/CharSlot4"),
            GetNode<Button>("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/CharacterCarousel/CharacterGrid/CharSlot5"),
            GetNode<Button>("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/CharacterCarousel/CharacterGrid/CharSlot6"),
            GetNode<Button>("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/CharacterCarousel/CharacterGrid/CharSlot7"),
        };

        _titleLabel = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/Title");
        _mapLabel = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/MapLabel");
        _playersLabel = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/PlayersLabel");
        _characterLabel = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterLabel");
        _moneyLabel = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/MoneyLabel");
        _globalEventLabel = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/GlobalEventLabel");
        _activeStrategemLabel = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/ActiveStrategemLabel");
        _passiveStrategemLabel = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/PassiveStrategemLabel");

        _characterPortrait = GetNode<TextureRect>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/Portrait");
        _characterName = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterName");
        _characterDesc = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterDesc");
        _combatKey = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterStats/CombatKey");
        _startMoneyStepKey = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterStats/StartMoneyStepKey");
        _buyStepKey = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterStats/BuyStepKey");
        _tollStepKey = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterStats/TollStepKey");
        _incomeStepKey = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterStats/IncomeStepKey");
        _buildStepKey = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterStats/BuildStepKey");
        _upgradeStepKey = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterStats/UpgradeStepKey");
        _combatValue = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterStats/CombatValue");
        _startMoneyStepValue = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterStats/StartMoneyStepValue");
        _buyStepValue = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterStats/BuyStepValue");
        _tollStepValue = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterStats/TollStepValue");
        _incomeStepValue = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterStats/IncomeStepValue");
        _buildStepValue = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterStats/BuildStepValue");
        _upgradeStepValue = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/CharacterInfo/Margin/VBox/CharacterStats/UpgradeStepValue");

        _mapOption = GetNode<OptionButton>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/MapOption");
        _playersOption = GetNode<OptionButton>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/PlayersOption");
        _startingMoneyOption = GetNode<OptionButton>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/StartingMoneyOption");
        _globalEventIntervalOption = GetNode<OptionButton>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/GlobalEventIntervalOption");
        _activeStrategemOption = GetNode<OptionButton>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/ActiveStrategemOption");
        _passiveStrategemOption = GetNode<OptionButton>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/PassiveStrategemOption");
        _aiFillLabel = GetNode<Label>("ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/AiFillLabel");

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
        _btnStart.Pressed += OnStartPressed;
        _btnBack.Pressed += OnBackPressed;
        if (_btnHelp != null)
        {
            _btnHelp.Pressed += OnHelpPressed;
        }
        _btnQuit.Pressed += OnQuitPressed;

        SetConfigPanelVisible(false);
        _loadPanel.Visible = false;
        _statusLabel.Visible = false;
        _statusLabel.Text = string.Empty;
        _startPending = false;
        _loadPending = false;
        ApplyLocalizedTexts();

        WireNewGameConfigControls();
        PopulateNewGameConfigControls();
        RefreshStartAvailability();
        ShowMenu();
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

    public void ShowMenu()
    {
        Visible = true;
        SetConfigPanelVisible(false);
        _loadPanel.Visible = false;
        _loadPending = false;
        SetOverlayVisible(false);
        SetOverlayInputEnabled(false);
        SetBoardInputEnabled(false);
        SetBoardVisible(false);
        SetHudVisible(false);
    }

    public void HideMenu()
    {
        Visible = false;
        SetOverlayVisible(true);
        SetOverlayInputEnabled(true);
        SetBoardInputEnabled(true);
        SetBoardVisible(true);
        ResetBoardCameraIfNeeded();
    }

    private void SetMenuButtonsEnabled(bool enabled)
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

    private void SetStartButtonEnabled(bool enabled)
    {
        _btnStart.Disabled = !enabled;
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

        ClearStatus();
        SetConfigPanelVisible(true);
        RefreshStartAvailability();
    }

    private void OnStartPressed()
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
                    string.Equals(error, "active_strategem_missing", StringComparison.Ordinal) ||
                    string.Equals(error, "passive_strategem_missing", StringComparison.Ordinal) ||
                    string.Equals(error, "players_count_invalid", StringComparison.Ordinal))
                {
                    _startPending = false;
                    SetMenuButtonsEnabled(true);
                    SetStartButtonEnabled(true);
                    Visible = true;
                    SetConfigPanelVisible(true);
                    SetHudVisible(false);
                    ShowStatus($"{TranslateOrFallback(MenuStatusInvalidSetupKey, "Invalid setup")}: {TranslateStartError(error)}");
                    return;
                }

                startConfigJson = "{}";
            }
        }

        _startPending = true;
        ClearStatus();
        ShowStatus(TranslateOrFallback(MenuStatusStartingKey, "Starting..."));
        SetMenuButtonsEnabled(false);
        SetStartButtonEnabled(false);
        Publish(UiMenuStart, "ui", startConfigJson ?? "{}");
    }

    private void OnBackPressed()
    {
        if (_startPending)
        {
            return;
        }

        ClearStatus();
        SetConfigPanelVisible(false);
    }

    private void OnSettingsPressed()
    {
        Publish(UiMenuSettings, "ui");
    }

    private void OnLoadPressed()
    {
        _loadPending = true;
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
            var helpLayer = GetNodeOrNull<Node>("/root/Main/HelpLayer");
            if (helpLayer != null)
            {
                helpLayer.AddChild(canvas);
            }
            else
            {
                GetTree().Root.AddChild(canvas);
            }
            canvas.Visible = true;
        }
    }

    private void OnDomainEventEmitted(string type, string _source, string dataJson, string _id, string _specVersion, string _dataContentType, string _timestampIso)
    {
        if (string.Equals(type, UiMenuReturn, StringComparison.Ordinal))
        {
            _startPending = false;
            _loadPending = false;
            ClearStatus();
            SetMenuButtonsEnabled(true);
            SetStartButtonEnabled(true);
            _loadPanel.Visible = false;
            ShowMenu();
            return;
        }

        if (string.Equals(type, GameLoaded, StringComparison.Ordinal))
        {
            if (!_loadPending)
            {
                return;
            }

            _startPending = false;
            _loadPending = false;
            ClearStatus();
            SetMenuButtonsEnabled(true);
            SetStartButtonEnabled(true);
            SetConfigPanelVisible(false);
            _loadPanel.Visible = false;
            HideMenu();
            SetHudVisible(true);
            return;
        }

        if (!_startPending)
        {
            return;
        }

        if (string.Equals(type, TurnStarted, StringComparison.Ordinal))
        {
            _startPending = false;
            ClearStatus();
            SetMenuButtonsEnabled(true);
            SetStartButtonEnabled(true);
            SetConfigPanelVisible(false);
            HideMenu();
            SetHudVisible(true);
            return;
        }

        if (string.Equals(type, UiMenuStartFailed, StringComparison.Ordinal))
        {
            _startPending = false;
            SetMenuButtonsEnabled(true);
            SetStartButtonEnabled(true);
            Visible = true;
            SetConfigPanelVisible(true);
            SetHudVisible(false);
            ShowStatus($"{TranslateOrFallback(MenuStatusStartFailedKey, "Start failed")}: {TranslateStartError(TryExtractStartFailedReason(dataJson) ?? "unknown")}");
        }
    }

    private void WireNewGameConfigControls()
    {
        _playersOption.ItemSelected += _ => RefreshStartAvailability();
        _startingMoneyOption.ItemSelected += _ => RefreshStartAvailability();
        _globalEventIntervalOption.ItemSelected += _ => RefreshStartAvailability();
        _activeStrategemOption.ItemSelected += _ => RefreshStartAvailability();
        _passiveStrategemOption.ItemSelected += _ => RefreshStartAvailability();
        _mapOption.ItemSelected += _ => RefreshStartAvailability();

        _btnCharPrev.Pressed += () => ShiftCharacterCarousel(-1);
        _btnCharNext.Pressed += () => ShiftCharacterCarousel(1);
        for (var i = 0; i < _characterSlots.Length; i++)
        {
            var slotIndex = i;
            _characterSlots[i].Pressed += () => OnCharacterSlotPressed(slotIndex);
        }
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

            PopulateStrategemOptions();

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

            _playersOption.Select(0);
            _startingMoneyOption.Select(1);
            _globalEventIntervalOption.Select(1);
            _mapOption.Select(0);
            _activeStrategemOption.Select(0);
            _passiveStrategemOption.Select(0);

            PopulateCharacters(loader, pack);

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
        _aiFillLabel.Text = playersCount > 0
            ? $"{_aiSlotsLabel}: {Math.Max(0, playersCount - 1)}"
            : $"{_aiSlotsLabel}: -";

        if (_startPending)
        {
            return;
        }

        if (!_newGameConfigReady)
        {
            _btnStart.Disabled = true;
            return;
        }

        _btnStart.Disabled = !TryBuildStartConfigJson(out _, out _);
    }

    private void SetHudVisible(bool visible)
    {
        var hud = GetNodeOrNull<CanvasItem>("/root/Main/SplitRoot/TopArea/HudLayer/HUD");
        if (hud != null)
        {
            hud.Visible = visible;
        }
    }

    private void SetBoardVisible(bool visible)
    {
        var board = GetNodeOrNull<CanvasItem>("/root/Main/SplitRoot/BottomArea/BoardArea/BoardViewportContainer/BoardViewport/SanguoBoardView");
        if (board != null)
        {
            board.Visible = visible;
        }
    }

    private void ResetBoardCameraIfNeeded()
    {
        var board = GetNodeOrNull<Node>("/root/Main/SplitRoot/BottomArea/BoardArea/BoardViewportContainer/BoardViewport/SanguoBoardView");
        if (board != null && board.HasMethod("ResetCameraView"))
        {
            board.Call("ResetCameraView");
        }
    }

    private void SetConfigPanelVisible(bool visible)
    {
        _newGameConfig.Visible = visible;
        var backdrop = GetNodeOrNull<ColorRect>("ConfigBackdrop");
        if (backdrop != null)
        {
            backdrop.Visible = visible;
        }
        _configCenter.MouseFilter = visible
            ? Control.MouseFilterEnum.Stop
            : Control.MouseFilterEnum.Ignore;
    }

    private void SetBoardInputEnabled(bool enabled)
    {
        var board = GetNodeOrNull<Node>("/root/Main/SplitRoot/BottomArea/BoardArea/BoardViewportContainer/BoardViewport/SanguoBoardView");
        if (board == null)
        {
            return;
        }

        board.SetProcess(enabled);
        board.SetProcessInput(enabled);
        board.SetProcessUnhandledInput(enabled);
    }

    private void SetOverlayInputEnabled(bool enabled)
    {
        var screenRoot = GetNodeOrNull<Control>("/root/Main/SplitRoot/BottomArea/BoardArea/ScreenRoot");
        if (screenRoot != null)
        {
            screenRoot.MouseFilter = enabled ? Control.MouseFilterEnum.Pass : Control.MouseFilterEnum.Ignore;
        }

        var overlays = GetNodeOrNull<Control>("/root/Main/SplitRoot/BottomArea/BoardArea/Overlays");
        if (overlays != null)
        {
            overlays.MouseFilter = enabled ? Control.MouseFilterEnum.Pass : Control.MouseFilterEnum.Ignore;
        }
    }

    private void SetOverlayVisible(bool visible)
    {
        var screenRoot = GetNodeOrNull<Control>("/root/Main/SplitRoot/BottomArea/BoardArea/ScreenRoot");
        if (screenRoot != null)
        {
            screenRoot.Visible = visible;
        }

        var overlays = GetNodeOrNull<Control>("/root/Main/SplitRoot/BottomArea/BoardArea/Overlays");
        if (overlays != null)
        {
            overlays.Visible = visible;
        }

        var settingsPanel = GetNodeOrNull<Control>("/root/Main/SettingsLayer/SettingsPanel");
        if (settingsPanel != null && !visible)
        {
            settingsPanel.Visible = false;
        }
    }

    private static string TranslateOrFallback(string key, string fallback)
    {
        if (string.IsNullOrWhiteSpace(key))
        {
            return fallback;
        }

        var translated = TranslationServer.Translate(key);
        if (string.IsNullOrWhiteSpace(translated) || string.Equals(translated, key, StringComparison.Ordinal))
        {
            return fallback;
        }

        return translated;
    }

    private void ApplyLocalizedTexts()
    {
        _btnPlay.Text = TranslateOrFallback(MenuPlayLabelKey, "Play");
        _btnLoad.Text = TranslateOrFallback(MenuLoadLabelKey, "Load");
        _btnSettings.Text = TranslateOrFallback(MenuSettingsLabelKey, "Settings");
        if (_btnHelp != null)
        {
            _btnHelp.Text = TranslateOrFallback(MenuHelpLabelKey, "Help");
        }
        _btnQuit.Text = TranslateOrFallback(MenuQuitLabelKey, "Quit");
        _btnStart.Text = TranslateOrFallback(StartButtonLabelKey, "Start");
        _btnBack.Text = TranslateOrFallback(MenuBackLabelKey, "Back");

        _titleLabel.Text = TranslateOrFallback(MenuNewGameLabelKey, "New Game");
        _mapLabel.Text = TranslateOrFallback(MenuMapLabelKey, "Map");
        _playersLabel.Text = TranslateOrFallback(MenuPlayersLabelKey, "Players");
        _characterLabel.Text = TranslateOrFallback(MenuCharacterLabelKey, "Player Character");
        _moneyLabel.Text = TranslateOrFallback(MenuStartingMoneyLabelKey, "Starting Money");
        _globalEventLabel.Text = TranslateOrFallback(MenuGlobalEventIntervalLabelKey, "Global Event Interval");
        _activeStrategemLabel.Text = TranslateOrFallback(MenuActiveStrategemLabelKey, "Active Strategem");
        _passiveStrategemLabel.Text = TranslateOrFallback(MenuPassiveStrategemLabelKey, "Passive Strategem");
        _aiSlotsLabel = TranslateOrFallback(MenuAiSlotsLabelKey, "AI slots");

        _combatKey.Text = TranslateOrFallback("ui.menu.character.combat", "Combat");
        _startMoneyStepKey.Text = TranslateOrFallback("ui.menu.character.start_money_step", "Starting money step");
        _buyStepKey.Text = TranslateOrFallback("ui.menu.character.buy_price_step", "Buy price step");
        _tollStepKey.Text = TranslateOrFallback("ui.menu.character.toll_step", "Toll step");
        _incomeStepKey.Text = TranslateOrFallback("ui.menu.character.income_step", "Income step");
        _buildStepKey.Text = TranslateOrFallback("ui.menu.character.build_cost_step", "Build cost step");
        _upgradeStepKey.Text = TranslateOrFallback("ui.menu.character.upgrade_cost_step", "Upgrade cost step");

        UpdateCharacterInfoPanel();
        RenderCharacterCarousel();
    }

    private string TranslateStartError(string error)
    {
        if (string.IsNullOrWhiteSpace(error))
        {
            return error;
        }

        return error switch
        {
            "map_missing" => TranslateOrFallback(MenuErrorMapMissingKey, error),
            "character_missing" => TranslateOrFallback(MenuErrorCharacterMissingKey, error),
            "players_count_invalid" => TranslateOrFallback(MenuErrorPlayersInvalidKey, error),
            "active_strategem_missing" => error,
            "passive_strategem_missing" => error,
            _ => error,
        };
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
        var activeStrategemId = GetSelectedActiveStrategemId();
        if (string.IsNullOrWhiteSpace(activeStrategemId))
        {
            error = "active_strategem_missing";
            return false;
        }

        var passiveStrategemId = GetSelectedPassiveStrategemId();
        if (string.IsNullOrWhiteSpace(passiveStrategemId))
        {
            error = "passive_strategem_missing";
            return false;
        }

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
            CharacterAssignments: assigns,
            ActiveStrategemId: activeStrategemId,
            PassiveStrategemId: passiveStrategemId);

        if (!GameStartConfigValidator.TryValidate(cfg, out var errors))
        {
            error = string.Join(" | ", errors.Take(3));
            return false;
        }

        json = JsonSerializer.Serialize(cfg);
        return true;
    }

    private void PopulateStrategemOptions()
    {
        _activeStrategemOption.Clear();
        _passiveStrategemOption.Clear();

        AddStrategemOption(_activeStrategemOption, "Default Active", "strat_active_default");
        AddStrategemOption(_passiveStrategemOption, "Default Passive", "strat_passive_default");
    }

    private static void AddStrategemOption(OptionButton option, string label, string strategemId)
    {
        var idx = option.ItemCount;
        option.AddItem(label);
        option.SetItemMetadata(idx, strategemId);
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

    private void PopulateCharacters(IResourceLoader loader, SanguoContentPackPaths? pack)
    {
        _characters = new List<SanguoCharacterDefinition>();
        _selectedCharacterId = string.Empty;
        _characterCarouselOffset = 0;

        if (SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, pack, out var chars, out _)
            && chars.Characters != null && chars.Characters.Count > 0)
        {
            _characters = chars.Characters
                .OrderBy(x => x.NameKey, StringComparer.Ordinal)
                .ToList();
        }
        else
        {
            _characters.Add(new SanguoCharacterDefinition(
                CharacterId: "c1",
                NameKey: "c1",
                DescriptionKey: string.Empty,
                CombatRating: 0,
                PortraitPath: string.Empty,
                StartingMoneyStepDelta: 0,
                EconomyStepDeltas: new SanguoEconomyStepDeltas(0, 0, 0, 0, 0)));
        }

        _selectedCharacterId = _characters[0].CharacterId;
        UpdateCharacterInfoPanel();
        RenderCharacterCarousel();
    }

    private void ShiftCharacterCarousel(int delta)
    {
        if (_characters.Count <= 8)
        {
            return;
        }

        var count = _characters.Count;
        _characterCarouselOffset = (_characterCarouselOffset + delta) % count;
        if (_characterCarouselOffset < 0)
        {
            _characterCarouselOffset += count;
        }

        RenderCharacterCarousel();
    }

    private void OnCharacterSlotPressed(int slotIndex)
    {
        if (slotIndex < 0 || slotIndex >= _characterSlots.Length)
        {
            return;
        }

        var button = _characterSlots[slotIndex];
        if (!button.HasMeta("character_index"))
        {
            return;
        }

        var idx = (int)button.GetMeta("character_index");
        if (idx < 0 || idx >= _characters.Count)
        {
            return;
        }

        _selectedCharacterId = _characters[idx].CharacterId;
        UpdateCharacterInfoPanel();
        RenderCharacterCarousel();
        RefreshStartAvailability();
    }

    private void RenderCharacterCarousel()
    {
        var count = _characters.Count;
        var canScroll = count > 8;
        _btnCharPrev.Disabled = !canScroll;
        _btnCharNext.Disabled = !canScroll;

        for (var slot = 0; slot < _characterSlots.Length; slot++)
        {
            var btn = _characterSlots[slot];
            if (count == 0)
            {
                btn.Visible = false;
                continue;
            }

            int idx;
            if (!canScroll)
            {
                if (slot >= count)
                {
                    btn.Visible = false;
                    continue;
                }

                idx = slot;
            }
            else
            {
                idx = (_characterCarouselOffset + slot) % count;
            }

            var def = _characters[idx];
            btn.Visible = true;
            btn.Text = TranslateOrFallback(def.NameKey, def.CharacterId);
            btn.SetMeta("character_index", idx);
            btn.ButtonPressed = string.Equals(def.CharacterId, _selectedCharacterId, StringComparison.Ordinal);
        }
    }

    private void UpdateCharacterInfoPanel()
    {
        if (_characters.Count == 0)
        {
            _characterName.Text = "-";
            _characterDesc.Text = string.Empty;
            _characterPortrait.Texture = null;
            _combatValue.Text = "-";
            _startMoneyStepValue.Text = "-";
            _buyStepValue.Text = "-";
            _tollStepValue.Text = "-";
            _incomeStepValue.Text = "-";
            _buildStepValue.Text = "-";
            _upgradeStepValue.Text = "-";
            return;
        }

        var selected = _characters.FirstOrDefault(x => string.Equals(x.CharacterId, _selectedCharacterId, StringComparison.Ordinal))
            ?? _characters[0];

        _characterName.Text = TranslateOrFallback(selected.NameKey, selected.CharacterId);
        _characterDesc.Text = TranslateOrFallback(selected.DescriptionKey, string.Empty);
        _combatValue.Text = selected.CombatRating.ToString();
        _startMoneyStepValue.Text = selected.StartingMoneyStepDelta.ToString();
        _buyStepValue.Text = selected.EconomyStepDeltas.BuyPrice.ToString();
        _tollStepValue.Text = selected.EconomyStepDeltas.Toll.ToString();
        _incomeStepValue.Text = selected.EconomyStepDeltas.IncomeSettlement.ToString();
        _buildStepValue.Text = selected.EconomyStepDeltas.BuildCost.ToString();
        _upgradeStepValue.Text = selected.EconomyStepDeltas.UpgradeCost.ToString();

        if (!string.IsNullOrWhiteSpace(selected.PortraitPath) && ResourceLoader.Exists(selected.PortraitPath))
        {
            // Headless smoke focuses on scene boot wiring; skip portrait texture imports there.
            if (string.Equals(DisplayServer.GetName(), "headless", StringComparison.OrdinalIgnoreCase))
            {
                _characterPortrait.Texture = null;
                return;
            }

            _characterPortrait.Texture = GD.Load<Texture2D>(selected.PortraitPath);
        }
        else
        {
            _characterPortrait.Texture = null;
        }
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
        return _selectedCharacterId ?? string.Empty;
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

    private string GetSelectedActiveStrategemId()
    {
        return GetSelectedStrategemId(_activeStrategemOption);
    }

    private string GetSelectedPassiveStrategemId()
    {
        return GetSelectedStrategemId(_passiveStrategemOption);
    }

    private static string GetSelectedStrategemId(OptionButton option)
    {
        if (option.ItemCount == 0 || option.Selected < 0)
        {
            return string.Empty;
        }

        var meta = option.GetItemMetadata(option.Selected);
        return meta.VariantType == Variant.Type.String ? meta.AsString() : string.Empty;
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
