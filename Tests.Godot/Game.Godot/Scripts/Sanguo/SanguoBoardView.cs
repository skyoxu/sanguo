using Godot;
using Game.Core.Contracts.Sanguo;
using Game.Godot.Adapters;
using System.Text.Json;

namespace Game.Godot.Scripts.Sanguo;

public partial class SanguoBoardView : Node2D
{
    private const string TokenVisualNodeName = "__TokenVisual__";

    [Export]
    public NodePath TokenPath { get; set; } = new NodePath("Token");

    [Export]
    public Vector2 Origin { get; set; } = Vector2.Zero;

    [Export(PropertyHint.Range, "0,512,1,or_greater")]
    public float StepPixels { get; set; } = 64f;

    [Export(PropertyHint.Range, "0,10,0.01,or_greater")]
    public double MoveDurationSeconds { get; set; } = 0.25;

    public int LastToIndex { get; private set; }
    public string? LastPlayerId { get; private set; }
    public bool LastMoveAnimated { get; private set; }

    private Tween? _moveTween;

    public override void _Ready()
    {
        var token = ResolveToken();
        if (token != null)
        {
            EnsureTokenHasVisual(token);
        }

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

        var token = ResolveToken();
        if (token == null)
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

            var target = Origin + new Vector2(LastToIndex * StepPixels, 0f);
            MoveTokenTo(token, target);
        }
        catch
        {
            // View-only: ignore parse failures (core validation happens in Game.Core).
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
