using Godot;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Godot.Adapters;
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

public partial class HUD : Control
{
    private Label _score = default!;
    private Label _health = default!;

    private Label _activePlayer = default!;
    private Label _date = default!;
    private Label _money = default!;
    private Button _diceButton = default!;

    private string? _activePlayerId;

    public override void _Ready()
    {
        _score = GetNode<Label>("TopBar/HBox/ScoreLabel");
        _health = GetNode<Label>("TopBar/HBox/HealthLabel");

        _activePlayer = GetNode<Label>("TopBar/HBox/ActivePlayerLabel");
        _date = GetNode<Label>("TopBar/HBox/DateLabel");
        _money = GetNode<Label>("TopBar/HBox/MoneyLabel");
        _diceButton = GetNode<Button>("TopBar/HBox/DiceButton");
        _diceButton.Pressed += OnDicePressed;

        var bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (bus != null)
        {
            bus.Connect(EventBusAdapter.SignalName.DomainEventEmitted, new Callable(this, nameof(OnDomainEventEmitted)));
        }
    }

    private void OnDicePressed()
    {
        var bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (bus == null)
        {
            return;
        }

        bus.PublishSimple("ui.hud.dice.roll", nameof(HUD), "{}");
    }

    private void OnDomainEventEmitted(string type, string source, string dataJson, string id, string specVersion, string dataContentType, string timestampIso)
    {
        if (type == CoreGameEvents.ScoreUpdated || type == CoreGameEvents.ScoreChanged)
        {
            try
            {
                var doc = JsonDocument.Parse(dataJson);
                int v = 0;
                if (doc.RootElement.TryGetProperty("value", out var val)) v = val.GetInt32();
                else if (doc.RootElement.TryGetProperty("score", out var sc)) v = sc.GetInt32();
                _score.Text = $"Score: {v}";
            }
            catch (System.Exception ex)
            {
                GD.PushWarning($"HUD failed to parse score event '{type}': {ex.Message}");
            }
        }
        else if (type == CoreGameEvents.HealthUpdated || type == CoreGameEvents.PlayerHealthChanged)
        {
            try
            {
                var doc = JsonDocument.Parse(dataJson);
                int v = 0;
                if (doc.RootElement.TryGetProperty("value", out var val)) v = val.GetInt32();
                else if (doc.RootElement.TryGetProperty("health", out var hp)) v = hp.GetInt32();
                _health.Text = $"HP: {v}";
            }
            catch (System.Exception ex)
            {
                GD.PushWarning($"HUD failed to parse health event '{type}': {ex.Message}");
            }
        }
        else if (type == Game.Core.Contracts.Sanguo.SanguoGameTurnStarted.EventType || type == Game.Core.Contracts.Sanguo.SanguoGameTurnAdvanced.EventType)
        {
            try
            {
                var doc = JsonDocument.Parse(dataJson);
                string active = "";
                int year = 0;
                int month = 0;
                int day = 0;

                if (doc.RootElement.TryGetProperty("ActivePlayerId", out var ap)) active = ap.GetString() ?? "";
                if (doc.RootElement.TryGetProperty("Year", out var y)) year = y.GetInt32();
                if (doc.RootElement.TryGetProperty("Month", out var m)) month = m.GetInt32();
                if (doc.RootElement.TryGetProperty("Day", out var d)) day = d.GetInt32();

                _activePlayerId = string.IsNullOrWhiteSpace(active) ? null : active;
                _activePlayer.Text = $"Player: {active}";
                _date.Text = $"Date: {year:D4}-{month:D2}-{day:D2}";
            }
            catch (System.Exception ex)
            {
                GD.PushWarning($"HUD failed to parse turn event '{type}': {ex.Message}");
            }
        }
        else if (type == Game.Core.Contracts.Sanguo.SanguoPlayerStateChanged.EventType)
        {
            try
            {
                var doc = JsonDocument.Parse(dataJson);
                if (!doc.RootElement.TryGetProperty("PlayerId", out var pidEl))
                {
                    return;
                }

                var pid = pidEl.GetString() ?? "";
                if (string.IsNullOrWhiteSpace(pid) || _activePlayerId == null || pid != _activePlayerId)
                {
                    return;
                }

                if (!doc.RootElement.TryGetProperty("Money", out var moneyEl))
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
            catch (System.Exception ex)
            {
                GD.PushWarning($"HUD failed to parse player event '{type}': {ex.Message}");
            }
        }
        else if (type == SanguoDiceRolled.EventType)
        {
            try
            {
                var doc = JsonDocument.Parse(dataJson);

                string pid = "";
                if (doc.RootElement.TryGetProperty("PlayerId", out var pidEl))
                {
                    pid = pidEl.GetString() ?? "";
                }

                if (!string.IsNullOrWhiteSpace(pid) && _activePlayerId != null && pid != _activePlayerId)
                {
                    return;
                }

                int value = 0;
                if (doc.RootElement.TryGetProperty("Value", out var v))
                {
                    value = v.GetInt32();
                }
                else if (doc.RootElement.TryGetProperty("value", out var vv))
                {
                    value = vv.GetInt32();
                }

                _diceButton.Text = $"Dice: {value}";
            }
            catch (System.Exception ex)
            {
                GD.PushWarning($"HUD failed to parse dice event '{type}': {ex.Message}");
            }
        }
    }

    public void SetScore(int v) => _score.Text = $"Score: {v}";
    public void SetHealth(int v) => _health.Text = $"HP: {v}";
}
