using Godot;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;
using Game.Core.Services;
using Game.Godot.Adapters;
using System;
using System.Collections.Generic;
using System.Text.Json;

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
    private const int MaxEventJsonChars = 64 * 1024;
    private static readonly JsonDocumentOptions JsonOptions = new() { MaxDepth = 32 };

    private const string UiMenuStart = "ui.menu.start";
    private const string UiHudDiceRoll = "ui.hud.dice.roll";

    private EventBusAdapter? _bus;
    private SanguoTurnManager? _turnManager;
    private bool _started;
    private bool _advanceQueued;
    private string? _activePlayerId;

    public override void _Ready()
    {
        _bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (_bus == null)
        {
            GD.PushWarning("SanguoGameLoopController: EventBus not found at /root/EventBus");
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
        if (_bus != null)
        {
            var callable = new Callable(this, nameof(OnDomainEventEmitted));
            if (_bus.IsConnected(EventBusAdapter.SignalName.DomainEventEmitted, callable))
            {
                _bus.Disconnect(EventBusAdapter.SignalName.DomainEventEmitted, callable);
            }
        }

        _bus = null;
        _turnManager = null;
        _started = false;
        _advanceQueued = false;
        _activePlayerId = null;
    }

    private void OnDomainEventEmitted(string type, string source, string dataJson, string id, string specVersion, string dataContentType, string timestampIso)
    {
        if (type == SanguoGameTurnStarted.EventType)
        {
            _activePlayerId = TryExtractActivePlayerId(dataJson);
            return;
        }

        if (type == UiMenuStart)
        {
            if (_started)
            {
                return;
            }

            var correlationId = Guid.NewGuid().ToString("N");
            CallDeferred(nameof(StartGameDeferred), correlationId);
            return;
        }

        if (type == UiHudDiceRoll)
        {
            if (!_started || _turnManager == null)
            {
                return;
            }

            if (_advanceQueued)
            {
                return;
            }

            var playerId = TryExtractPlayerId(dataJson);
            if (!string.IsNullOrWhiteSpace(_activePlayerId) && !string.IsNullOrWhiteSpace(playerId) && !string.Equals(_activePlayerId, playerId, StringComparison.Ordinal))
            {
                return;
            }

            if (IsAiPlayerId(_activePlayerId) || IsAiPlayerId(playerId))
            {
                return;
            }

            var correlationId = TryExtractCorrelationId(dataJson) ?? Guid.NewGuid().ToString("N");
            _advanceQueued = true;
            CallDeferred(nameof(AdvanceTurnDeferred), correlationId);
        }
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

        var economyRules = SanguoEconomyRules.Default;
        var players = new[]
        {
            new SanguoPlayer(playerId: "p1", money: 100m, positionIndex: 0, economyRules: economyRules),
            new SanguoPlayer(playerId: "ai-1", money: 100m, positionIndex: 0, economyRules: economyRules),
        };

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City(
                id: "c1",
                name: "City 1",
                regionId: "r1",
                basePrice: MoneyValue.FromDecimal(100m),
                baseToll: MoneyValue.FromDecimal(10m),
                positionIndex: 2),
            ["c2"] = new City(
                id: "c2",
                name: "City 2",
                regionId: "r1",
                basePrice: MoneyValue.FromDecimal(100m),
                baseToll: MoneyValue.FromDecimal(10m),
                positionIndex: 4),
            ["c3"] = new City(
                id: "c3",
                name: "City 3",
                regionId: "r2",
                basePrice: MoneyValue.FromDecimal(100m),
                baseToll: MoneyValue.FromDecimal(10m),
                positionIndex: 6),
        };

        var boardState = new SanguoBoardState(players: players, citiesById: citiesById);
        var treasury = new SanguoTreasury();
        var economy = new SanguoEconomyManager(_bus);

        _turnManager = new SanguoTurnManager(
            bus: _bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            totalPositionsHint: 10);

        try
        {
            await _turnManager.StartNewGameAsync(
                gameId: "g1",
                playerOrder: new[] { "p1", "ai-1" },
                year: 3,
                month: 2,
                day: 1,
                correlationId: correlationId,
                causationId: UiMenuStart);
            _started = true;
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SanguoGameLoopController: failed to start game: {ex.Message}");
            _turnManager = null;
            _started = false;
        }
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
            await _turnManager.AdvanceTurnAsync(correlationId: correlationId, causationId: UiHudDiceRoll);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SanguoGameLoopController: failed to advance turn: {ex.Message}");
        }
        finally
        {
            _advanceQueued = false;
        }
    }

    private static string? TryExtractCorrelationId(string dataJson)
    {
        var json = string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson;
        if (json.Length > MaxEventJsonChars)
        {
            return null;
        }

        try
        {
            using var doc = JsonDocument.Parse(json, JsonOptions);
            if (!doc.RootElement.TryGetProperty("CorrelationId", out var corr) || corr.ValueKind != JsonValueKind.String)
            {
                return null;
            }

            var value = corr.GetString();
            return string.IsNullOrWhiteSpace(value) ? null : value;
        }
        catch
        {
            return null;
        }
    }

    private static string? TryExtractActivePlayerId(string dataJson)
    {
        var json = string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson;
        if (json.Length > MaxEventJsonChars)
        {
            return null;
        }

        try
        {
            using var doc = JsonDocument.Parse(json, JsonOptions);
            if (!doc.RootElement.TryGetProperty("ActivePlayerId", out var pid) || pid.ValueKind != JsonValueKind.String)
            {
                return null;
            }

            var value = pid.GetString();
            return string.IsNullOrWhiteSpace(value) ? null : value;
        }
        catch
        {
            return null;
        }
    }

    private static string? TryExtractPlayerId(string dataJson)
    {
        var json = string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson;
        if (json.Length > MaxEventJsonChars)
        {
            return null;
        }

        try
        {
            using var doc = JsonDocument.Parse(json, JsonOptions);
            if (!doc.RootElement.TryGetProperty("PlayerId", out var pid) || pid.ValueKind != JsonValueKind.String)
            {
                return null;
            }

            var value = pid.GetString();
            return string.IsNullOrWhiteSpace(value) ? null : value;
        }
        catch
        {
            return null;
        }
    }

    private static bool IsAiPlayerId(string? playerId)
    {
        return !string.IsNullOrWhiteSpace(playerId) && playerId.StartsWith("ai-", StringComparison.OrdinalIgnoreCase);
    }

}
