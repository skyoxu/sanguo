using Godot;
using Game.Core.Contracts.Sanguo;
using Game.Godot.Adapters;
using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Game.Godot.Scripts.Sanguo;

/// <summary>
/// Listens for <see cref="SanguoDiceRolled"/> and publishes <see cref="SanguoTokenMoved"/> events
/// for UI/scene consumers (e.g. <see cref="SanguoBoardView"/>).
/// </summary>
public partial class SanguoTokenMovePublisher : Node
{
    private const int MaxEventJsonChars = 64 * 1024;
    private static readonly JsonDocumentOptions JsonOptions = new() { MaxDepth = 32 };

    private readonly Dictionary<string, int> _currentIndexByPlayerId = new(StringComparer.Ordinal);

    private EventBusAdapter? _bus;

    public override void _Ready()
    {
        _bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (_bus == null)
        {
            GD.PushWarning("SanguoTokenMovePublisher: EventBus not found at /root/EventBus");
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
        _currentIndexByPlayerId.Clear();
    }

    private void OnDomainEventEmitted(string type, string source, string dataJson, string id, string specVersion, string dataContentType, string timestampIso)
    {
        if (type != SanguoDiceRolled.EventType)
        {
            return;
        }

        if (_bus == null)
        {
            return;
        }

        var json = string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson;
        if (json.Length > MaxEventJsonChars)
        {
            GD.PushWarning($"SanguoTokenMovePublisher ignored over-sized event payload (type='{type}', length={json.Length}).");
            return;
        }

        try
        {
            using var doc = JsonDocument.Parse(json, JsonOptions);

            if (!doc.RootElement.TryGetProperty("PlayerId", out var playerIdEl))
            {
                GD.PushWarning("SanguoTokenMovePublisher ignored dice event without PlayerId.");
                return;
            }

            var playerId = playerIdEl.GetString();
            if (string.IsNullOrWhiteSpace(playerId))
            {
                GD.PushWarning("SanguoTokenMovePublisher ignored dice event with empty PlayerId.");
                return;
            }

            if (!doc.RootElement.TryGetProperty("Value", out var valueEl) || !valueEl.TryGetInt32(out var steps))
            {
                GD.PushWarning("SanguoTokenMovePublisher ignored dice event without valid Value.");
                return;
            }

            if (steps < 0)
            {
                GD.PushWarning($"SanguoTokenMovePublisher ignored dice event with negative Value={steps}.");
                return;
            }

            var boardView = GetParentOrNull<SanguoBoardView>();
            var totalPositions = boardView?.TotalPositions ?? 0;
            if (totalPositions <= 0)
            {
                GD.PushWarning($"SanguoTokenMovePublisher refused to publish token move because TotalPositions is not configured (TotalPositions={totalPositions}).");
                return;
            }

            var fromIndex = _currentIndexByPlayerId.TryGetValue(playerId, out var current) ? current : 0;
            if (fromIndex < 0)
            {
                GD.PushWarning($"SanguoTokenMovePublisher corrected negative FromIndex={fromIndex} for PlayerId='{playerId}'.");
                fromIndex = 0;
            }

            int toIndex;
            bool passedStart;

            if (fromIndex >= totalPositions)
            {
                GD.PushWarning($"SanguoTokenMovePublisher corrected out-of-range FromIndex={fromIndex} (TotalPositions={totalPositions}) for PlayerId='{playerId}'.");
                fromIndex = 0;
            }

            toIndex = (fromIndex + steps) % totalPositions;
            passedStart = fromIndex + steps >= totalPositions;

            if (toIndex < 0 || (totalPositions > 0 && toIndex >= totalPositions))
            {
                GD.PushWarning($"SanguoTokenMovePublisher refused to publish token move (ToIndex={toIndex}, TotalPositions={totalPositions}).");
                return;
            }

            _currentIndexByPlayerId[playerId] = toIndex;

            var payload = JsonSerializer.Serialize(new
            {
                PlayerId = playerId,
                FromIndex = fromIndex,
                ToIndex = toIndex,
                Steps = steps,
                PassedStart = passedStart,
            });

            _bus.PublishSimple(SanguoTokenMoved.EventType, nameof(SanguoTokenMovePublisher), payload);
        }
        catch
        {
            // Publisher: ignore parse failures (input should be validated upstream).
        }
    }
}

