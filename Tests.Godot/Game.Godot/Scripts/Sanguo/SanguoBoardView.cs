using Godot;
using Game.Core.Contracts.Sanguo;
using Game.Godot.Adapters;
using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Game.Godot.Scripts.Sanguo;

public partial class SanguoBoardView : Node2D
{
    private const int MaxEventJsonChars = 64 * 1024;
    private static readonly JsonDocumentOptions JsonOptions = new() { MaxDepth = 32 };

    private static readonly Color HumanColor = new(0.9f, 0.2f, 0.2f, 1f);
    private static readonly Color AiColor = new(0.2f, 0.4f, 0.9f, 1f);
    private static readonly Color NeutralColor = new(0.32f, 0.32f, 0.32f, 1f);

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

    [Export]
    public bool UseSquareLayout { get; set; } = true;

    [Export(PropertyHint.Range, "0,128,1,or_greater")]
    public float TokenLaneOffsetPixels { get; set; } = 16f;

    public int LastToIndex { get; private set; }
    public string? LastPlayerId { get; private set; }
    public bool LastMoveAnimated { get; private set; }

    private EventBusAdapter? _bus;
    private readonly SanguoBoardLayout _layout = new();
    private readonly SanguoBoardTileOverlay _overlay;
    private readonly SanguoTokenAnimator _animator;
    private readonly SanguoBoardTokens _tokens;

    private readonly Dictionary<string, Node2D> _tokensByPlayerId = new(StringComparer.Ordinal);
    private readonly Dictionary<string, int> _lastPositionByPlayerId = new(StringComparer.Ordinal);

    public SanguoBoardView()
    {
        _overlay = new SanguoBoardTileOverlay(this);
        _animator = new SanguoTokenAnimator(this);
        _tokens = new SanguoBoardTokens(this, _tokensByPlayerId);
    }

