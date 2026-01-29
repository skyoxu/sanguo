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
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

public partial class HUD : Control
{
    private static readonly JsonDocumentOptions JsonOptions = new() { MaxDepth = 32 };
    private const string ActionBuild = "build";
    private const string UiHudDiceRollEventType = "ui.hud.dice.roll";
    private const string UiHudSaveEventType = "ui.hud.save";
    private const string UiHudLoadEventType = "ui.hud.load";
    private const string UiTileActionSelectedEventType = "ui.sanguo.tile.action.selected";
    private const string MoneyCapAuditAction = "SANGUO_MONEY_CAPPED";
    private const string EventLogOverlayFlag = "event_log_overlay";
    private const string DefaultSaveSlotId = "quick";

    private Label _score = default!;
    private Label _health = default!;

    private Label _activePlayer = default!;
    private Label _date = default!;
    private Label _money = default!;
    private TextureRect? _avatar;
    private Button _diceButton = default!;
    private Button _saveButton = default!;
    private Button _loadButton = default!;

    private Control? _actionPanel;
    private Label? _actionTitle;
    private VBoxContainer? _actionButtons;
    private Button? _skipActionButton;

    private string? _activePlayerId;
    private int _lastDateKey;
    private EventBusAdapter? _bus;
    private readonly Dictionary<string, Action<JsonElement>> _handlers = new(StringComparer.Ordinal);

    private EventToast? _toast;
    private EventLogPanel? _logPanel;
    private bool _logVisible;

    private readonly Dictionary<int, TileInfo> _tilesByIndex = new();
    private readonly Dictionary<string, string> _tileNameKeyById = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _cityOwnersByCityId = new(StringComparer.Ordinal);
    private bool _awaitingTileAction;
    private string _awaitingCorrelationId = string.Empty;
    private int _awaitingToIndex;

    private readonly Dictionary<string, string> _regionNameKeyById = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _cardNameKeyById = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _relicNameKeyById = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _randomEventNameKeyById = new(StringComparer.Ordinal);

    private readonly Dictionary<string, string> _characterIdByPlayerId = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _characterNameKeyById = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _portraitPathByCharacterId = new(StringComparer.Ordinal);
    private readonly Dictionary<string, Texture2D> _portraitCache = new(StringComparer.Ordinal);
    private ResourceLoaderAdapter? _fallbackResourceLoader;

    public override void _Ready()
    {
        _lastDateKey = -1;
        _score = GetNode<Label>("TopBar/HBox/ScoreLabel");
        _health = GetNode<Label>("TopBar/HBox/HealthLabel");

        _activePlayer = GetNode<Label>("TopBar/HBox/ActivePlayerLabel");
        _date = GetNode<Label>("TopBar/HBox/DateLabel");
        _money = GetNode<Label>("TopBar/HBox/MoneyLabel");
        _avatar = GetNodeOrNull<TextureRect>("TopBar/HBox/Avatar");
        _diceButton = GetNode<Button>("TopBar/HBox/DiceButton");
        _diceButton.Pressed += OnDicePressed;
        _diceButton.Disabled = true;
        _diceButton.Text = "Waiting...";

        _saveButton = GetNode<Button>("TopBar/HBox/SaveButton");
        _saveButton.Pressed += OnSavePressed;
        _saveButton.Disabled = true;

        _loadButton = GetNode<Button>("TopBar/HBox/LoadButton");
        _loadButton.Pressed += OnLoadPressed;
        _loadButton.Disabled = false;

        _actionPanel = GetNodeOrNull<Control>("ActionPanel");
        _actionTitle = GetNodeOrNull<Label>("ActionPanel/VBox/ActionTitle");
        _actionButtons = GetNodeOrNull<VBoxContainer>("ActionPanel/VBox/Actions");
        _skipActionButton = GetNodeOrNull<Button>("ActionPanel/VBox/SkipButton");
        if (_skipActionButton != null)
        {
            _skipActionButton.Pressed += OnSkipTileActionPressed;
        }

        _toast = GetNodeOrNull<EventToast>("EventToast");
        _logPanel = GetNodeOrNull<EventLogPanel>("EventLogPanel");
        _logVisible = false;
        if (_logPanel != null)
        {
            var ff = GetNodeOrNull<FeatureFlags>("/root/FeatureFlags");
            _logVisible = ff != null && ff.IsEnabled(EventLogOverlayFlag);
            _logPanel.Visible = _logVisible;
        }

        RegisterHandlers();
        TryLoadMapTilesForUi();
        TryLoadUiCatalogLabels();
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

        var callable = new Callable(this, nameof(OnDomainEventEmitted));
        TryConnectBus(callable);
    }

