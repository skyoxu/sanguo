using Godot;
using Game.Core.Contracts.Sanguo;
using Game.Godot.Adapters;
using System;
using System.IO;
using System.Text.Json;

namespace Game.Godot.Scripts.Sanguo;

public partial class SanguoBoardView : Node2D
{
    private const int MaxEventJsonChars = 64 * 1024;
    private static readonly JsonDocumentOptions JsonOptions = new() { MaxDepth = 32 };
    private const string TokenVisualNodeName = "__TokenVisual__";

    [Export]
    public NodePath TokenPath { get; set; } = new NodePath("Token");

    [Export]
    public Vector2 Origin { get; set; } = Vector2.Zero;

    [Export(PropertyHint.Range, "0,512,1,or_greater")]
    public float StepPixels { get; set; } = 64f;

    [Export(PropertyHint.Range, "0,10,0.01,or_greater")]
    public double MoveDurationSeconds { get; set; } = 0.25;

    [Export(PropertyHint.Range, "0,512,1,or_greater")]
    public int TotalPositions { get; set; } = 0;

    public int LastToIndex { get; private set; }
    public string? LastPlayerId { get; private set; }
    public bool LastMoveAnimated { get; private set; }

    private EventBusAdapter? _bus;
    private Tween? _moveTween;

    public override void _Ready()
    {
        var token = ResolveToken();
        if (token != null)
        {
            EnsureTokenHasVisual(token);
        }

        _bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (_bus == null)
        {
            GD.PushWarning("SanguoBoardView: EventBus not found at /root/EventBus");
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
        _moveTween?.Kill();
        _moveTween = null;

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

    private void OnDomainEventEmitted(string type, string source, string dataJson, string id, string specVersion, string dataContentType, string timestampIso)
    {
        if (type != SanguoTokenMoved.EventType)
        {
            return;
        }

        var token = ResolveToken();
        if (token == null)
        {
            return;
        }

        var json = string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson;
        if (json.Length > MaxEventJsonChars)
        {
            GD.PushWarning($"SanguoBoardView ignored over-sized event payload (type='{type}', length={json.Length}).");
            return;
        }

        try
        {
            using var doc = JsonDocument.Parse(json, JsonOptions);
            if (!doc.RootElement.TryGetProperty("ToIndex", out var toIndex) || !toIndex.TryGetInt32(out var parsedToIndex))
            {
                GD.PushWarning($"SanguoBoardView ignored event without valid ToIndex (type='{type}').");
                return;
            }

            if (parsedToIndex < 0)
            {
                TryAppendSecurityAudit(
                    action: "SANGUO_BOARD_TOKEN_MOVE_REJECTED",
                    reason: "to_index_negative",
                    target: $"to_index={parsedToIndex} total_positions={TotalPositions}",
                    caller: "SanguoBoardView.OnDomainEventEmitted",
                    eventType: type,
                    eventSource: source,
                    eventId: id);
                GD.PushWarning($"SanguoBoardView ignored event with out-of-range ToIndex={parsedToIndex} (TotalPositions={TotalPositions}).");
                return;
            }

            if (TotalPositions > 0 && parsedToIndex >= TotalPositions)
            {
                TryAppendSecurityAudit(
                    action: "SANGUO_BOARD_TOKEN_MOVE_REJECTED",
                    reason: "to_index_out_of_range",
                    target: $"to_index={parsedToIndex} total_positions={TotalPositions}",
                    caller: "SanguoBoardView.OnDomainEventEmitted",
                    eventType: type,
                    eventSource: source,
                    eventId: id);
                GD.PushWarning($"SanguoBoardView ignored event with out-of-range ToIndex={parsedToIndex} (TotalPositions={TotalPositions}).");
                return;
            }

            if (doc.RootElement.TryGetProperty("PlayerId", out var playerId))
            {
                LastPlayerId = playerId.GetString();
            }

            LastToIndex = parsedToIndex;
            var target = Origin + new Vector2(LastToIndex * StepPixels, 0f);
            MoveTokenTo(token, target);
        }
        catch
        {
            // View-only: ignore parse failures (core validation happens in Game.Core).
        }
    }

    private static void TryAppendSecurityAudit(
        string action,
        string reason,
        string target,
        string caller,
        string eventType,
        string eventSource,
        string eventId
    )
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
                event_type = eventType,
                event_source = eventSource,
                event_id = eventId,
            };

            File.AppendAllText(path, JsonSerializer.Serialize(record) + System.Environment.NewLine);
        }
        catch
        {
            // Best-effort audit only.
        }
    }

    private Node2D? ResolveToken()
    {
        if (!TokenPath.IsEmpty)
        {
            return GetNodeOrNull<Node2D>(TokenPath);
        }

        return null;
    }

    private void MoveTokenTo(Node2D token, Vector2 targetLocalPosition)
    {
        _moveTween?.Kill();
        _moveTween = null;

        if (MoveDurationSeconds <= 0)
        {
            token.Position = targetLocalPosition;
            LastMoveAnimated = false;
            return;
        }

        LastMoveAnimated = true;
        _moveTween = CreateTween();
        _moveTween.TweenProperty(token, "position", targetLocalPosition, MoveDurationSeconds);
    }

    private static void EnsureTokenHasVisual(Node2D token)
    {
        if (token.GetNodeOrNull<Node2D>(TokenVisualNodeName) != null)
        {
            return;
        }

        foreach (var child in token.GetChildren())
        {
            if (child is CanvasItem)
            {
                return;
            }
        }

        var visual = new Polygon2D
        {
            Name = TokenVisualNodeName,
            Color = new Color(0.9f, 0.2f, 0.2f, 1f),
            Polygon =
                new[]
                {
                    new Vector2(-8, -8),
                    new Vector2(8, -8),
                    new Vector2(8, 8),
                    new Vector2(-8, 8),
                },
        };

        token.AddChild(visual);
    }
}