    public override void _Ready()
    {
        var token = _tokens.ResolvePrimary(TokenPath);
        if (token != null)
        {
            SanguoBoardTokens.EnsureTokenHasVisual(token, HumanColor);
            _tokensByPlayerId["p1"] = token;
        }

        var aiToken = _tokens.EnsureExtraToken("ai-1");
        SanguoBoardTokens.EnsureTokenHasVisual(aiToken, AiColor);

        EnsureBoardVisuals();

        _bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (_bus == null)
        {
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
        _animator.KillAll();

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

    private void OnDomainEventEmitted(
        string type,
        string source,
        string dataJson,
        string id,
        string specVersion,
        string dataContentType,
        string timestampIso
    )
    {
        if (type != SanguoTokenMoved.EventType && type != SanguoCityBought.EventType)
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
            var root = doc.RootElement;

            if (type == SanguoCityBought.EventType)
            {
                if (!root.TryGetProperty("BuyerId", out var buyerProp) || buyerProp.ValueKind != JsonValueKind.String)
                {
                    return;
                }

                var buyerId = buyerProp.GetString() ?? string.Empty;
                if (string.IsNullOrWhiteSpace(buyerId))
                {
                    return;
                }

                if (!_lastPositionByPlayerId.TryGetValue(buyerId, out var pos))
                {
                    return;
                }

                EnsureBoardVisuals();
                _overlay.SetOwnerForIndex(_layout, _layout.ClampIndex(pos), buyerId);
                return;
            }

            if (!root.TryGetProperty("ToIndex", out var toIndex) || !toIndex.TryGetInt32(out var parsedToIndex))
            {
                GD.PushWarning($"SanguoBoardView ignored event without valid ToIndex (type='{type}').");
                return;
            }

            if (TotalPositions <= 0)
            {
                SanguoSecurityAuditWriter.TryAppendSecurityAudit(
                    action: "SANGUO_BOARD_TOKEN_MOVE_REJECTED",
                    reason: "total_positions_not_configured",
                    target: $"to_index={parsedToIndex} total_positions={TotalPositions}",
                    caller: "SanguoBoardView.OnDomainEventEmitted",
                    eventType: type,
                    eventSource: source,
                    eventId: id);
                GD.PushWarning($"SanguoBoardView ignored token move because TotalPositions is not configured (TotalPositions={TotalPositions}).");
                return;
            }

            if (parsedToIndex < 0)
            {
                SanguoSecurityAuditWriter.TryAppendSecurityAudit(
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

            if (parsedToIndex >= TotalPositions)
            {
                SanguoSecurityAuditWriter.TryAppendSecurityAudit(
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

            var playerId = "p1";
            if (root.TryGetProperty("PlayerId", out var pid) && pid.ValueKind == JsonValueKind.String)
            {
                var v = pid.GetString();
                if (!string.IsNullOrWhiteSpace(v))
                {
                    playerId = v;
                }
            }

            var token = _tokens.ResolveTokenForPlayerId(playerId, TokenPath, HumanColor, AiColor, NeutralColor);
            if (token == null)
            {
                return;
            }

            EnsureBoardVisuals();

            LastPlayerId = playerId;
            LastToIndex = parsedToIndex;

            var fromIndex = LastToIndex;
            if (root.TryGetProperty("FromIndex", out var fromEl) && fromEl.TryGetInt32(out var parsedFromIndex))
            {
                fromIndex = parsedFromIndex;
            }
            else if (_lastPositionByPlayerId.TryGetValue(playerId, out var previous))
            {
                fromIndex = previous;
            }

            var stepCount = 0;
            if (root.TryGetProperty("Steps", out var stepsEl) && stepsEl.TryGetInt32(out var parsedSteps))
            {
                stepCount = parsedSteps;
            }

            var clampedFrom = ClampIndexToBoard(fromIndex);
            var clampedTo = _layout.ClampIndex(LastToIndex);
            var effectiveSteps = ResolveEffectiveSteps(clampedFrom, clampedTo, stepCount);

            _lastPositionByPlayerId[playerId] = clampedTo;

            if (MoveDurationSeconds <= 0 || effectiveSteps <= 1)
            {
                var target = GetTokenTargetPosition(playerId, clampedTo);
                LastMoveAnimated = _animator.MoveTo(playerId, token, target, MoveDurationSeconds);
                return;
            }

            LastMoveAnimated = _animator.MoveAlongPath(
                playerId,
                token,
                _layout.TotalPositions,
                clampedFrom,
                effectiveSteps,
                MoveDurationSeconds,
                index => GetTokenTargetPosition(playerId, index));
        }
        catch
        {
            // View-only: ignore parse failures (core validation happens in Game.Core).
        }
    }

    private int ClampIndexToBoard(int index) => _layout.ClampIndex(index);

    private int ResolveEffectiveSteps(int fromIndex, int toIndex, int declaredSteps)
    {
        if (TotalPositions <= 0)
        {
            return 1;
        }

        var delta = (toIndex - fromIndex) % TotalPositions;
        if (delta < 0)
        {
            delta += TotalPositions;
        }

        if (declaredSteps > 0 && declaredSteps <= TotalPositions && ((fromIndex + declaredSteps) % TotalPositions) == toIndex)
        {
            return declaredSteps;
        }

        return delta <= 0 ? 1 : delta;
    }

    public Vector2 GetPositionForIndex(int index)
    {
        EnsureBoardVisuals();
        return _layout.GetBasePositionForIndex(index);
    }

    private Vector2 GetTokenTargetPosition(string playerId, int index)
    {
        EnsureBoardVisuals();
        var basePos = _layout.GetBasePositionForIndex(index);
        if (string.IsNullOrWhiteSpace(playerId) || string.Equals(playerId, "p1", StringComparison.Ordinal))
        {
            return basePos;
        }

        return basePos + new Vector2(0f, TokenLaneOffsetPixels);
    }

    private void EnsureBoardVisuals()
    {
        _layout.Configure(TotalPositions, StepPixels, Origin, UseSquareLayout);
        _overlay.EnsureBuilt(_layout);
    }
}
