using Godot;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;
using Game.Core.Services;
using Game.Godot.Adapters;
using System;
using System.Collections.Generic;

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
    private const string UiMenuStart = "ui.menu.start";
    private const string UiHudDiceRoll = "ui.hud.dice.roll";
    private const string AiAutoAdvanceCausationId = "runtime.ai.auto.advance";

    [Export(PropertyHint.Range, "0,30,0.1,or_greater")]
    public double AiAutoAdvanceDelaySeconds { get; set; } = 5.0;

    [Export(PropertyHint.Range, "0,30,0.1,or_greater")]
    public double AiAutoAdvanceDelaySecondsWhenSkip { get; set; } = 5.0;

    private EventBusAdapter? _bus;
    private SanguoTurnManager? _turnManager;
    private bool _started;
    private bool _advanceQueued;
    private string? _activePlayerId;
    private bool _aiAutoAdvanceRequested;
    private double _aiAutoAdvanceDelaySec = 5.0;

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
        if (type == SanguoGameEnded.EventType)
        {
            _started = false;
            _turnManager = null;
            _advanceQueued = false;
            _activePlayerId = null;
            _aiAutoAdvanceRequested = false;
            return;
        }

        if (type == SanguoGameTurnStarted.EventType)
        {
            _activePlayerId = SanguoGlueJson.TryExtractActivePlayerId(dataJson);
            return;
        }

        if (type == SanguoAiDecisionMade.EventType)
        {
            var decisionType = SanguoGlueJson.TryExtractAiDecisionType(dataJson);
            _aiAutoAdvanceRequested = true;
            _aiAutoAdvanceDelaySec = string.Equals(decisionType, "Skip", StringComparison.OrdinalIgnoreCase)
                ? AiAutoAdvanceDelaySecondsWhenSkip
                : AiAutoAdvanceDelaySeconds;

            TryQueueAiAutoAdvanceIfNeeded();
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

            var playerId = SanguoGlueJson.TryExtractPlayerId(dataJson);
            if (!string.IsNullOrWhiteSpace(_activePlayerId) && !string.IsNullOrWhiteSpace(playerId) && !string.Equals(_activePlayerId, playerId, StringComparison.Ordinal))
            {
                return;
            }

            if (SanguoGlueJson.IsAiPlayerId(_activePlayerId) || SanguoGlueJson.IsAiPlayerId(playerId))
            {
                return;
            }

            var correlationId = SanguoGlueJson.TryExtractCorrelationId(dataJson) ?? Guid.NewGuid().ToString("N");
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
            new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: economyRules),
            new SanguoPlayer(playerId: "ai-1", money: 300m, positionIndex: 0, economyRules: economyRules),
        };

        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal);
        // Demo board: make most tiles purchasable to keep the playable loop moving.
        // PositionIndex 0 acts as the start tile (non-city).
        for (var pos = 1; pos <= 9; pos++)
        {
            var cityId = $"c{pos}";
            var regionId = (pos % 2 == 0) ? "r1" : "r2";
            citiesById[cityId] = new City(
                id: cityId,
                name: $"City {pos}",
                regionId: regionId,
                basePrice: MoneyValue.FromDecimal(50m),
                baseToll: MoneyValue.FromDecimal(20m),
                positionIndex: pos);
        }

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
            TryQueueAiAutoAdvanceIfNeeded();
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

        TryQueueAiAutoAdvanceIfNeeded();
    }

    private void TryQueueAiAutoAdvanceIfNeeded()
    {
        if (!_started || _turnManager == null)
            return;

        if (_advanceQueued)
            return;

        if (!SanguoGlueJson.IsAiPlayerId(_activePlayerId))
            return;

        if (!_aiAutoAdvanceRequested)
            return;

        _advanceQueued = true;
        _aiAutoAdvanceRequested = false;
        var correlationId = Guid.NewGuid().ToString("N");
        CallDeferred(nameof(AdvanceAiTurnDeferred), correlationId, _aiAutoAdvanceDelaySec);
    }

    private async void AdvanceAiTurnDeferred(string correlationId, double delaySec)
    {
        try
        {
            if (!_started || _turnManager == null)
                return;

        if (!SanguoGlueJson.IsAiPlayerId(_activePlayerId))
            return;

            // Give the board view time to animate AI moves (if any) before the next turn starts.
            var timer = GetTree().CreateTimer(delaySec <= 0 ? AiAutoAdvanceDelaySeconds : delaySec);
            await ToSignal(timer, SceneTreeTimer.SignalName.Timeout);

            await _turnManager.AdvanceTurnAsync(correlationId: correlationId, causationId: AiAutoAdvanceCausationId);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SanguoGameLoopController: failed to auto-advance AI turn: {ex.Message}");
        }
        finally
        {
            _advanceQueued = false;
        }

        // In case multiple AIs exist, keep advancing until a non-AI player becomes active.
        TryQueueAiAutoAdvanceIfNeeded();
    }

}
