using Godot;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services;
using Game.Godot.Adapters;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

public partial class HUD : Control
{
    private const int MaxEventJsonChars = 64 * 1024;
    private static readonly JsonDocumentOptions JsonOptions = new() { MaxDepth = 32 };
    private const string UiHudDiceRollEventType = "ui.hud.dice.roll";
    private const string MoneyCapAuditAction = "SANGUO_MONEY_CAPPED";

    private Label _score = default!;
    private Label _health = default!;

    private Label _activePlayer = default!;
    private Label _date = default!;
    private Label _money = default!;
    private Button _diceButton = default!;

    private string? _activePlayerId;
    private EventBusAdapter? _bus;
    private SanguoDiceService? _diceService;
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

        _diceService = new SanguoDiceService(_bus);

        var callable = new Callable(this, nameof(OnDomainEventEmitted));
        TryConnectBus(callable);
    }

    public override void _ExitTree()
    {
        _diceButton.Pressed -= OnDicePressed;

        if (_bus == null)
        {
            return;
        }

        var callable = new Callable(this, nameof(OnDomainEventEmitted));
        TryDisconnectBus(callable);

        _bus = null;
        _diceService = null;
    }

    private void OnDicePressed()
    {
        if (_bus == null)
        {
            GD.PushWarning("HUD: EventBus not found; cannot publish ui.hud.dice.roll");
            return;
        }

        var playerId = _activePlayerId ?? "";
        if (string.IsNullOrWhiteSpace(playerId))
        {
            GD.PushWarning("HUD: ActivePlayerId is not known; publishing ui.hud.dice.roll without PlayerId");
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
        _handlers[UiHudDiceRollEventType] = HandleHudDiceRollEvent;
        _handlers[SanguoCityTollPaid.EventType] = HandleCityTollPaidEvent;
    }

    private void HandleHudDiceRollEvent(JsonElement root)
    {
        if (_diceService == null)
        {
            return;
        }

        string gameId = "g1";
        if (root.TryGetProperty("GameId", out var gid) && gid.ValueKind == JsonValueKind.String)
        {
            var v = gid.GetString();
            if (!string.IsNullOrWhiteSpace(v)) gameId = v;
        }

        string playerId = _activePlayerId ?? "";
        if (root.TryGetProperty("PlayerId", out var pid) && pid.ValueKind == JsonValueKind.String)
        {
            var v = pid.GetString();
            if (!string.IsNullOrWhiteSpace(v)) playerId = v;
        }

        if (string.IsNullOrWhiteSpace(playerId))
        {
            return;
        }

        string correlationId = Guid.NewGuid().ToString("N");
        if (root.TryGetProperty("CorrelationId", out var corr) && corr.ValueKind == JsonValueKind.String)
        {
            var v = corr.GetString();
            if (!string.IsNullOrWhiteSpace(v)) correlationId = v;
        }

        string? causationId = UiHudDiceRollEventType;
        if (root.TryGetProperty("CausationId", out var cause) && cause.ValueKind == JsonValueKind.String)
        {
            var v = cause.GetString();
            if (!string.IsNullOrWhiteSpace(v)) causationId = v;
        }

        _ = _diceService.RollD6(gameId: gameId, playerId: playerId, correlationId: correlationId, causationId: causationId);
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
        try
        {
            var dir = ProjectSettings.GlobalizePath("user://logs/security");
            Directory.CreateDirectory(dir);
            var path = Path.Combine(dir, "security-audit.jsonl");

            var record = new
            {
                ts = DateTimeOffset.UtcNow.ToString("O"),
                action,
                reason,
                target,
                caller,
            };

            File.AppendAllText(path, JsonSerializer.Serialize(record) + System.Environment.NewLine);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"HUD: security audit write failed: {ex.Message}");
        }
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
