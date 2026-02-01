using Godot;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using Game.Core.Services.Sanguo;
using Game.Godot.Adapters;
using Game.Godot.Scripts.Config;
using Game.Godot.Scripts.Sanguo;
using Game.Godot.Scripts.Security;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

public partial class HUD : Control, IHudEventHandlers
{
    private static readonly JsonDocumentOptions JsonOptions = new() { MaxDepth = 32 };
    private const string UiHudDiceRollEventType = "ui.hud.dice.roll";
    private const string UiHudSaveEventType = "ui.hud.save";
    private const string UiHudLoadEventType = "ui.hud.load";
    private const string UiMenuSettingsEventType = "ui.menu.settings";
    private const string UiMenuHelpEventType = "ui.menu.help";
    private const string UiMenuReturnEventType = "ui.menu.return";
    private const string UiMenuQuitEventType = "ui.menu.quit";
    private const string UiHudPlayerPrefixKey = "ui.hud.player";
    private const string UiHudDatePrefixKey = "ui.hud.date";
    private const string UiHudMoneyPrefixKey = "ui.hud.money";
    private const string UiHudScorePrefixKey = "ui.hud.score";
    private const string UiHudHealthPrefixKey = "ui.hud.health";
    private const string UiHudDiceRollKey = "ui.hud.dice.roll";
    private const string UiHudDiceWaitingKey = "ui.hud.dice.waiting";
    private const string UiHudDiceAiKey = "ui.hud.dice.ai";
    private const string UiHudDiceValueKey = "ui.hud.dice.value";
    private const string UiHudGameOverKey = "ui.hud.game_over";
    private const string UiHudGameSettingsKey = "ui.hud.game_settings";
    private const string UiHudLogKey = "ui.hud.log";
    private const string UiHudCardsKey = "ui.hud.cards";
    private const string UiHudCardsTitleKey = "ui.hud.cards.title";
    private const string UiHudCardsEmptyKey = "ui.hud.cards.empty";
    private const string UiHudCardsUseKey = "ui.hud.cards.use";
    private const string UiHudCardsCloseKey = "ui.hud.cards.close";
    private const string UiHudCardsConfirmTextKey = "ui.hud.cards.confirm_text";
    private const string UiHudCardsConfirmUseKey = "ui.hud.cards.confirm_use";
    private const string UiHudCardsConfirmCancelKey = "ui.hud.cards.confirm_cancel";
    private const string UiHudPlayersTitleKey = "ui.hud.players";
    private const string UiHudSettingsTitleKey = "ui.hud.settings.title";
    private const string UiHudSettingsResumeKey = "ui.hud.settings.resume";
    private const string UiHudSettingsSaveKey = "ui.hud.settings.save";
    private const string UiHudSettingsLoadKey = "ui.hud.settings.load";
    private const string UiHudSettingsSettingKey = "ui.hud.settings.setting";
    private const string UiHudSettingsHelpKey = "ui.hud.settings.help";
    private const string UiHudSettingsReturnKey = "ui.hud.settings.return";
    private const string UiHudSettingsQuitKey = "ui.hud.settings.quit";
    private const string UiHudActionTitleKey = "ui.hud.action.title";
    private const string UiHudActionSkipKey = "ui.hud.action.skip";
    private const string UiHudGuideTitleKey = "ui.hud.guide.title";
    private const string UiHudGuideStepKey = "ui.hud.guide.step";
    private const string UiHudToastChooseActionKey = "ui.hud.toast.choose_action_or_skip";
    private const string UiHudToastGameStartingKey = "ui.hud.toast.game_starting";
    private const string UiActionCardPlayEventType = "ui.sanguo.action_card.play";
    private const string MoneyCapAuditAction = "SANGUO_MONEY_CAPPED";
    private const string EventLogOverlayFlag = "event_log_overlay";
    private const string DefaultSaveSlotId = "quick";
    private const string HelpTutorialGroup = "help_tutorial";
    private const string HelpTutorialScenePath = "res://Game.Godot/Scenes/UI/HelpTutorial.tscn";
    private const int InitialActionCardCopiesPerType = 2;
    private const int MaxActionCardsPerPlayer = 15;

    private static readonly HashSet<string> ResultPopupEventTypes = new(StringComparer.Ordinal)
    {
        SanguoCityBought.EventType,
        SanguoBuildingBuilt.EventType,
        SanguoRandomEventApplied.EventType,
        SanguoRandomEventRejected.EventType,
        SanguoActionCardPlayed.EventType,
        SanguoActionCardPlayRejected.EventType,
        SanguoLootGranted.EventType,
        SanguoRelicApplied.EventType,
        SanguoCombatStarted.EventType,
        SanguoCombatEnded.EventType,
        SanguoCityTollPaid.EventType,
        SanguoCityTollSynergyPaid.EventType,
    };

    private Label _score = default!;
    private Label _health = default!;

    private Label _activePlayer = default!;
    private Label _date = default!;
    private Label _money = default!;
    private TextureRect? _avatar;
    private Button _diceButton = default!;
    private Button _btnSave = default!;
    private Button? _cardsButton;
    private HudSettingsMenuController? _settingsMenuController;
    private PlayersPanelController? _playersPanelController;
    private HudEventHandlersController? _eventHandlersController;
    private HudActionPanelController? _actionPanelController;
    private HudGuideController? _guideController;

    private Control? _actionPanel;

    private string? _activePlayerId;
    private int _lastDateKey;
    private EventBusAdapter? _bus;

    private EventToast? _toast;
    private EventResultPopup? _resultPopup;
    private EventLogPanel? _logPanel;
    private Control? _cardsPanel;
    private VBoxContainer? _cardsList;
    private Label? _cardsTitle;
    private Label? _cardsEmptyLabel;
    private Button? _cardsCloseButton;
    private Control? _cardConfirmPanel;
    private Label? _cardConfirmLabel;
    private Button? _cardConfirmUseButton;
    private Button? _cardConfirmCancelButton;
    private string? _pendingCardId;
    private bool _logVisible;

    [Export] public bool EnableGuideText { get; set; } = true;
    [Export] public bool EnableGuideHighlight { get; set; } = true;

    private readonly Dictionary<int, TileInfo> _tilesByIndex = new();
    private readonly Dictionary<string, string> _tileNameKeyById = new(StringComparer.Ordinal);

    private readonly Dictionary<string, string> _regionNameKeyById = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _cardNameKeyById = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _relicNameKeyById = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _randomEventNameKeyById = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _randomEventPoolNameKeyById = new(StringComparer.Ordinal);

