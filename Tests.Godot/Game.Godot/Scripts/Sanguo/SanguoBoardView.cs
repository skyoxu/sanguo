using Godot;
using Game.Core.Contracts.Sanguo;
using Game.Godot.Adapters;
using System.Text.Json;

namespace Game.Godot.Scripts.Sanguo;

public partial class SanguoBoardView : Node2D
{
    [Export]
    public NodePath? TokenPath { get; set; }

    public int LastToIndex { get; private set; }
    public string? LastPlayerId { get; private set; }

    public override void _Ready()
    {
        var bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (bus == null)
        {
            return;
        }

        bus.Connect(EventBusAdapter.SignalName.DomainEventEmitted, new Callable(this, nameof(OnDomainEventEmitted)));
    }

    private void OnDomainEventEmitted(string type, string source, string dataJson, string id, string specVersion, string dataContentType, string timestampIso)
    {
        if (type != SanguoTokenMoved.EventType)
        {
            return;
        }

        try
        {
            using var doc = JsonDocument.Parse(string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson);
            if (doc.RootElement.TryGetProperty("ToIndex", out var toIndex))
            {
                LastToIndex = toIndex.GetInt32();
            }

            if (doc.RootElement.TryGetProperty("PlayerId", out var playerId))
            {
                LastPlayerId = playerId.GetString();
            }
        }
        catch
        {
            // View-only: ignore parse failures (core validation happens in Game.Core).
        }
    }
}

