using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;
using Godot;
using Game.Core.Contracts.Sanguo;
using Game.Godot.Adapters;

namespace Game.Godot.Scripts.Sanguo;

public sealed partial class SanguoBattleView : Control
{
    private const string CombatStarted = SanguoCombatStarted.EventType;
    private const string CombatEnded = SanguoCombatEnded.EventType;
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
            var summary = BuildCombatDetailsSummary(
                dataJson: dataJson,
                defaultHeader: $"Started (encounter={encounterId})",
                defaultOutcomeLine: string.Empty,
                includeOutcome: false);
            _details.Text = summary;
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
            var summary = BuildCombatDetailsSummary(
                dataJson: dataJson,
                defaultHeader: $"Result: {outcome} (money_delta={moneyDelta})",
                defaultOutcomeLine: $"Result: {outcome} (money_delta={moneyDelta})",
                includeOutcome: true);
            _details.Text = summary;
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

    private static string BuildCombatDetailsSummary(
        string dataJson,
        string defaultHeader,
        string defaultOutcomeLine,
        bool includeOutcome)
    {
        try
        {
            using var doc = JsonDocument.Parse(string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson, JsonOptions);
            var root = doc.RootElement;
            var lines = new List<string>();

            if (!string.IsNullOrWhiteSpace(defaultHeader))
            {
                lines.Add(defaultHeader);
            }

            if (includeOutcome && !string.IsNullOrWhiteSpace(defaultOutcomeLine))
            {
                lines.Add(defaultOutcomeLine);
            }

            var playerSnapshot = TryGetSnapshot(root, "PlayerSnapshot");
            var enemySnapshot = TryGetSnapshot(root, "EnemySnapshot");
            if (playerSnapshot.HasValue)
            {
                lines.Add(FormatSnapshot("Player", playerSnapshot.Value));
            }
            else
            {
                lines.Add("Player: unavailable");
            }

            if (enemySnapshot.HasValue)
            {
                lines.Add(FormatSnapshot("Enemy", enemySnapshot.Value));
            }
            else
            {
                lines.Add("Enemy: unavailable");
            }

            return string.Join("\n", lines);
        }
        catch
        {
            return defaultHeader;
        }
    }

    private static JsonElement? TryGetSnapshot(JsonElement root, string propertyName)
    {
        if (root.TryGetProperty(propertyName, out var snapshot) && snapshot.ValueKind == JsonValueKind.Object)
        {
            return snapshot;
        }

        if (root.TryGetProperty("Result", out var result)
            && result.ValueKind == JsonValueKind.Object
            && result.TryGetProperty(propertyName, out var nested)
            && nested.ValueKind == JsonValueKind.Object)
        {
            return nested;
        }

        return null;
    }

    private static string FormatSnapshot(string side, JsonElement snapshot)
    {
        if (!snapshot.TryGetProperty("MainUnit", out var unit) || unit.ValueKind != JsonValueKind.Object)
        {
            return $"{side}: unavailable";
        }

        var name = BuildDisplayNameWithSummons(unit, snapshot);
        var modelPlaceholder = TryGetString(unit, "UnitId", "unavailable");
        var role = TryGetString(unit, "UnitRole", "unknown");
        var stats = TryFormatStats(unit);
        var skills = TryFormatStringList(unit, "SkillIds");
        var passives = TryFormatStringList(unit, "PassiveSkillIds");
        var relics = TryFormatStringList(unit, "RelicIds");
        var buffs = TryFormatStringList(unit, "BuffIds");
        var debuffs = TryFormatStringList(unit, "DebuffIds");

        var sb = new StringBuilder();
        sb.Append(side).Append(": ").Append(name).Append(" [").Append(role).Append("]");
        sb.Append(" | Model=").Append(modelPlaceholder);
        sb.Append(" | Runtime=").Append(stats);
        sb.Append(" | Skills=").Append(skills);
        sb.Append(" | Passives=").Append(passives);
        sb.Append(" | Relics=").Append(relics);
        sb.Append(" | Buffs=").Append(buffs);
        sb.Append(" | Debuffs=").Append(debuffs);
        return sb.ToString();
    }

    private static string BuildDisplayNameWithSummons(JsonElement mainUnit, JsonElement snapshot)
    {
        var names = new List<string> { TryGetString(mainUnit, "DisplayName", "Unknown") };

        if (!snapshot.TryGetProperty("Summons", out var summons) || summons.ValueKind != JsonValueKind.Array)
        {
            return names[0];
        }

        foreach (var summon in summons.EnumerateArray())
        {
            if (summon.ValueKind != JsonValueKind.Object)
            {
                continue;
            }

            var summonName = TryGetString(summon, "DisplayName", string.Empty);
            if (!string.IsNullOrWhiteSpace(summonName))
            {
                names.Add(summonName);
            }
        }

        return string.Join(",", names);
    }

    private static string TryFormatStats(JsonElement unit)
    {
        if (!unit.TryGetProperty("Stats", out var stats) || stats.ValueKind != JsonValueKind.Object)
        {
            return "unavailable";
        }

        var hp = TryGetInt(stats, "CurrentHP");
        var maxHp = TryGetInt(stats, "MaxHP");
        var attack = TryGetInt(stats, "Attack");
        return $"HP {hp}/{maxHp}, ATK {attack}";
    }

    private static string TryFormatStringList(JsonElement unit, string propertyName)
    {
        if (!unit.TryGetProperty(propertyName, out var items) || items.ValueKind != JsonValueKind.Array)
        {
            return "unavailable";
        }

        var values = new List<string>();
        foreach (var item in items.EnumerateArray())
        {
            if (item.ValueKind == JsonValueKind.String)
            {
                var value = item.GetString();
                if (!string.IsNullOrWhiteSpace(value))
                {
                    values.Add(value.Trim());
                }
            }
        }

        if (values.Count == 0)
        {
            return "empty";
        }

        return string.Join(",", values);
    }

    private static string TryGetString(JsonElement obj, string propertyName, string fallback)
    {
        if (obj.TryGetProperty(propertyName, out var value) && value.ValueKind == JsonValueKind.String)
        {
            return value.GetString() ?? fallback;
        }

        return fallback;
    }

    private static int TryGetInt(JsonElement obj, string propertyName)
    {
        if (obj.TryGetProperty(propertyName, out var value) && value.ValueKind == JsonValueKind.Number && value.TryGetInt32(out var parsed))
        {
            return parsed;
        }

        return 0;
    }
}
