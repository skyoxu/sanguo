using Godot;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Godot.Adapters;
using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

public partial class HUD : Control
{
    private const int MaxEventJsonChars = 64 * 1024;
    private static readonly JsonDocumentOptions JsonOptions = new() { MaxDepth = 32 };

    private Label _score = default!;
    private Label _health = default!;

    private Label _activePlayer = default!;
    private Label _date = default!;
    private Label _money = default!;
    private Button _diceButton = default!;

    private string? _activePlayerId;
    private EventBusAdapter? _bus;
    private readonly Dictionary<string, Action<JsonElement>> _handlers = new(StringComparer.Ordinal);

    private EventToast? _toast;
    private EventLogPanel? _logPanel;

    public override void _Ready()
    {
        _score = GetNode<Label>("TopBar/HBox/ScoreLabel");
        _health = GetNode<Label>("TopBar/HBox/HealthLabel");

        _activePlayer = GetNode<Label>("TopBar/HBox/ActivePlayerLabel");
        _date = GetNode<Label>("TopBar/HBox/DateLabel");
        _money = GetNode<Label>("TopBar/HBox/MoneyLabel");
        _diceButton = GetNode<Button>("TopBar/HBox/DiceButton");
        _diceButton.Pressed += OnDicePressed;

        _toast = GetNodeOrNull<EventToast>("EventToast");
        _logPanel = GetNodeOrNull<EventLogPanel>("EventLogPanel");

        RegisterHandlers();

        _bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (_bus == null)
        {
            GD.PushWarning("HUD: EventBus not found at /root/EventBus");
            return;
        }

        var callable = new Callable(this, nameof(OnDomainEventEmitted));
        if (!_bus.IsConnected(EventBusAdapter.SignalName.DomainEventEmitted, callable))
        {
            _bus.Connect(EventBusAdapter.SignalName.DomainEventEmitted, callable);
        }
    }

    public override void _ExitTree()
    {
        _diceButton.Pressed -= OnDicePressed;

        if (_bus == null)
        {
            return;
        }

        var callable = new Callable(this, nameof(OnDomainEventEmitted));
        if (_bus.IsConnected(EventBusAdapter.SignalName.DomainEventEmitted, callable))
        {
            _bus.Disconnect(EventBusAdapter.SignalName.DomainEventEmitted, callable);
        }

        _bus = null;
    }

    private void OnDicePressed()
    {
        if (_bus == null)
        {
            GD.PushWarning("HUD: EventBus not found; cannot publish ui.hud.dice.roll");
            return;
        }

        _bus.PublishSimple("ui.hud.dice.roll", nameof(HUD), "{}");
    }

    private void OnDomainEventEmitted(string type, string source, string dataJson, string id, string specVersion, string dataContentType, string timestampIso)
    {
        var json = string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson;
        if (json.Length > MaxEventJsonChars)
        {
            GD.PushWarning($"HUD ignored over-sized event payload (type='{type}', length={json.Length}).");
            return;
        }

        if (!_handlers.TryGetValue(type, out var handler))
        {
            return;
        }

        try
        {
            using var doc = JsonDocument.Parse(json, JsonOptions);
            RecordEventForUi(type, doc.RootElement);
            handler(doc.RootElement);
        }
        catch (System.Exception ex)
        {
            GD.PushWarning($"HUD failed to handle event '{type}': {ex.Message}");
        }
    }

    private void RecordEventForUi(string type, JsonElement root)
    {
        var message = BuildEventSummary(type, root);
        _toast?.ShowMessage(message);
        _logPanel?.Append(message);
    }

    private static string BuildEventSummary(string type, JsonElement root)
    {
        string? playerId = null;
        if (root.TryGetProperty("PlayerId", out var pid))
        {
            playerId = pid.GetString();
        }
        else if (root.TryGetProperty("ActivePlayerId", out var ap))
        {
            playerId = ap.GetString();
        }

        if (root.TryGetProperty("Value", out var value) && value.ValueKind == JsonValueKind.Number)
        {
            return string.IsNullOrWhiteSpace(playerId) ? $"{type} value={value}" : $"{type} player={playerId} value={value}";
        }

        if (root.TryGetProperty("CityId", out var cityId))
        {
            var city = cityId.GetString();
            return string.IsNullOrWhiteSpace(playerId) ? $"{type} city={city}" : $"{type} player={playerId} city={city}";
        }

        return string.IsNullOrWhiteSpace(playerId) ? type : $"{type} player={playerId}";
    }

    private void RegisterHandlers()
    {
        if (_handlers.Count != 0)
        {
            return;
        }

        _handlers[CoreGameEvents.ScoreUpdated] = HandleScoreEvent;
        _handlers[CoreGameEvents.ScoreChanged] = HandleScoreEvent;

        _handlers[CoreGameEvents.HealthUpdated] = HandleHealthEvent;
        _handlers[CoreGameEvents.PlayerHealthChanged] = HandleHealthEvent;

        _handlers[SanguoGameTurnStarted.EventType] = HandleTurnEvent;
        _handlers[SanguoGameTurnAdvanced.EventType] = HandleTurnEvent;

        _handlers[SanguoPlayerStateChanged.EventType] = HandlePlayerStateChangedEvent;
        _handlers[SanguoDiceRolled.EventType] = HandleDiceRolledEvent;
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
        string active = "";
        int year = 0;
        int month = 0;
        int day = 0;

        if (root.TryGetProperty("ActivePlayerId", out var ap)) active = ap.GetString() ?? "";
        if (root.TryGetProperty("Year", out var y)) year = y.GetInt32();
        if (root.TryGetProperty("Month", out var m)) month = m.GetInt32();
        if (root.TryGetProperty("Day", out var d)) day = d.GetInt32();

        _activePlayerId = string.IsNullOrWhiteSpace(active) ? null : active;
        _activePlayer.Text = $"Player: {active}";
        _date.Text = $"Date: {year:D4}-{month:D2}-{day:D2}";
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

    public void SetScore(int v) => _score.Text = $"Score: {v}";
    public void SetHealth(int v) => _health.Text = $"HP: {v}";
}