    private readonly Dictionary<string, string> _characterIdByPlayerId = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _characterNameKeyById = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _portraitPathByCharacterId = new(StringComparer.Ordinal);
    private readonly Dictionary<string, Texture2D> _portraitCache = new(StringComparer.Ordinal);
    private readonly Dictionary<string, PlayerStateSnapshot> _playerStatesById = new(StringComparer.Ordinal);
    private readonly Dictionary<string, Dictionary<string, int>> _cardsByPlayerId = new(StringComparer.Ordinal);
    private readonly List<string> _cardIds = new();
    private ResourceLoaderAdapter? _fallbackResourceLoader;
    private string _playerPrefix = "Player";
    private string _datePrefix = "Date";
    private string _moneyPrefix = "Money";
    private string _scorePrefix = "Score";
    private string _healthPrefix = "HP";
    private string _diceRollLabel = "Roll Dice";
    private string _diceWaitingLabel = "Waiting...";
    private string _diceAiLabel = "AI Turn";
    private string _diceValueLabel = "Dice";

    public override void _Ready()
    {
        ProcessMode = Node.ProcessModeEnum.Always;
        _lastDateKey = -1;
        _score = GetNode<Label>("TopBar/TopStack/HBox/ScoreLabel");
        _health = GetNode<Label>("TopBar/TopStack/HBox/HealthLabel");

        _activePlayer = GetNode<Label>("TopBar/TopStack/HBox/ActivePlayerLabel");
        _date = GetNode<Label>("TopBar/TopStack/HBox/DateLabel");
        _money = GetNode<Label>("TopBar/TopStack/HBox/MoneyLabel");
        _avatar = GetNodeOrNull<TextureRect>("TopBar/TopStack/HBox/Avatar");
        _diceButton = GetNode<Button>("TopBar/TopStack/HBox/DiceButton");
        _diceButton.Pressed += OnDicePressed;
        _diceButton.Disabled = true;
        _diceButton.Text = "Waiting...";

        var gameSettingsButton = GetNode<Button>("TopBar/TopStack/HBox/GameSettingsButton");
        var logButton = GetNode<Button>("TopBar/TopStack/HBox/LogButton");
        var cardsButton = GetNode<Button>("TopBar/TopStack/HBox/CardsButton");
        var settingsMenu = GetNode<Control>("SettingsMenu");
        var btnResume = GetNode<Button>("SettingsMenu/Center/Panel/VBox/BtnResume");
        var btnSave = GetNode<Button>("SettingsMenu/Center/Panel/VBox/BtnSave");
        var btnLoad = GetNode<Button>("SettingsMenu/Center/Panel/VBox/BtnLoad");
        var btnSetting = GetNode<Button>("SettingsMenu/Center/Panel/VBox/BtnSetting");
        var btnHelp = GetNode<Button>("SettingsMenu/Center/Panel/VBox/BtnHelp");
        var btnReturn = GetNode<Button>("SettingsMenu/Center/Panel/VBox/BtnReturn");
        var btnQuit = GetNode<Button>("SettingsMenu/Center/Panel/VBox/BtnQuit");

        _btnSave = btnSave;
        _cardsButton = cardsButton;
        _btnSave.Disabled = true;
        btnLoad.Disabled = false;

        _settingsMenuController = new HudSettingsMenuController(
            owner: this,
            menu: settingsMenu,
            openButton: gameSettingsButton,
            resumeButton: btnResume,
            saveButton: btnSave,
            loadButton: btnLoad,
            settingButton: btnSetting,
            helpButton: btnHelp,
            returnButton: btnReturn,
            quitButton: btnQuit,
            onSave: OnSavePressed,
            onLoad: OnLoadPressed,
            onSetting: () => PublishMenuEvent(UiMenuSettingsEventType),
            onHelp: () =>
            {
                PublishMenuEvent(UiMenuHelpEventType);
                ToggleHelpTutorial();
            },
            onReturn: () => PublishMenuEvent(UiMenuReturnEventType),
            onQuit: () => PublishMenuEvent(UiMenuQuitEventType));
        _settingsMenuController.Bind();
        cardsButton.Pressed += ToggleCardsPanel;

        _playersPanelController = new PlayersPanelController(GetNode<VBoxContainer>("TopBar/TopStack/PlayersPanel/VBox/PlayersList"));

        _actionPanel = GetNodeOrNull<Control>("ActionPanel");
        var actionTitle = GetNodeOrNull<Label>("ActionPanel/VBox/ActionTitle");
        var actionButtons = GetNodeOrNull<VBoxContainer>("ActionPanel/VBox/Actions");
        var skipActionButton = GetNodeOrNull<Button>("ActionPanel/VBox/SkipButton");

        _toast = GetNodeOrNull<EventToast>("EventToast");
        _resultPopup = GetNodeOrNull<EventResultPopup>("EventResultPopup");
        _logPanel = GetNodeOrNull<EventLogPanel>("EventLogPanel");
        _cardsPanel = GetNodeOrNull<Control>("CardsPanel");
        _cardsTitle = GetNodeOrNull<Label>("CardsPanel/Center/Panel/VBox/Title");
        _cardsList = GetNodeOrNull<VBoxContainer>("CardsPanel/Center/Panel/VBox/CardsScroll/CardsList");
        _cardsEmptyLabel = GetNodeOrNull<Label>("CardsPanel/Center/Panel/VBox/EmptyLabel");
        _cardsCloseButton = GetNodeOrNull<Button>("CardsPanel/Center/Panel/VBox/ButtonRow/CloseButton");
        _cardConfirmPanel = GetNodeOrNull<Control>("CardsPanel/CardConfirm");
        _cardConfirmLabel = GetNodeOrNull<Label>("CardsPanel/CardConfirm/ConfirmCenter/ConfirmPanel/ConfirmVBox/ConfirmLabel");
        _cardConfirmUseButton = GetNodeOrNull<Button>("CardsPanel/CardConfirm/ConfirmCenter/ConfirmPanel/ConfirmVBox/ConfirmButtons/ConfirmUseButton");
        _cardConfirmCancelButton = GetNodeOrNull<Button>("CardsPanel/CardConfirm/ConfirmCenter/ConfirmPanel/ConfirmVBox/ConfirmButtons/ConfirmCancelButton");
        var guidePanel = GetNodeOrNull<PanelContainer>("GuideHintPanel");
        var guideTitle = GetNodeOrNull<Label>("GuideHintPanel/VBox/GuideTitle");
        var guideText = GetNodeOrNull<Label>("GuideHintPanel/VBox/GuideText");
        var guideCloseButton = GetNodeOrNull<Button>("GuideHintPanel/VBox/GuideButtonRow/GuideCloseButton");
        var guideOverlay = GetNodeOrNull<GuideHighlightOverlay>("GuideOverlay");
        _logVisible = false;
        if (_logPanel != null)
        {
            var ff = GetNodeOrNull<FeatureFlags>("/root/FeatureFlags");
            _logVisible = ff != null && ff.IsEnabled(EventLogOverlayFlag);
            _logPanel.Visible = _logVisible;
        }
        logButton.Pressed += ToggleEventLogOverlay;
        if (_logPanel == null)
        {
            logButton.Disabled = true;
        }

        if (_cardsPanel != null)
        {
            _cardsPanel.Visible = false;
        }
        if (_cardConfirmPanel != null)
        {
            _cardConfirmPanel.Visible = false;
        }
        if (_cardsCloseButton != null)
        {
            _cardsCloseButton.Pressed += HideCardsPanel;
        }
        if (_cardConfirmCancelButton != null)
        {
            _cardConfirmCancelButton.Pressed += HideCardConfirm;
        }
        if (_cardConfirmUseButton != null)
        {
            _cardConfirmUseButton.Pressed += OnConfirmUseCard;
        }

        MoveOverlayToBottom(settingsMenu);
        MoveOverlayToBottom(_toast);
        MoveOverlayToBottom(_resultPopup);
        MoveOverlayToBottom(_logPanel);
        MoveOverlayToBottom(_cardsPanel);
        MoveOverlayToBottom(guidePanel);
        MoveOverlayToBottom(guideOverlay);
        MoveOverlayToBottom(_actionPanel);
        CallDeferred(nameof(AttachOverlaysToBottom));

        ApplyLocalizedTexts(
            gameSettingsButton,
            logButton,
            cardsButton,
            btnResume,
            btnSave,
            btnLoad,
            btnSetting,
            btnHelp,
            btnReturn,
            btnQuit,
            actionTitle,
            skipActionButton,
            guideTitle,
            guideText);

        if (guidePanel != null && guideTitle != null && guideText != null && guideOverlay != null)
        {
            _guideController = new HudGuideController(
                guidePanel,
                guideTitle,
                guideText,
                guideOverlay,
                _diceButton,
                _money,
                _actionPanel,
                _toast as Control,
                _logPanel as Control,
                FindControlByPath,
                TranslateOrFallback);
            _guideController.Initialize();
            if (guideCloseButton != null)
            {
                guideCloseButton.Text = TranslateOrFallback("ui.guide.close");
                guideCloseButton.Pressed += () =>
                {
                    guidePanel.Visible = false;
                    guideOverlay.Visible = false;
                };
            }
        }
        else
        {
            if (guidePanel != null)
            {
                guidePanel.Visible = false;
            }
            if (guideOverlay != null)
            {
                guideOverlay.Visible = false;
            }
        }

        _eventHandlersController = new HudEventHandlersController(
            RecordEventForUi,
            message => GD.PushWarning(message),
            JsonOptions);
        RegisterHandlers();
        UpdateActivePlayerIdentityDisplay();

        _score.Visible = false;
        _health.Visible = false;
        _date.Visible = true;

        _bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (_bus == null)
        {
            GD.PushWarning("HUD: EventBus not found at /root/EventBus");
            return;
        }

        if (_actionPanel != null && actionTitle != null && actionButtons != null && skipActionButton != null)
        {
            _actionPanelController = new HudActionPanelController(
                _actionPanel,
                actionTitle,
                actionButtons,
                skipActionButton,
                _diceButton,
                _toast,
                _bus,
                nameof(HUD));
            _actionPanelController.Bind();
        }

        TryLoadMapTilesForUi();
        TryLoadUiCatalogLabels();
        UpdateCardsButtonState();

        var callable = new Callable(this, nameof(OnDomainEventEmitted));
        TryConnectBus(callable);
    }

