using Godot;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Ports;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;
using Game.Core.Services;
using Game.Godot.Adapters;
using Game.Godot.Autoloads;
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
    private const string UiTileActionSelected = "ui.sanguo.tile.action.selected";
    private const string AiAutoAdvanceCausationId = "runtime.ai.auto.advance";

    [Export(PropertyHint.Range, "0,30,0.1,or_greater")]
    public double AiAutoAdvanceDelaySeconds { get; set; } = 5.0;

    [Export(PropertyHint.Range, "0,30,0.1,or_greater")]
    public double AiAutoAdvanceDelaySecondsWhenSkip { get; set; } = 5.0;

    [Export]
    public NodePath BoardViewPath { get; set; } = new NodePath("../SanguoBoardView");

    private EventBusAdapter? _bus;
    private SanguoTurnManager? _turnManager;
    private bool _started;
    private bool _advanceQueued;
    private string? _activePlayerId;
    private bool _aiAutoAdvanceRequested;
    private double _aiAutoAdvanceDelaySec = 5.0;

    private SanguoMapDefinition? _map;
    private readonly Dictionary<int, string[]> _actionsByIndex = new();
    private bool _awaitingHumanTileAction;
    private string _awaitingHumanActionCorrelationId = string.Empty;
    private string _lastHumanMoveCorrelationId = string.Empty;
    private int _lastHumanMoveToIndex;

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
            _awaitingHumanTileAction = false;
            _awaitingHumanActionCorrelationId = string.Empty;
            _lastHumanMoveCorrelationId = string.Empty;
            return;
        }

        if (type == SanguoGameTurnStarted.EventType)
        {
            _activePlayerId = SanguoGlueJson.TryExtractActivePlayerId(dataJson);
            return;
        }

        if (type == SanguoTokenMoved.EventType)
        {
            var pid = SanguoGlueJson.TryExtractPlayerId(dataJson);
            if (!SanguoGlueJson.IsAiPlayerId(pid) && !string.IsNullOrWhiteSpace(pid))
            {
                _lastHumanMoveCorrelationId = SanguoGlueJson.TryExtractCorrelationId(dataJson) ?? string.Empty;
                _lastHumanMoveToIndex = SanguoGlueJson.TryExtractIntProperty(dataJson, "ToIndex") ?? 0;
            }
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

        if (type == UiTileActionSelected)
        {
            if (!_started || _turnManager == null)
            {
                return;
            }

            if (!_awaitingHumanTileAction)
            {
                return;
            }

            var corr = SanguoGlueJson.TryExtractCorrelationId(dataJson) ?? string.Empty;
            if (string.IsNullOrWhiteSpace(corr) || !string.Equals(corr, _awaitingHumanActionCorrelationId, StringComparison.Ordinal))
            {
                return;
            }

            var action = SanguoGlueJson.TryExtractAction(dataJson) ?? string.Empty;
            _advanceQueued = true;
            CallDeferred(nameof(AdvanceAfterHumanTileActionDeferred), corr, action);
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

        var loader = ResolveResourceLoader();
        if (loader == null)
        {
            GD.PushWarning("SanguoGameLoopController: ResourceLoaderPort not found; cannot load map config.");
            return;
        }

        if (!SanguoMapConfigLoader.TryLoadMap(loader, correlationId, out var map, out var mapSourcePath, out var mapError))
        {
            GD.PushWarning($"SanguoGameLoopController: map config load failed (source='{mapSourcePath}', error='{mapError}').");
            return;
        }

        _map = map;
        LoadMapActions(map);

        var boardView = GetNodeOrNull<SanguoBoardView>(BoardViewPath);
        boardView?.ApplyMapDefinition(map);

        var economyRules = SanguoEconomyRules.Default;
        var players = new[]
        {
            new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: economyRules),
            new SanguoPlayer(playerId: "ai-1", money: 300m, positionIndex: 0, economyRules: economyRules),
        };

        var citiesById = BuildCitiesByIdFromMap(map);

        var boardState = new SanguoBoardState(players: players, citiesById: citiesById);
        var treasury = new SanguoTreasury();
        var economy = new SanguoEconomyManager(_bus);

        _turnManager = new SanguoTurnManager(
            bus: _bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            totalPositionsHint: map.TileCount);

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

    private IResourceLoader? ResolveResourceLoader()
    {
        try
        {
            var root = GetNodeOrNull<Node>("/root/CompositionRoot");
            if (root is CompositionRoot cr && cr.ResourceLoader != null)
            {
                return cr.ResourceLoader;
            }
        }
        catch
        {
        }

        var port = GetNodeOrNull<ResourceLoaderAdapter>("/root/CompositionRoot/ResourceLoaderPort");
        if (port != null)
        {
            return port;
        }

        // Fallback for minimal scenes/tests where CompositionRoot is not available.
        return new ResourceLoaderAdapter();
    }

    private static Dictionary<string, City> BuildCitiesByIdFromMap(SanguoMapDefinition map)
    {
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal);
        foreach (var tile in map.Tiles)
        {
            var tileType = (tile.TileType ?? string.Empty).Trim();
            if (!string.Equals(tileType, SanguoTileDefinition.TileTypeCity, StringComparison.OrdinalIgnoreCase))
                continue;

            citiesById[tile.TileId] = new City(
                id: tile.TileId,
                name: tile.Name,
                regionId: tile.StateId,
                basePrice: MoneyValue.FromDecimal(tile.PurchasePrice),
                baseToll: MoneyValue.FromDecimal(tile.TollPrice),
                positionIndex: tile.PositionIndex);
        }

        return citiesById;
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
            if (ShouldWaitForHumanTileAction(correlationId))
            {
                _awaitingHumanTileAction = true;
                _awaitingHumanActionCorrelationId = correlationId;
                return;
            }

            await _turnManager.AdvanceTurnAsync(correlationId: correlationId, causationId: UiHudDiceRoll);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SanguoGameLoopController: failed to advance turn: {ex.Message}");
        }
        finally
        {
            if (!_awaitingHumanTileAction)
            {
                _advanceQueued = false;
            }
        }

        TryQueueAiAutoAdvanceIfNeeded();
    }

    private bool ShouldWaitForHumanTileAction(string correlationId)
    {
        if (_map == null || _actionsByIndex.Count == 0)
        {
            return false;
        }

        if (string.IsNullOrWhiteSpace(correlationId))
        {
            return false;
        }

        if (!string.Equals(_lastHumanMoveCorrelationId, correlationId, StringComparison.Ordinal))
        {
            return false;
        }

        if (!_actionsByIndex.TryGetValue(_lastHumanMoveToIndex, out var actions))
        {
            return false;
        }

        return actions.Length > 0;
    }

    private async void AdvanceAfterHumanTileActionDeferred(string correlationId, string action)
    {
        try
        {
            if (!_started || _turnManager == null)
            {
                return;
            }

            await _turnManager.ExecuteHumanTileActionAsync(action: action, correlationId: correlationId, causationId: UiTileActionSelected);
            await _turnManager.AdvanceTurnAsync(correlationId: correlationId, causationId: UiTileActionSelected);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SanguoGameLoopController: failed to apply tile action: {ex.Message}");
        }
        finally
        {
            _awaitingHumanTileAction = false;
            _awaitingHumanActionCorrelationId = string.Empty;
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

    private void LoadMapActions(SanguoMapDefinition map)
    {
        _actionsByIndex.Clear();
        foreach (var tile in map.Tiles)
        {
            if (tile.Actions is null)
            {
                _actionsByIndex[tile.PositionIndex] = Array.Empty<string>();
                continue;
            }

            var list = new List<string>();
            foreach (var a in tile.Actions)
            {
                var v = (a ?? string.Empty).Trim();
                if (!string.IsNullOrWhiteSpace(v))
                {
                    list.Add(v);
                }
            }

            _actionsByIndex[tile.PositionIndex] = list.ToArray();
        }
    }

}