    public override void _ExitTree()
    {
        _diceButton.Pressed -= OnDicePressed;
        _saveButton.Pressed -= OnSavePressed;
        _loadButton.Pressed -= OnLoadPressed;
        if (_skipActionButton != null)
        {
            _skipActionButton.Pressed -= OnSkipTileActionPressed;
        }

        if (_bus == null)
        {
            return;
        }

        var callable = new Callable(this, nameof(OnDomainEventEmitted));
        TryDisconnectBus(callable);

        _bus = null;
        _fallbackResourceLoader = null;
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

        if (_awaitingTileAction)
        {
            _toast?.ShowMessage("Please choose a tile action or Skip.");
            return;
        }

        var playerId = _activePlayerId ?? "";
        if (string.IsNullOrWhiteSpace(playerId))
        {
            _toast?.ShowMessage("Game is starting. Please wait...");
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

        if (_awaitingTileAction)
        {
            _toast?.ShowMessage("Please choose a tile action or Skip.");
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

        if (_awaitingTileAction)
        {
            _toast?.ShowMessage("Please choose a tile action or Skip.");
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

    private void OnDomainEventEmitted(string type, string source, string dataJson, string id, string specVersion, string dataContentType, string timestampIso)
    {
        if (string.IsNullOrWhiteSpace(source) || source.Length > 64)
        {
            return;
        }

        var json = string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson;
        if (!_handlers.TryGetValue(type, out var handler))
        {
            return;
        }

        if (json.Length > 65536)
        {
            GD.PushWarning($"HUD ignored over-sized event payload (type='{type}', length={json.Length}).");
            return;
        }

        try
        {
            using var doc = JsonDocument.Parse(json, JsonOptions);
            RecordEventForUi(type, source, id, timestampIso, doc.RootElement);
            handler(doc.RootElement);
        }
        catch (System.Exception ex)
        {
            GD.PushWarning($"HUD failed to handle event '{type}': {ex.Message}");
        }
    }

    private void RecordEventForUi(string type, string source, string id, string timestampIso, JsonElement root)
    {
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
            eventLabelById);
        _toast?.ShowMessage(explanation.SummaryText);
        _logPanel?.Append(explanation);
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
        if (_handlers.Count != 0)
        {
            return;
        }

        _handlers[SanguoGameStarted.EventType] = HandleGameStartedEvent;
        _handlers[CoreGameEvents.ScoreUpdated] = HandleScoreEvent;
        _handlers[CoreGameEvents.ScoreChanged] = HandleScoreEvent;

        _handlers[CoreGameEvents.HealthUpdated] = HandleHealthEvent;
        _handlers[CoreGameEvents.PlayerHealthChanged] = HandleHealthEvent;

        _handlers[SanguoGameTurnStarted.EventType] = HandleTurnEvent;
        _handlers[SanguoGameTurnAdvanced.EventType] = HandleTurnEvent;
        _handlers[SanguoGameTurnEnded.EventType] = HandleUiOnlyEvent;

        _handlers[SanguoPlayerStateChanged.EventType] = HandlePlayerStateChangedEvent;
        _handlers[SanguoDiceRolled.EventType] = HandleDiceRolledEvent;
        _handlers[SanguoCityTollPaid.EventType] = HandleCityTollPaidEvent;
        _handlers[SanguoCityBought.EventType] = HandleCityBoughtEvent;
        _handlers[SanguoCityOwnerChanged.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoActionCardPlayed.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoCombatStarted.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoCombatEnded.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoPlayerEliminated.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoGameSaved.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoGameLoaded.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoTokenMoved.EventType] = HandleTokenMovedEvent;
        _handlers[SanguoMonthSettled.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoSeasonEventApplied.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoYearPriceAdjusted.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoLootGranted.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoRelicApplied.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoCardLost.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoRegionCaptured.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoRegionLost.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoRandomEventApplied.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoCityTollSynergyPaid.EventType] = HandleUiOnlyEvent;
        _handlers[SanguoGameEnded.EventType] = HandleGameEndedEvent;
    }

    private void HandleUiOnlyEvent(JsonElement _)
    {
        // Intentionally empty: the UI feedback is recorded via RecordEventForUi(...)
        // before the per-type handler is invoked.
    }

    private void HandleCityBoughtEvent(JsonElement root)
    {
        if (!root.TryGetProperty("BuyerId", out var buyerProp) || buyerProp.ValueKind != JsonValueKind.String)
        {
            return;
        }

        if (!root.TryGetProperty("CityId", out var cityProp) || cityProp.ValueKind != JsonValueKind.String)
        {
            return;
        }

        var buyerId = buyerProp.GetString() ?? string.Empty;
        var cityId = cityProp.GetString() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(buyerId) || string.IsNullOrWhiteSpace(cityId))
        {
            return;
        }

        _cityOwnersByCityId[cityId] = buyerId;
    }

    private void HandleGameEndedEvent(JsonElement root)
    {
        _activePlayerId = null;
        _diceButton.Disabled = true;
        _diceButton.Text = "Game Over";
        _activePlayer.Text = "Name: -";
        if (_avatar != null)
        {
            _avatar.Texture = null;
        }
    }

    private void HandleCityTollPaidEvent(JsonElement root)
    {
        decimal overflow = 0m;
        if (root.TryGetProperty("TreasuryOverflow", out var ov) && ov.ValueKind == JsonValueKind.Number)
        {
            if (!ov.TryGetDecimal(out overflow))
            {
                overflow = ov.GetInt64();
            }
        }

        if (overflow <= 0m)
        {
            return;
        }

        var payerId = root.TryGetProperty("PayerId", out var payer) ? payer.GetString() : null;
        var ownerId = root.TryGetProperty("OwnerId", out var owner) ? owner.GetString() : null;
        var cityId = root.TryGetProperty("CityId", out var city) ? city.GetString() : null;

        TryAppendSecurityAudit(
            action: MoneyCapAuditAction,
            reason: "money_cap_overflow",
            target: $"payer_id={payerId} owner_id={ownerId} city_id={cityId} overflow={overflow}",
            caller: "HUD.HandleCityTollPaidEvent");
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

    private void HandleScoreEvent(JsonElement root)
    {
        int v = 0;
        if (root.TryGetProperty("value", out var val)) v = val.GetInt32();
        else if (root.TryGetProperty("score", out var sc)) v = sc.GetInt32();
        _score.Text = $"Score: {v}";
    }

    private void HandleHealthEvent(JsonElement root)
    {
        int v = 0;
        if (root.TryGetProperty("value", out var val)) v = val.GetInt32();
        else if (root.TryGetProperty("health", out var hp)) v = hp.GetInt32();
        _health.Text = $"HP: {v}";
    }

    private void HandleTurnEvent(JsonElement root)
    {
        var previousActive = _activePlayerId;
        string active = "";
        int year = 0;
        int month = 0;
        int day = 0;

        if (root.TryGetProperty("ActivePlayerId", out var ap)) active = ap.GetString() ?? "";
        if (root.TryGetProperty("Year", out var y)) year = y.GetInt32();
        if (root.TryGetProperty("Month", out var m)) month = m.GetInt32();
        if (root.TryGetProperty("Day", out var d)) day = d.GetInt32();

        var dateKey = ComputeDateKey(year, month, day);
        if (dateKey > 0 && _lastDateKey > 0 && dateKey < _lastDateKey)
        {
            return;
        }

        if (dateKey > 0 && dateKey > _lastDateKey)
        {
            _lastDateKey = dateKey;
        }

        _activePlayerId = string.IsNullOrWhiteSpace(active) ? null : active;
        _diceButton.Disabled = string.IsNullOrWhiteSpace(active) || IsAiPlayerId(active);
        _diceButton.Text = string.IsNullOrWhiteSpace(active) ? "Roll Dice" : (IsAiPlayerId(active) ? "AI Turn" : "Roll Dice");
        _saveButton.Disabled = string.IsNullOrWhiteSpace(active);
        UpdateActivePlayerIdentityDisplay();
        _date.Text = $"Date: {year:D4}-{month:D2}-{day:D2}";

        if (_awaitingTileAction && previousActive != null && !string.Equals(previousActive, _activePlayerId, StringComparison.Ordinal))
        {
            HideTileActionPanel();
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

    private void HandlePlayerStateChangedEvent(JsonElement root)
    {
        if (!root.TryGetProperty("PlayerId", out var pidEl))
        {
            return;
        }

        var pid = pidEl.GetString() ?? "";
        if (string.IsNullOrWhiteSpace(pid) || _activePlayerId == null || pid != _activePlayerId)
        {
            return;
        }

        if (!root.TryGetProperty("Money", out var moneyEl))
        {
            return;
        }

        decimal money = moneyEl.ValueKind switch
        {
            JsonValueKind.Number when moneyEl.TryGetDecimal(out var dec) => dec,
            JsonValueKind.Number => moneyEl.GetInt64(),
            _ => 0m,
        };

        _money.Text = $"Money: {money}";
    }

    private void HandleDiceRolledEvent(JsonElement root)
    {
        string pid = "";
        if (root.TryGetProperty("PlayerId", out var pidEl))
        {
            pid = pidEl.GetString() ?? "";
        }

        if (!string.IsNullOrWhiteSpace(pid) && _activePlayerId != null && pid != _activePlayerId)
        {
            return;
        }

        int value = 0;
        if (root.TryGetProperty("Value", out var v))
        {
            value = v.GetInt32();
        }
        else if (root.TryGetProperty("value", out var vv))
        {
            value = vv.GetInt32();
        }

        _diceButton.Text = $"Dice: {value}";
    }

    private void HandleGameStartedEvent(JsonElement root)
    {
        if (!root.TryGetProperty("game_start_config", out var cfg) || cfg.ValueKind != JsonValueKind.Object)
        {
            return;
        }

        if (!cfg.TryGetProperty("character_assignments", out var assigns) || assigns.ValueKind != JsonValueKind.Object)
        {
            return;
        }

        _characterIdByPlayerId.Clear();
        foreach (var prop in assigns.EnumerateObject())
        {
            var playerId = prop.Name ?? string.Empty;
            var characterId = prop.Value.ValueKind == JsonValueKind.String ? (prop.Value.GetString() ?? string.Empty) : string.Empty;
            if (string.IsNullOrWhiteSpace(playerId) || string.IsNullOrWhiteSpace(characterId))
            {
                continue;
            }

            _characterIdByPlayerId[playerId] = characterId;
        }

        TryLoadCharacterCatalog();
        UpdateActivePlayerIdentityDisplay();
    }

    private void TryLoadCharacterCatalog()
    {
        _characterNameKeyById.Clear();
        _portraitPathByCharacterId.Clear();

        var loader = ResolveResourceLoader();
        if (!SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out var catalog, out _))
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
            _activePlayer.Text = "Player: -";
            if (_avatar != null)
            {
                _avatar.Texture = null;
            }
            return;
        }

        if (!_characterIdByPlayerId.TryGetValue(pid, out var characterId) || string.IsNullOrWhiteSpace(characterId))
        {
            _activePlayer.Text = $"Player: {pid}";
            if (_avatar != null)
            {
                _avatar.Texture = null;
            }
            return;
        }

        _activePlayer.Text = $"Player: {pid}";

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

    private void HandleTokenMovedEvent(JsonElement root)
    {
        if (_tilesByIndex.Count == 0)
        {
            return;
        }

        if (!root.TryGetProperty("PlayerId", out var pidProp) || pidProp.ValueKind != JsonValueKind.String)
        {
            return;
        }

        var playerId = pidProp.GetString() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(playerId) || IsAiPlayerId(playerId))
        {
            return;
        }

        if (_activePlayerId == null || !string.Equals(_activePlayerId, playerId, StringComparison.Ordinal))
        {
            return;
        }

        if (!root.TryGetProperty("ToIndex", out var toProp) || !toProp.TryGetInt32(out var toIndex) || toIndex < 0)
        {
            return;
        }

        if (!_tilesByIndex.TryGetValue(toIndex, out var tile))
        {
            return;
        }

        var corr = root.TryGetProperty("CorrelationId", out var corrProp) && corrProp.ValueKind == JsonValueKind.String
            ? (corrProp.GetString() ?? string.Empty)
            : string.Empty;

        ShowTileActionPanel(playerId, toIndex, corr, tile);
    }

    private void ShowTileActionPanel(string playerId, int toIndex, string correlationId, TileInfo tile)
    {
        if (_actionPanel == null || _actionButtons == null || _skipActionButton == null || _bus == null)
        {
            return;
        }

        var actions = FilterTileActionsForUi(playerId, tile);
        if (actions.Length == 0)
        {
            return;
        }

        _awaitingTileAction = true;
        _awaitingCorrelationId = correlationId ?? string.Empty;
        _awaitingToIndex = toIndex;

        _diceButton.Disabled = true;

        if (_actionTitle != null)
        {
            _actionTitle.Text = $"Tile: {tile.Name}";
        }

        foreach (var child in _actionButtons.GetChildren())
        {
            if (child is Node n)
            {
                n.QueueFree();
            }
        }

        foreach (var action in actions)
        {
            var a = action ?? string.Empty;
            if (string.IsNullOrWhiteSpace(a))
            {
                continue;
            }

            var btn = new Button { Text = a, FocusMode = FocusModeEnum.All };
            btn.Pressed += () => OnTileActionPressed(playerId, toIndex, _awaitingCorrelationId, a);
            _actionButtons.AddChild(btn);
        }

        _actionPanel.Visible = true;
        _toast?.ShowMessage($"Choose action for '{tile.Name}' or Skip.");
    }

    private void OnTileActionPressed(string playerId, int toIndex, string correlationId, string action)
    {
        PublishTileActionSelected(playerId, toIndex, correlationId, action);
        HideTileActionPanel();
    }

    private void OnSkipTileActionPressed()
    {
        if (_activePlayerId == null)
        {
            return;
        }

        PublishTileActionSelected(_activePlayerId, _awaitingToIndex, _awaitingCorrelationId, "skip");
        HideTileActionPanel();
    }

    private void PublishTileActionSelected(string playerId, int toIndex, string correlationId, string action)
    {
        if (_bus == null)
        {
            return;
        }

        var payload = JsonSerializer.Serialize(new
        {
            GameId = "g1",
            PlayerId = playerId,
            ToIndex = toIndex,
            Action = action,
            CorrelationId = string.IsNullOrWhiteSpace(correlationId) ? Guid.NewGuid().ToString("N") : correlationId,
            CausationId = UiTileActionSelectedEventType,
        });

        _bus.PublishSimple(UiTileActionSelectedEventType, nameof(HUD), payload);
    }

    private void HideTileActionPanel()
    {
        _awaitingTileAction = false;
        _awaitingCorrelationId = string.Empty;
        _awaitingToIndex = 0;

        if (_actionPanel != null)
        {
            _actionPanel.Visible = false;
        }
    }

    private void TryLoadMapTilesForUi()
    {
        _tilesByIndex.Clear();
        _cityOwnersByCityId.Clear();
        _tileNameKeyById.Clear();

        try
        {
            var loader = ResolveResourceLoader();
            var correlationId = Guid.NewGuid().ToString("N");
            if (!SanguoMapConfigLoader.TryLoadMap(loader, correlationId, out var map, out _, out _))
            {
                return;
            }

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
        _relicNameKeyById.Clear();
        _randomEventNameKeyById.Clear();

        try
        {
            var loader = ResolveResourceLoader();
            if (SanguoRegionsCatalogLoader.TryLoadRegionsCatalog(loader, out var regions, out _))
            {
                foreach (var region in regions.Regions)
                {
                    if (!string.IsNullOrWhiteSpace(region.RegionId))
                    {
                        _regionNameKeyById[region.RegionId] = region.NameKey ?? string.Empty;
                    }
                }
            }

            if (SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, out var cards, out _))
            {
                foreach (var card in cards.Cards)
                {
                    if (!string.IsNullOrWhiteSpace(card.CardId))
                    {
                        _cardNameKeyById[card.CardId] = card.NameKey ?? string.Empty;
                    }
                }
            }

            if (SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, out var relics, out _))
            {
                foreach (var relic in relics.Relics)
                {
                    if (!string.IsNullOrWhiteSpace(relic.RelicId))
                    {
                        _relicNameKeyById[relic.RelicId] = relic.NameKey ?? string.Empty;
                    }
                }
            }

            if (SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out var eventsCatalog, out _))
            {
                foreach (var evt in eventsCatalog.Events)
                {
                    if (!string.IsNullOrWhiteSpace(evt.EventId))
                    {
                        _randomEventNameKeyById[evt.EventId] = evt.NameKey ?? string.Empty;
                    }
                }
            }
        }
        catch
        {
        }
    }

    private static bool IsCityTile(TileInfo tile) =>
        string.Equals((tile.TileType ?? string.Empty).Trim(), "city", StringComparison.OrdinalIgnoreCase);

    private static bool IsBuildAction(string actionId) =>
        string.Equals((actionId ?? string.Empty).Trim(), ActionBuild, StringComparison.OrdinalIgnoreCase);

    private static bool IsBuyLandAction(string actionId) =>
        string.Equals((actionId ?? string.Empty).Trim(), "buy_land", StringComparison.OrdinalIgnoreCase);

    private string[] FilterTileActionsForUi(string playerId, TileInfo tile)
    {
        if (tile.Actions.Length == 0)
        {
            return Array.Empty<string>();
        }

        var isCity = IsCityTile(tile);
        var cityId = (tile.TileId ?? string.Empty).Trim();
        var ownerId = string.Empty;
        var hasOwner = isCity
            && !string.IsNullOrWhiteSpace(cityId)
            && _cityOwnersByCityId.TryGetValue(cityId, out ownerId);
        var isOwnedByActive = hasOwner && string.Equals(ownerId, playerId, StringComparison.Ordinal);

        var filtered = new List<string>(tile.Actions.Length);
        foreach (var raw in tile.Actions)
        {
            var a = (raw ?? string.Empty).Trim();
            if (string.IsNullOrWhiteSpace(a))
            {
                continue;
            }

            if (IsBuildAction(a))
            {
                if (!isOwnedByActive)
                {
                    continue;
                }
            }
            else if (IsBuyLandAction(a))
            {
                if (!isCity || hasOwner)
                {
                    continue;
                }
            }

            filtered.Add(a);
        }

        return filtered.ToArray();
    }

    private readonly record struct TileInfo(string TileId, string TileType, string Name, string[] Actions);

    public void SetScore(int v) => _score.Text = $"Score: {v}";
    public void SetHealth(int v) => _health.Text = $"HP: {v}";
}