    public override void _ExitTree()
    {
        _diceButton.Pressed -= OnDicePressed;
        _settingsMenuController?.Unbind();
        _actionPanelController?.Unbind();

        if (_bus == null)
        {
            return;
        }

        var callable = new Callable(this, nameof(OnDomainEventEmitted));
        TryDisconnectBus(callable);

        _bus = null;
        _fallbackResourceLoader = null;
        _settingsMenuController = null;
        _playersPanelController = null;
        _eventHandlersController = null;
        _actionPanelController = null;
        _guideController = null;
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        if (@event is InputEventKey key && key.Pressed && !key.Echo && key.Keycode == Key.F1)
        {
            ToggleEventLogOverlay();
        }
    }

    public void ToggleEventLogOverlay()
    {
        if (_logPanel == null)
        {
            return;
        }

        _logVisible = !_logVisible;
        _logPanel.Visible = _logVisible;
    }

    private void OnDicePressed()
    {
        if (_bus == null)
        {
            GD.PushWarning("HUD: EventBus not found; cannot publish ui.hud.dice.roll");
            return;
        }

        if (_actionPanelController != null && _actionPanelController.IsAwaitingTileAction())
        {
            _toast?.ShowMessage(TranslateOrFallback(UiHudToastChooseActionKey, "Please choose a tile action or Skip."));
            return;
        }

        var playerId = _activePlayerId ?? "";
        if (string.IsNullOrWhiteSpace(playerId))
        {
            _toast?.ShowMessage(TranslateOrFallback(UiHudToastGameStartingKey, "Game is starting. Please wait..."));
            GD.PushWarning("HUD: ActivePlayerId is not known; not publishing ui.hud.dice.roll");
            return;
        }

        var payload = JsonSerializer.Serialize(new
        {
            GameId = "g1",
            PlayerId = playerId,
            CorrelationId = Guid.NewGuid().ToString("N"),
            CausationId = UiHudDiceRollEventType,
        });

        _bus.PublishSimple(UiHudDiceRollEventType, nameof(HUD), payload);
    }

    private void OnSavePressed()
    {
        if (_bus == null)
        {
            GD.PushWarning("HUD: EventBus not found; cannot publish ui.hud.save");
            return;
        }

        if (_actionPanelController != null && _actionPanelController.IsAwaitingTileAction())
        {
            _toast?.ShowMessage(TranslateOrFallback(UiHudToastChooseActionKey, "Please choose a tile action or Skip."));
            return;
        }

        var payload = JsonSerializer.Serialize(new
        {
            GameId = "g1",
            PlayerId = _activePlayerId ?? string.Empty,
            SaveSlotId = DefaultSaveSlotId,
            CorrelationId = Guid.NewGuid().ToString("N"),
            CausationId = UiHudSaveEventType,
        });

        _bus.PublishSimple(UiHudSaveEventType, nameof(HUD), payload);
    }

    private void OnLoadPressed()
    {
        if (_bus == null)
        {
            GD.PushWarning("HUD: EventBus not found; cannot publish ui.hud.load");
            return;
        }

        if (_actionPanelController != null && _actionPanelController.IsAwaitingTileAction())
        {
            _toast?.ShowMessage(TranslateOrFallback(UiHudToastChooseActionKey, "Please choose a tile action or Skip."));
            return;
        }

        var payload = JsonSerializer.Serialize(new
        {
            GameId = "g1",
            PlayerId = _activePlayerId ?? string.Empty,
            SaveSlotId = DefaultSaveSlotId,
            CorrelationId = Guid.NewGuid().ToString("N"),
            CausationId = UiHudLoadEventType,
        });

        _bus.PublishSimple(UiHudLoadEventType, nameof(HUD), payload);
    }

