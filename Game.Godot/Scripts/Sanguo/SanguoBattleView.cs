using System;
using System.Text.Json;
using Godot;
using Game.Godot.Adapters;

namespace Game.Godot.Scripts.Sanguo;

public sealed partial class SanguoBattleView : Control
{
    private const string CombatStarted = "core.sanguo.combat.started";
    private const string CombatEnded = "core.sanguo.combat.ended";
    private static readonly JsonDocumentOptions JsonOptions = new() { MaxDepth = 32 };

    private Label? _title;
    private Label? _details;
    private Button? _continueButton;
    private EventBusAdapter? _bus;
    private Callable _busCallable;

    private string _correlationId = string.Empty;
    private string _encounterId = string.Empty;

    public override void _Ready()
    {
        Visible = false;

        _title = GetNodeOrNull<Label>("Panel/VBox/Title");
        _details = GetNodeOrNull<Label>("Panel/VBox/Details");
        _continueButton = GetNodeOrNull<Button>("Panel/VBox/ContinueButton");
        if (_continueButton != null)
        {
            _continueButton.Pressed += OnContinuePressed;
            _continueButton.Disabled = true;
        }

        _bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (_bus == null)
        {
            GD.PushWarning("SanguoBattleView: EventBus not found at /root/EventBus");
            return;
        }

        _busCallable = new Callable(this, nameof(OnDomainEventEmitted));
        if (!_bus.IsConnected(EventBusAdapter.SignalName.DomainEventEmitted, _busCallable))
        {
            _bus.Connect(EventBusAdapter.SignalName.DomainEventEmitted, _busCallable);
        }
    }

    public override void _ExitTree()
    {
        if (_bus == null)
        {
            return;
        }

        if (_bus.IsConnected(EventBusAdapter.SignalName.DomainEventEmitted, _busCallable))
        {
            _bus.Disconnect(EventBusAdapter.SignalName.DomainEventEmitted, _busCallable);
        }
    }

    private void OnContinuePressed()
    {
        Visible = false;
        _correlationId = string.Empty;
        _encounterId = string.Empty;
        if (_continueButton != null)
        {
            _continueButton.Disabled = true;
        }
    }

    private void OnDomainEventEmitted(
        string type,
        string _source,
        string dataJson,
        string _id,
        string _specVersion,
        string _dataContentType,
        string _timestampIso)
    {
        if (string.Equals(type, CombatStarted, StringComparison.Ordinal))
        {
            HandleCombatStarted(dataJson);
            return;
        }

        if (string.Equals(type, CombatEnded, StringComparison.Ordinal))
        {
            HandleCombatEnded(dataJson);
        }
    }

    private void HandleCombatStarted(string dataJson)
    {
        if (!TryParseCommon(dataJson, out var playerId, out var correlationId, out var encounterId))
        {
            return;
        }

        if (IsAiPlayerId(playerId))
        {
            return;
        }

        Visible = true;
        _correlationId = correlationId;
        _encounterId = encounterId;

        if (_title != null)
        {
            _title.Text = "Combat";
        }

        if (_details != null)
        {
            _details.Text = $"Started (encounter={encounterId})";
        }

        if (_continueButton != null)
        {
            _continueButton.Disabled = true;
        }
    }

    private void HandleCombatEnded(string dataJson)
    {
        if (!TryParseCommon(dataJson, out var playerId, out var correlationId, out var encounterId))
        {
            return;
        }

        if (IsAiPlayerId(playerId))
        {
            return;
        }

        if (!string.IsNullOrWhiteSpace(_correlationId) && !string.Equals(_correlationId, correlationId, StringComparison.Ordinal))
        {
            return;
        }

        Visible = true;
        _correlationId = correlationId;
        _encounterId = encounterId;

        var outcome = "unknown";
        decimal moneyDelta = 0m;

        try
        {
            using var doc = JsonDocument.Parse(string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson, JsonOptions);
            if (doc.RootElement.TryGetProperty("Result", out var result))
            {
                if (result.TryGetProperty("Outcome", out var o) && o.ValueKind == JsonValueKind.String)
                {
                    outcome = o.GetString() ?? "unknown";
                }

                if (result.TryGetProperty("MoneyDelta", out var md))
                {
                    if (md.ValueKind == JsonValueKind.Number && md.TryGetDecimal(out var v))
                    {
                        moneyDelta = v;
                    }
                }
            }
        }
        catch
        {
        }

        if (_details != null)
        {
            _details.Text = $"Result: {outcome} (money_delta={moneyDelta})";
        }

        if (_continueButton != null)
        {
            _continueButton.Disabled = false;
        }
    }

    private static bool TryParseCommon(string dataJson, out string playerId, out string correlationId, out string encounterId)
    {
        playerId = string.Empty;
        correlationId = string.Empty;
        encounterId = string.Empty;

        try
        {
            using var doc = JsonDocument.Parse(string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson, JsonOptions);
            var root = doc.RootElement;

            if (root.TryGetProperty("PlayerId", out var p) && p.ValueKind == JsonValueKind.String)
            {
                playerId = p.GetString() ?? string.Empty;
            }

            if (root.TryGetProperty("CorrelationId", out var c) && c.ValueKind == JsonValueKind.String)
            {
                correlationId = c.GetString() ?? string.Empty;
            }

            if (root.TryGetProperty("EncounterId", out var e) && e.ValueKind == JsonValueKind.String)
            {
                encounterId = e.GetString() ?? string.Empty;
            }

            return !string.IsNullOrWhiteSpace(playerId) && !string.IsNullOrWhiteSpace(correlationId) && !string.IsNullOrWhiteSpace(encounterId);
        }
        catch
        {
            return false;
        }
    }

    private static bool IsAiPlayerId(string playerId)
        => (playerId ?? string.Empty).Trim().StartsWith("ai-", StringComparison.OrdinalIgnoreCase);
}