    private void PublishMenuEvent(string type)
    {
        if (_bus == null)
        {
            GD.PushWarning($"HUD: EventBus not found; cannot publish {type}");
            return;
        }

        _bus.PublishSimple(type, nameof(HUD), "{}");
    }

    private void ToggleHelpTutorial()
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

    private void OnDomainEventEmitted(string type, string source, string dataJson, string id, string specVersion, string dataContentType, string timestampIso)
    {
        _eventHandlersController?.HandleDomainEvent(type, source, dataJson, id, timestampIso);
    }

    private void RecordEventForUi(string type, string source, string id, string timestampIso, JsonElement root)
    {
        _guideController?.UpdateGuideHintForEventType(type, EnableGuideText, EnableGuideHighlight);
        UpdateCardsFromEvent(type, root);
        var tileLabelByIndex = _tilesByIndex.Count == 0
            ? null
            : new Func<int, string?>(idx => _tilesByIndex.TryGetValue(idx, out var tile) ? tile.Name : null);
        var tileLabelById = _tileNameKeyById.Count == 0
            ? null
            : new Func<string, string?>(tileId => _tileNameKeyById.TryGetValue(tileId ?? string.Empty, out var nameKey) ? nameKey : null);
        var regionLabelById = _regionNameKeyById.Count == 0
            ? null
            : new Func<string, string?>(regionId => _regionNameKeyById.TryGetValue(regionId ?? string.Empty, out var nameKey) ? nameKey : null);
        var cardLabelById = _cardNameKeyById.Count == 0
            ? null
            : new Func<string, string?>(cardId => _cardNameKeyById.TryGetValue(cardId ?? string.Empty, out var nameKey) ? nameKey : null);
        var relicLabelById = _relicNameKeyById.Count == 0
            ? null
            : new Func<string, string?>(relicId => _relicNameKeyById.TryGetValue(relicId ?? string.Empty, out var nameKey) ? nameKey : null);
        var eventLabelById = _randomEventNameKeyById.Count == 0
            ? null
            : new Func<string, string?>(eventId => _randomEventNameKeyById.TryGetValue(eventId ?? string.Empty, out var nameKey) ? nameKey : null);
        var eventPoolLabelById = _randomEventPoolNameKeyById.Count == 0
            ? null
            : new Func<string, string?>(poolId => _randomEventPoolNameKeyById.TryGetValue(poolId ?? string.Empty, out var nameKey) ? nameKey : null);

        var explanation = EventExplainService.Explain(
            type,
            source,
            id,
            timestampIso,
            root,
            tileLabelByIndex,
            tileLabelById,
            regionLabelById,
            cardLabelById,
            relicLabelById,
            eventLabelById,
            eventPoolLabelById);
        if (ShouldShowResultPopup(type))
        {
            var autoHide = ResolvePopupAutoHideSeconds(type, root);
            _resultPopup?.ShowMessage(explanation.SummaryText, autoHide);
        }
        _toast?.ShowMessage(explanation.SummaryText);
        _logPanel?.Append(explanation);
    }

    private double? ResolvePopupAutoHideSeconds(string type, JsonElement root)
    {
        if (_resultPopup == null)
        {
            return null;
        }

        if (!IsAiEvent(type, root))
        {
            return null;
        }

        return Math.Max(0.5, _resultPopup.AutoHideSeconds * 0.5);
    }

    private static bool ShouldShowResultPopup(string type)
        => ResultPopupEventTypes.Contains(type)
           || string.Equals(type, SanguoAiDecisionMade.EventType, StringComparison.Ordinal);

    private static bool IsAiEvent(string type, JsonElement root)
    {
        if (string.Equals(type, SanguoAiDecisionMade.EventType, StringComparison.Ordinal))
        {
            return true;
        }

        var ids = new[]
        {
            TryGetStringLoose(root, "AiPlayerId"),
            TryGetStringLoose(root, "PlayerId"),
            TryGetStringLoose(root, "BuyerId"),
            TryGetStringLoose(root, "OwnerId"),
            TryGetStringLoose(root, "PayerId"),
        };

        foreach (var id in ids)
        {
            if (!string.IsNullOrWhiteSpace(id) && IsAiPlayerId(id))
            {
                return true;
            }
        }

        return false;
    }

    private static string? TryGetStringLoose(JsonElement obj, string expectedName)
    {
        if (obj.ValueKind != JsonValueKind.Object)
        {
            return null;
        }

        foreach (var p in obj.EnumerateObject())
        {
            var name = p.Name;
            if (string.Equals(name, expectedName, StringComparison.OrdinalIgnoreCase)
                || string.Equals(name.Trim(), expectedName, StringComparison.OrdinalIgnoreCase))
            {
                if (p.Value.ValueKind == JsonValueKind.String)
                {
                    return p.Value.GetString();
                }
                return p.Value.ValueKind == JsonValueKind.Null ? null : p.Value.ToString();
            }
        }

        return null;
    }

    private static string TranslateOrFallback(string key)
    {
        if (string.IsNullOrWhiteSpace(key))
        {
            return string.Empty;
        }

        var translated = TranslationServer.Translate(key);
        if (!string.IsNullOrWhiteSpace(translated) && !string.Equals(translated, key, StringComparison.Ordinal))
        {
            return translated;
        }

        return key;
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

    private void ApplyLocalizedTexts(
        Button gameSettingsButton,
        Button logButton,
        Button cardsButton,
        Button btnResume,
        Button btnSave,
        Button btnLoad,
        Button btnSetting,
        Button btnHelp,
        Button btnReturn,
        Button btnQuit,
        Label? actionTitle,
        Button? skipActionButton,
        Label? guideTitle,
        Label? guideText)
    {
        _playerPrefix = TranslateOrFallback(UiHudPlayerPrefixKey, "Player");
        _datePrefix = TranslateOrFallback(UiHudDatePrefixKey, "Date");
        _moneyPrefix = TranslateOrFallback(UiHudMoneyPrefixKey, "Money");
        _scorePrefix = TranslateOrFallback(UiHudScorePrefixKey, "Score");
        _healthPrefix = TranslateOrFallback(UiHudHealthPrefixKey, "HP");
        _diceRollLabel = TranslateOrFallback(UiHudDiceRollKey, "Roll Dice");
        _diceWaitingLabel = TranslateOrFallback(UiHudDiceWaitingKey, "Waiting...");
        _diceAiLabel = TranslateOrFallback(UiHudDiceAiKey, "AI Turn");
        _diceValueLabel = TranslateOrFallback(UiHudDiceValueKey, "Dice");

        _activePlayer.Text = $"{_playerPrefix}: -";
        _date.Text = $"{_datePrefix}: -";
        _money.Text = $"{_moneyPrefix}: -";
        _score.Text = $"{_scorePrefix}: 0";
        _health.Text = $"{_healthPrefix}: 100";
        _diceButton.Text = _diceWaitingLabel;

        gameSettingsButton.Text = TranslateOrFallback(UiHudGameSettingsKey, "Game Settings");
        logButton.Text = TranslateOrFallback(UiHudLogKey, "Log");
        cardsButton.Text = TranslateOrFallback(UiHudCardsKey, "Cards");
        var playersTitle = GetNodeOrNull<Label>("TopBar/TopStack/PlayersPanel/VBox/PlayersTitle");
        if (playersTitle != null)
        {
            playersTitle.Text = TranslateOrFallback(UiHudPlayersTitleKey, "Players");
        }

        var settingsTitle = GetNodeOrNull<Label>("SettingsMenu/Center/Panel/VBox/Title");
        if (settingsTitle != null)
        {
            settingsTitle.Text = TranslateOrFallback(UiHudSettingsTitleKey, "Game Settings");
        }

        btnResume.Text = TranslateOrFallback(UiHudSettingsResumeKey, "Resume");
        btnSave.Text = TranslateOrFallback(UiHudSettingsSaveKey, "Save");
        btnLoad.Text = TranslateOrFallback(UiHudSettingsLoadKey, "Load");
        btnSetting.Text = TranslateOrFallback(UiHudSettingsSettingKey, "Setting");
        btnHelp.Text = TranslateOrFallback(UiHudSettingsHelpKey, "Help");
        btnReturn.Text = TranslateOrFallback(UiHudSettingsReturnKey, "Back to Menu");
        btnQuit.Text = TranslateOrFallback(UiHudSettingsQuitKey, "Quit");

        if (_cardsTitle != null)
        {
            _cardsTitle.Text = TranslateOrFallback(UiHudCardsTitleKey, "Cards");
        }
        if (_cardsEmptyLabel != null)
        {
            _cardsEmptyLabel.Text = TranslateOrFallback(UiHudCardsEmptyKey, "No cards");
        }
        if (_cardsCloseButton != null)
        {
            _cardsCloseButton.Text = TranslateOrFallback(UiHudCardsCloseKey, "Close");
        }
        if (_cardConfirmLabel != null)
        {
            _cardConfirmLabel.Text = TranslateOrFallback(UiHudCardsConfirmTextKey, "Use card");
        }
        if (_cardConfirmUseButton != null)
        {
            _cardConfirmUseButton.Text = TranslateOrFallback(UiHudCardsConfirmUseKey, "Use");
        }
        if (_cardConfirmCancelButton != null)
        {
            _cardConfirmCancelButton.Text = TranslateOrFallback(UiHudCardsConfirmCancelKey, "Cancel");
        }

        if (actionTitle != null)
        {
            actionTitle.Text = TranslateOrFallback(UiHudActionTitleKey, "Tile Actions");
        }

        if (skipActionButton != null)
        {
            skipActionButton.Text = TranslateOrFallback(UiHudActionSkipKey, "Skip");
        }

        if (guideTitle != null)
        {
            guideTitle.Text = TranslateOrFallback(UiHudGuideTitleKey, "Guide");
        }

        if (guideText != null)
        {
            guideText.Text = TranslateOrFallback(UiHudGuideStepKey, "Step");
        }
    }

    private Control? FindControlByPath(string path)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            return null;
        }

        return GetNodeOrNull<Control>(path);
    }

    private void AttachOverlaysToBottom()
    {
        MoveOverlayToBottom(GetNodeOrNull<Control>("SettingsMenu"));
        MoveOverlayToBottom(GetNodeOrNull<Control>("EventToast"));
        MoveOverlayToBottom(GetNodeOrNull<Control>("EventResultPopup"));
        MoveOverlayToBottom(GetNodeOrNull<Control>("EventLogPanel"));
        MoveOverlayToBottom(GetNodeOrNull<Control>("CardsPanel"));
        MoveOverlayToBottom(GetNodeOrNull<Control>("GuideHintPanel"));
        MoveOverlayToBottom(GetNodeOrNull<Control>("GuideOverlay"));
        MoveOverlayToBottom(GetNodeOrNull<Control>("ActionPanel"));
    }

    private void MoveOverlayToBottom(Node? node)
    {
        if (node == null)
        {
            return;
        }

        var overlayRoot = GetNodeOrNull<Control>("/root/Main/SplitRoot/BottomArea/BoardArea/Overlays/HudOverlay");
        if (overlayRoot == null)
        {
            return;
        }

        if (node.GetParent() == overlayRoot)
        {
            return;
        }

        node.GetParent()?.RemoveChild(node);
        overlayRoot.AddChild(node);
    }

    private void TryConnectBus(Callable callable)
    {
        if (_bus == null) return;

        TryConnectBusSignal(EventBusAdapter.SignalName.DomainEventEmitted, callable);
        TryConnectBusSignal("DomainEventEmitted", callable);
    }

    private void TryDisconnectBus(Callable callable)
    {
        if (_bus == null) return;

        TryDisconnectBusSignal(EventBusAdapter.SignalName.DomainEventEmitted, callable);
        TryDisconnectBusSignal("DomainEventEmitted", callable);
    }

    private void TryConnectBusSignal(StringName signal, Callable callable)
    {
        if (_bus == null) return;
        try
        {
            if (!_bus.IsConnected(signal, callable))
            {
                _bus.Connect(signal, callable);
            }
        }
        catch (Exception ex)
        {
            GD.PushWarning($"HUD: failed to connect to EventBus signal '{signal}': {ex.Message}");
        }
    }

    private void TryDisconnectBusSignal(StringName signal, Callable callable)
    {
        if (_bus == null) return;
        try
        {
            if (_bus.IsConnected(signal, callable))
            {
                _bus.Disconnect(signal, callable);
            }
        }
        catch { }
    }

    private void RegisterHandlers()
    {
        if (_eventHandlersController == null)
        {
            return;
        }

        HudEventHandlerRegistry.RegisterAll(_eventHandlersController, this);
    }

    public void HandleUiOnly()
    {
        // Intentionally empty: the UI feedback is recorded via RecordEventForUi(...)
        // before the per-type handler is invoked.
    }

    public void HandleCityBought(HudCityBoughtDto dto)
    {
        if (string.IsNullOrWhiteSpace(dto.BuyerId) || string.IsNullOrWhiteSpace(dto.CityId))
        {
            return;
        }

        _actionPanelController?.UpdateCityOwner(dto.BuyerId, dto.CityId);
    }

    public void HandleGameEnded()
    {
        var previousActive = _activePlayerId;
        _activePlayerId = null;
        _actionPanelController?.SetActivePlayerId(null);
        _actionPanelController?.HandleActivePlayerChanged(previousActive, null);
        _diceButton.Disabled = true;
        _diceButton.Text = TranslateOrFallback(UiHudGameOverKey, "Game Over");
        _activePlayer.Text = $"{_playerPrefix}: -";
        if (_avatar != null)
        {
            _avatar.Texture = null;
        }
        HideCardsPanel();
    }

    public void HandleCityTollPaid(HudCityTollPaidDto dto)
    {
        if (dto.TreasuryOverflow <= 0m)
        {
            return;
        }

        TryAppendSecurityAudit(
            action: MoneyCapAuditAction,
            reason: "money_cap_overflow",
            target: $"payer_id={dto.PayerId} owner_id={dto.OwnerId} city_id={dto.CityId} overflow={dto.TreasuryOverflow}",
            caller: "HUD.HandleCityTollPaid");
    }

    private static void TryAppendSecurityAudit(string action, string reason, string target, string caller)
    {
        SecurityAuditWriter.TryAppendSecurityAudit(
            action: action,
            reason: reason,
            target: target,
            caller: caller,
            eventType: "ui.security.audit",
            eventSource: nameof(HUD),
            eventId: Guid.NewGuid().ToString("N"));
    }

    public void HandleScore(HudScoreDto dto)
    {
        _score.Text = $"{_scorePrefix}: {dto.Value}";
    }

    public void HandleHealth(HudHealthDto dto)
    {
        _health.Text = $"{_healthPrefix}: {dto.Value}";
    }

    public void HandleTurn(HudTurnDto dto)
    {
        var previousActive = _activePlayerId;
        var dateKey = ComputeDateKey(dto.Year, dto.Month, dto.Day);
        if (dateKey > 0 && _lastDateKey > 0 && dateKey < _lastDateKey)
        {
            return;
        }

        if (dateKey > 0 && dateKey > _lastDateKey)
        {
            _lastDateKey = dateKey;
        }

        _activePlayerId = string.IsNullOrWhiteSpace(dto.ActivePlayerId) ? null : dto.ActivePlayerId;
        _actionPanelController?.SetActivePlayerId(_activePlayerId);
        _diceButton.Disabled = string.IsNullOrWhiteSpace(dto.ActivePlayerId) || IsAiPlayerId(dto.ActivePlayerId);
        _diceButton.Text = string.IsNullOrWhiteSpace(dto.ActivePlayerId)
            ? _diceRollLabel
            : (IsAiPlayerId(dto.ActivePlayerId) ? _diceAiLabel : _diceRollLabel);
        _btnSave.Disabled = string.IsNullOrWhiteSpace(dto.ActivePlayerId);
        UpdateActivePlayerIdentityDisplay();
        UpdateCardsButtonState();
        _date.Text = $"{_datePrefix}: {dto.Year:D4}-{dto.Month:D2}-{dto.Day:D2}";
        _actionPanelController?.HandleActivePlayerChanged(previousActive, _activePlayerId);

        if (_cardsPanel != null && _cardsPanel.Visible)
        {
            RefreshCardsList();
        }
    }

    private static int ComputeDateKey(int year, int month, int day)
    {
        if (year <= 0 || month <= 0 || day <= 0)
        {
            return -1;
        }

        return (year * 10000) + (month * 100) + day;
    }

    private static bool IsAiPlayerId(string playerId)
    {
        return !string.IsNullOrWhiteSpace(playerId) && playerId.StartsWith("ai-", StringComparison.OrdinalIgnoreCase);
    }

    public void HandlePlayerStateChanged(HudPlayerStateDto dto)
    {
        if (string.IsNullOrWhiteSpace(dto.PlayerId))
        {
            return;
        }

        _playerStatesById[dto.PlayerId] = new PlayerStateSnapshot(dto.Money, dto.PositionIndex);
        UpdatePlayersList();

        if (_activePlayerId != null && string.Equals(dto.PlayerId, _activePlayerId, StringComparison.Ordinal))
        {
            _money.Text = $"{_moneyPrefix}: {dto.Money}";
        }
    }

    public void HandleDiceRolled(HudDiceRolledDto dto)
    {
        if (!string.IsNullOrWhiteSpace(dto.PlayerId)
            && _activePlayerId != null
            && !string.Equals(dto.PlayerId, _activePlayerId, StringComparison.Ordinal))
        {
            return;
        }

        _diceButton.Text = $"{_diceValueLabel}: {dto.Value}";
    }

    public void HandleGameStarted(HudGameStartedDto dto)
    {
        _characterIdByPlayerId.Clear();
        foreach (var assignment in dto.CharacterAssignments)
        {
            if (string.IsNullOrWhiteSpace(assignment.Key) || string.IsNullOrWhiteSpace(assignment.Value))
            {
                continue;
            }

            _characterIdByPlayerId[assignment.Key] = assignment.Value;
        }

        if (dto.PlayerIds != null)
        {
            foreach (var playerId in dto.PlayerIds)
            {
                if (string.IsNullOrWhiteSpace(playerId))
                {
                    continue;
                }

                if (!_playerStatesById.ContainsKey(playerId))
                {
                    _playerStatesById[playerId] = new PlayerStateSnapshot(dto.StartingMoneyPreset, 0);
                }
            }
        }

        InitializeActionCardsForPlayers(dto.PlayerIds);
        TryLoadCharacterCatalog();
        UpdateActivePlayerIdentityDisplay();
        UpdatePlayersList();
        RefreshCardsList();
    }

    private void TryLoadCharacterCatalog()
    {
        _characterNameKeyById.Clear();
        _portraitPathByCharacterId.Clear();

        var loader = ResolveResourceLoader();
        var pack = ResolveContentPack(loader);
        if (!SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, pack, out var catalog, out _))
        {
            return;
        }

        foreach (var c in catalog.Characters)
        {
            if (string.IsNullOrWhiteSpace(c.CharacterId))
            {
                continue;
            }

            _characterNameKeyById[c.CharacterId] = c.NameKey ?? c.CharacterId;
            _portraitPathByCharacterId[c.CharacterId] = c.PortraitPath ?? string.Empty;
        }
    }

    private void UpdateActivePlayerIdentityDisplay()
    {
        var pid = _activePlayerId;
        if (string.IsNullOrWhiteSpace(pid))
        {
            _activePlayer.Text = $"{_playerPrefix}: -";
            if (_avatar != null)
            {
                _avatar.Texture = null;
            }
            return;
        }

        if (!_characterIdByPlayerId.TryGetValue(pid, out var characterId) || string.IsNullOrWhiteSpace(characterId))
        {
            _activePlayer.Text = $"{_playerPrefix}: {pid}";
            if (_avatar != null)
            {
                _avatar.Texture = null;
            }
            return;
        }

        _activePlayer.Text = $"{_playerPrefix}: {pid}";

        if (_avatar == null)
        {
            return;
        }

        if (_portraitCache.TryGetValue(characterId, out var cached))
        {
            _avatar.Texture = cached;
            return;
        }

        if (!_portraitPathByCharacterId.TryGetValue(characterId, out var path) || string.IsNullOrWhiteSpace(path))
        {
            _avatar.Texture = null;
            return;
        }

        if (!ResourceLoader.Exists(path))
        {
            _avatar.Texture = null;
            return;
        }

        try
        {
            var tex = GD.Load<Texture2D>(path);
            if (tex != null)
            {
                _portraitCache[characterId] = tex;
            }
            _avatar.Texture = tex;
        }
        catch
        {
            _avatar.Texture = null;
        }
    }

    private void UpdatePlayersList()
    {
        if (_playersPanelController == null)
        {
            return;
        }
        _playersPanelController.Render(_playerStatesById, ResolvePlayerDisplayName, IsAiPlayerId);
    }

    private void InitializeActionCardsForPlayers(IReadOnlyList<string> playerIds)
    {
        _cardsByPlayerId.Clear();

        if (playerIds == null || playerIds.Count == 0)
        {
            return;
        }

        if (_cardIds.Count == 0)
        {
            TryLoadUiCatalogLabels();
        }

        if (_cardIds.Count == 0)
        {
            return;
        }

        foreach (var playerId in playerIds)
        {
            if (string.IsNullOrWhiteSpace(playerId))
            {
                continue;
            }

            var cards = new Dictionary<string, int>(StringComparer.Ordinal);
            _cardsByPlayerId[playerId] = cards;

            var remaining = MaxActionCardsPerPlayer;
            foreach (var cardId in _cardIds)
            {
                if (remaining <= 0)
                {
                    break;
                }

                var add = Math.Min(InitialActionCardCopiesPerType, remaining);
                if (add <= 0)
                {
                    break;
                }

                cards[cardId] = add;
                remaining -= add;
            }
        }
    }

    private void UpdateCardsFromEvent(string type, JsonElement root)
    {
        if (string.Equals(type, SanguoCardLost.EventType, StringComparison.Ordinal))
        {
            var playerId = TryGetStringLoose(root, "PlayerId") ?? string.Empty;
            var cardId = TryGetStringLoose(root, "CardId") ?? string.Empty;
            if (!string.IsNullOrWhiteSpace(playerId) && !string.IsNullOrWhiteSpace(cardId))
            {
                RemoveActionCard(playerId, cardId, 1);
            }
        }

        if (string.Equals(type, SanguoLootGranted.EventType, StringComparison.Ordinal))
        {
            var playerId = TryGetStringLoose(root, "PlayerId") ?? string.Empty;
            var cardId = TryGetStringLoose(root, "CardId") ?? string.Empty;
            if (!string.IsNullOrWhiteSpace(playerId) && !string.IsNullOrWhiteSpace(cardId))
            {
                AddActionCard(playerId, cardId, 1);
            }
        }

        if (_cardsPanel != null && _cardsPanel.Visible && !string.IsNullOrWhiteSpace(_activePlayerId))
        {
            RefreshCardsList();
        }
    }

    private void AddActionCard(string playerId, string cardId, int count)
    {
        if (count <= 0)
        {
            return;
        }

        var cards = GetOrCreatePlayerCards(playerId);
        if (cards == null)
        {
            return;
        }

        var total = cards.Values.Sum();
        if (total >= MaxActionCardsPerPlayer)
        {
            return;
        }

        var add = Math.Min(count, MaxActionCardsPerPlayer - total);
        if (add <= 0)
        {
            return;
        }

        if (cards.TryGetValue(cardId, out var existing))
        {
            cards[cardId] = existing + add;
            return;
        }

        cards[cardId] = add;
    }

    private void RemoveActionCard(string playerId, string cardId, int count)
    {
        if (count <= 0)
        {
            return;
        }

        if (!_cardsByPlayerId.TryGetValue(playerId, out var cards))
        {
            return;
        }

        if (!cards.TryGetValue(cardId, out var existing) || existing <= 0)
        {
            return;
        }

        var next = existing - count;
        if (next <= 0)
        {
            cards.Remove(cardId);
            return;
        }

        cards[cardId] = next;
    }

    private Dictionary<string, int>? GetOrCreatePlayerCards(string playerId)
    {
        if (string.IsNullOrWhiteSpace(playerId))
        {
            return null;
        }

        if (_cardsByPlayerId.TryGetValue(playerId, out var cards))
        {
            return cards;
        }

        var created = new Dictionary<string, int>(StringComparer.Ordinal);
        _cardsByPlayerId[playerId] = created;
        return created;
    }

    private void UpdateCardsButtonState()
    {
        if (_cardsButton == null)
        {
            return;
        }

        var active = _activePlayerId ?? string.Empty;
        _cardsButton.Disabled = _cardIds.Count == 0 || string.IsNullOrWhiteSpace(active) || IsAiPlayerId(active);
    }

    private void ToggleCardsPanel()
    {
        if (_cardsPanel == null)
        {
            return;
        }

        if (_cardsPanel.Visible)
        {
            HideCardsPanel();
            return;
        }

        ShowCardsPanel();
    }

    private void ShowCardsPanel()
    {
        if (_cardsPanel == null)
        {
            return;
        }

        _cardsPanel.Visible = true;
        RefreshCardsList();
    }

    private void HideCardsPanel()
    {
        if (_cardsPanel == null)
        {
            return;
        }

        HideCardConfirm();
        _cardsPanel.Visible = false;
    }

    private void RefreshCardsList()
    {
        if (_cardsList == null || _cardsEmptyLabel == null)
        {
            return;
        }

        foreach (var child in _cardsList.GetChildren())
        {
            child.QueueFree();
        }

        var playerId = _activePlayerId ?? string.Empty;
        if (string.IsNullOrWhiteSpace(playerId) || !_cardsByPlayerId.TryGetValue(playerId, out var cards) || cards.Count == 0)
        {
            _cardsEmptyLabel.Visible = true;
            return;
        }

        var entries = cards
            .Where(kv => kv.Value > 0)
            .OrderBy(kv => kv.Key, StringComparer.Ordinal)
            .ToArray();

        if (entries.Length == 0)
        {
            _cardsEmptyLabel.Visible = true;
            return;
        }

        _cardsEmptyLabel.Visible = false;

        foreach (var (cardId, count) in entries)
        {
            var row = new HBoxContainer();
            var nameKey = _cardNameKeyById.TryGetValue(cardId, out var key) ? key : string.Empty;
            var displayName = TranslateOrFallback(string.IsNullOrWhiteSpace(nameKey) ? cardId : nameKey, cardId);
            var label = new Label { Text = $"{displayName} x{count}" };
            var useButton = new Button { Text = TranslateOrFallback(UiHudCardsUseKey, "Use") };
            if (IsAiPlayerId(playerId))
            {
                useButton.Disabled = true;
            }
            useButton.Pressed += () => ShowCardConfirm(cardId);
            row.AddChild(label);
            row.AddChild(useButton);
            _cardsList.AddChild(row);
        }
    }

    private void ShowCardConfirm(string cardId)
    {
        if (_cardConfirmPanel == null || string.IsNullOrWhiteSpace(cardId))
        {
            return;
        }

        _pendingCardId = cardId;
        if (_cardConfirmLabel != null)
        {
            var nameKey = _cardNameKeyById.TryGetValue(cardId, out var key) ? key : string.Empty;
            var displayName = TranslateOrFallback(string.IsNullOrWhiteSpace(nameKey) ? cardId : nameKey, cardId);
            var prefix = TranslateOrFallback(UiHudCardsConfirmTextKey, "Use card");
            _cardConfirmLabel.Text = $"{prefix}: {displayName}";
        }

        _cardConfirmPanel.Visible = true;
    }

    private void HideCardConfirm()
    {
        if (_cardConfirmPanel == null)
        {
            _pendingCardId = null;
            return;
        }

        _cardConfirmPanel.Visible = false;
        _pendingCardId = null;
    }

    private void OnConfirmUseCard()
    {
        var cardId = _pendingCardId ?? string.Empty;
        if (string.IsNullOrWhiteSpace(cardId))
        {
            return;
        }

        HideCardConfirm();
        PublishActionCardPlay(cardId);
        HideCardsPanel();
    }

    private void PublishActionCardPlay(string cardId)
    {
        if (_bus == null)
        {
            return;
        }

        var playerId = _activePlayerId ?? string.Empty;
        if (string.IsNullOrWhiteSpace(playerId) || IsAiPlayerId(playerId))
        {
            return;
        }

        var payload = JsonSerializer.Serialize(new
        {
            GameId = "g1",
            PlayerId = playerId,
            CardId = cardId,
            CorrelationId = Guid.NewGuid().ToString("N"),
            CausationId = UiActionCardPlayEventType
        });

        _bus.PublishSimple(UiActionCardPlayEventType, nameof(HUD), payload);
    }

    private string ResolvePlayerDisplayName(string playerId)
    {
        if (string.IsNullOrWhiteSpace(playerId))
        {
            return string.Empty;
        }

        if (_characterIdByPlayerId.TryGetValue(playerId, out var characterId)
            && !string.IsNullOrWhiteSpace(characterId)
            && _characterNameKeyById.TryGetValue(characterId, out var nameKey)
            && !string.IsNullOrWhiteSpace(nameKey))
        {
            return TranslateOrFallback(nameKey);
        }

        return playerId;
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

    public void HandleTokenMoved(HudTokenMovedDto dto)
    {
        _actionPanelController?.HandleTokenMoved(dto);
    }

    private void TryLoadMapTilesForUi()
    {
        _tilesByIndex.Clear();
        _tileNameKeyById.Clear();

        try
        {
            var loader = ResolveResourceLoader();
            var pack = ResolveContentPack(loader);
            var correlationId = Guid.NewGuid().ToString("N");
            if (!SanguoMapConfigLoader.TryLoadMap(loader, correlationId, out var map, out _, out _, pack))
            {
                return;
            }

            _actionPanelController?.LoadMapTiles(map);

            foreach (var tile in map.Tiles)
            {
                var actions = tile.Actions is null ? Array.Empty<string>() : new List<string>(tile.Actions).ToArray();
                _tilesByIndex[tile.PositionIndex] = new TileInfo(
                    TileId: tile.TileId ?? string.Empty,
                    TileType: tile.TileType ?? string.Empty,
                    Name: tile.Name ?? string.Empty,
                    Actions: actions);
                if (!string.IsNullOrWhiteSpace(tile.TileId))
                {
                    _tileNameKeyById[tile.TileId] = tile.Name ?? string.Empty;
                }
            }
        }
        catch
        {
        }
    }

    private void TryLoadUiCatalogLabels()
    {
        _regionNameKeyById.Clear();
        _cardNameKeyById.Clear();
        _cardIds.Clear();
        _relicNameKeyById.Clear();
        _randomEventNameKeyById.Clear();
        _randomEventPoolNameKeyById.Clear();

        try
        {
            var loader = ResolveResourceLoader();
            var pack = ResolveContentPack(loader);
            if (SanguoRegionsCatalogLoader.TryLoadRegionsCatalog(loader, pack, out var regions, out _))
            {
                foreach (var region in regions.Regions)
                {
                    if (!string.IsNullOrWhiteSpace(region.RegionId))
                    {
                        _regionNameKeyById[region.RegionId] = region.NameKey ?? string.Empty;
                    }
                }
            }

            if (SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, pack, out var cards, out _))
            {
                var seen = new HashSet<string>(StringComparer.Ordinal);
                foreach (var card in cards.Cards)
                {
                    if (!string.IsNullOrWhiteSpace(card.CardId))
                    {
                        _cardNameKeyById[card.CardId] = card.NameKey ?? string.Empty;
                        if (seen.Add(card.CardId))
                        {
                            _cardIds.Add(card.CardId);
                        }
                    }
                }
            }

            if (_cardIds.Count > 1)
            {
                _cardIds.Sort(StringComparer.Ordinal);
            }

            if (SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, pack, out var relics, out _))
            {
                foreach (var relic in relics.Relics)
                {
                    if (!string.IsNullOrWhiteSpace(relic.RelicId))
                    {
                        _relicNameKeyById[relic.RelicId] = relic.NameKey ?? string.Empty;
                    }
                }
            }

            if (SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, pack, out var eventsCatalog, out _))
            {
                foreach (var evt in eventsCatalog.Events)
                {
                    if (!string.IsNullOrWhiteSpace(evt.EventId))
                    {
                        _randomEventNameKeyById[evt.EventId] = evt.NameKey ?? string.Empty;
                    }
                }

                foreach (var pool in eventsCatalog.EventPools)
                {
                    if (!string.IsNullOrWhiteSpace(pool.PoolId))
                    {
                        _randomEventPoolNameKeyById[pool.PoolId] = pool.NameKey ?? string.Empty;
                    }
                }
            }
        }
        catch
        {
        }
    }

    private readonly record struct TileInfo(string TileId, string TileType, string Name, string[] Actions);
    public void SetScore(int v) => _score.Text = $"{_scorePrefix}: {v}";
    public void SetHealth(int v) => _health.Text = $"{_healthPrefix}: {v}";
}
