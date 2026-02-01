using Godot;
using Game.Core.Contracts.Sanguo;
using Game.Godot.Adapters;
using Game.Godot.Scripts.Security;
using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Game.Godot.Scripts.Sanguo;

public partial class SanguoBoardView : Node2D
{
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

    [Export]
    public bool EnableMousePan { get; set; } = true;

    [Export]
    public bool EnableWheelScroll { get; set; } = true;

    [Export]
    public NodePath CameraPath { get; set; } = new NodePath("Camera2D");

    [Export]
    public bool EnableCameraInertia { get; set; } = true;

    [Export(PropertyHint.Range, "0,60,0.1,or_greater")]
    public float CameraInertiaSpeed { get; set; } = 8f;

    [Export(PropertyHint.Range, "0,2048,1,or_greater")]
    public float CameraBoundsPadding { get; set; } = 96f;

    [Export]
    public bool AutoCenterOnMapLoad { get; set; } = true;

    [Export(PropertyHint.Range, "0,512,1,or_greater")]
    public float ScrollPixels { get; set; } = 64f;

    [Export(PropertyHint.Range, "0,5,0.01,or_greater")]
    public float DragSpeed { get; set; } = 1f;

    [Export]
    public MouseButton PanButton { get; set; } = MouseButton.Middle;

    [Export]
    public bool EnableHoverHighlight { get; set; } = true;

    [Export]
    public bool EnableHoverTooltip { get; set; } = true;

    [Export(PropertyHint.Range, "0,512,1,or_greater")]
    public float HoverDetectRadiusPixels { get; set; } = 24f;

    [Export]
    public NodePath HoverTooltipPath { get; set; } = new NodePath("HoverTooltip");

    public int LastToIndex { get; private set; }
    public string? LastPlayerId { get; private set; }
    public bool LastMoveAnimated { get; private set; }

    private EventBusAdapter? _bus;
    private Camera2D? _camera;
    private Vector2 _cameraTarget;
    private Rect2 _cameraBounds;
    private bool _cameraBoundsValid;

    private readonly SanguoBoardLayout _layout = new();
    private readonly SanguoBoardTileOverlay _overlay;
    private readonly SanguoTokenAnimator _animator;
    private readonly SanguoBoardTokens _tokens;

    private readonly Dictionary<string, Node2D> _tokensByPlayerId = new(StringComparer.Ordinal);
    private readonly Dictionary<string, int> _lastPositionByPlayerId = new(StringComparer.Ordinal);
    private readonly Dictionary<string, int> _positionIndexByTileId = new(StringComparer.Ordinal);
    private readonly Dictionary<int, string> _tileNameByIndex = new();
    private readonly Dictionary<int, string> _tileTypeByIndex = new();
    private readonly Dictionary<int, string> _tileStateByIndex = new();

    private Label? _hoverTooltip;
    private int _hoverIndex = -1;
    private bool _isPanning;

    public SanguoBoardView()
    {
        _overlay = new SanguoBoardTileOverlay(this);
        _animator = new SanguoTokenAnimator(this);
        _tokens = new SanguoBoardTokens(this, _tokensByPlayerId);
    }

    public override void _Ready()
    {
        ResetBoardTransform();
        var token = _tokens.ResolvePrimary(TokenPath);
        if (token != null)
        {
            SanguoBoardTokens.EnsureTokenHasVisual(token, HumanColor);
            _tokensByPlayerId["p1"] = token;
        }

        var aiToken = _tokens.EnsureExtraToken("ai-1");
        SanguoBoardTokens.EnsureTokenHasVisual(aiToken, AiColor);

        EnsureCamera();
        EnsureBoardVisuals();
        UpdateCameraBounds();
        ClampCameraTarget();

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

    public override void _Process(double delta)
    {
        UpdateCamera(delta);
        UpdateHover();
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        if (!EnableMousePan && !EnableWheelScroll)
        {
            return;
        }

        if (@event is InputEventMouseButton mouseButton)
        {
            if (EnableWheelScroll && mouseButton.Pressed)
            {
                var delta = ResolveWheelDelta(mouseButton);
                if (delta != Vector2.Zero)
                {
                    ApplyPanDelta(delta);
                    GetViewport().SetInputAsHandled();
                    return;
                }
            }

            if (EnableMousePan && mouseButton.ButtonIndex == PanButton)
            {
                _isPanning = mouseButton.Pressed;
                GetViewport().SetInputAsHandled();
            }
        }
        else if (EnableMousePan && _isPanning && @event is InputEventMouseMotion motion)
        {
            ApplyPanDelta(-motion.Relative * DragSpeed);
            GetViewport().SetInputAsHandled();
        }
    }

    public void ApplyMapDefinition(SanguoMapDefinition map)
    {
        if (map is null)
        {
            return;
        }

        TotalPositions = map.TileCount;
        _lastPositionByPlayerId.Clear();
        _positionIndexByTileId.Clear();
        _tileNameByIndex.Clear();
        _tileTypeByIndex.Clear();
        _tileStateByIndex.Clear();

        foreach (var tile in map.Tiles)
        {
            var safeTileType = tile.TileType ?? string.Empty;
            var safeName = tile.Name ?? string.Empty;
            var safeState = tile.StateId ?? string.Empty;
            _overlay.SetTileTypeForIndex(tile.PositionIndex, safeTileType);
            _overlay.SetBaseLabelForIndex(tile.PositionIndex, safeName);
            _tileNameByIndex[tile.PositionIndex] = safeName;
            _tileTypeByIndex[tile.PositionIndex] = safeTileType;
            _tileStateByIndex[tile.PositionIndex] = safeState;
            if (!string.IsNullOrWhiteSpace(tile.TileId))
            {
                _positionIndexByTileId[tile.TileId] = tile.PositionIndex;
            }
        }

        EnsureBoardVisuals();
        _overlay.ClearOwners(_layout);
        UpdateCameraBounds();
        if (AutoCenterOnMapLoad)
        {
            CenterCameraToBounds();
        }
        else
        {
            ClampCameraTarget();
        }
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
        if (json.Length > 65536)
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

                var cityId = root.TryGetProperty("CityId", out var cityProp) && cityProp.ValueKind == JsonValueKind.String
                    ? (cityProp.GetString() ?? string.Empty)
                    : string.Empty;

                var cityIndex = 0;
                var hasIndex = !string.IsNullOrWhiteSpace(cityId) && _positionIndexByTileId.TryGetValue(cityId, out cityIndex);
                if (!hasIndex && !_lastPositionByPlayerId.TryGetValue(buyerId, out cityIndex))
                {
                    return;
                }

                EnsureBoardVisuals();
                _overlay.SetOwnerForIndex(_layout, _layout.ClampIndex(cityIndex), buyerId);
                return;
            }

            if (!root.TryGetProperty("ToIndex", out var toIndex) || !toIndex.TryGetInt32(out var parsedToIndex))
            {
                GD.PushWarning($"SanguoBoardView ignored event without valid ToIndex (type='{type}').");
                return;
            }

            if (TotalPositions <= 0)
            {
                SecurityAuditWriter.TryAppendSecurityAudit(
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
                SecurityAuditWriter.TryAppendSecurityAudit(
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
                SecurityAuditWriter.TryAppendSecurityAudit(
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

        // Keep human token on the lane, offset other players so overlapping tokens remain distinguishable.
        return basePos + new Vector2(0f, TokenLaneOffsetPixels);
    }

    private void EnsureBoardVisuals()
    {
        _layout.Configure(TotalPositions, StepPixels, Origin, UseSquareLayout);
        _overlay.EnsureBuilt(_layout);
        UpdateCameraBounds();
    }

    private void ResetBoardTransform()
    {
        Position = Vector2.Zero;
        Rotation = 0f;
        Scale = Vector2.One;
    }

    public void ResetCameraView()
    {
        ResetBoardTransform();
        EnsureBoardVisuals();
        UpdateCameraBounds();
        if (AutoCenterOnMapLoad)
        {
            CenterCameraToBounds();
        }
        else
        {
            ClampCameraTarget();
        }
    }

    private Vector2 ResolveWheelDelta(InputEventMouseButton mouseButton)
    {
        if (ScrollPixels <= 0)
        {
            return Vector2.Zero;
        }

        return mouseButton.ButtonIndex switch
        {
            MouseButton.WheelUp => new Vector2(0f, ScrollPixels),
            MouseButton.WheelDown => new Vector2(0f, -ScrollPixels),
            MouseButton.WheelLeft => new Vector2(ScrollPixels, 0f),
            MouseButton.WheelRight => new Vector2(-ScrollPixels, 0f),
            _ => Vector2.Zero
        };
    }

    private void EnsureCamera()
    {
        _camera = GetNodeOrNull<Camera2D>(CameraPath);
        if (_camera == null)
        {
            _camera = new Camera2D { Name = "Camera2D" };
            AddChild(_camera);
        }

        _camera.MakeCurrent();
        _cameraTarget = _camera.Position;

        if (EnableHoverTooltip)
        {
            _hoverTooltip = GetNodeOrNull<Label>(HoverTooltipPath);
            if (_hoverTooltip == null)
            {
                _hoverTooltip = new Label
                {
                    Name = "HoverTooltip",
                    Visible = false,
                    ZIndex = 10,
                    MouseFilter = Control.MouseFilterEnum.Ignore
                };
                AddChild(_hoverTooltip);
            }
        }
    }

    private void ApplyPanDelta(Vector2 delta)
    {
        if (_camera != null)
        {
            _cameraTarget -= delta;
            ClampCameraTarget();
        }
        else
        {
            Position += delta;
        }
    }

    private void UpdateCamera(double delta)
    {
        if (_camera == null)
        {
            return;
        }

        if (!_cameraBoundsValid)
        {
            UpdateCameraBounds();
        }

        ClampCameraTarget();

        if (!EnableCameraInertia || CameraInertiaSpeed <= 0f)
        {
            _camera.Position = _cameraTarget;
            return;
        }

        var t = 1f - MathF.Exp(-CameraInertiaSpeed * (float)delta);
        _camera.Position = _camera.Position.Lerp(_cameraTarget, t);
    }

    private void UpdateCameraBounds()
    {
        if (TotalPositions <= 0 || StepPixels <= 0)
        {
            _cameraBoundsValid = false;
            return;
        }

        var width = UseSquareLayout
            ? (_layout.LayoutEdgeSteps * StepPixels + StepPixels)
            : (TotalPositions * StepPixels + 16f);
        var height = UseSquareLayout
            ? (_layout.LayoutEdgeSteps * StepPixels + StepPixels)
            : 56f;
        var origin = _layout.Origin + new Vector2(-StepPixels * 0.5f, -StepPixels * 0.5f);
        _cameraBounds = new Rect2(GlobalPosition + origin, new Vector2(width, height));
        _cameraBoundsValid = true;
    }

    private void CenterCameraToBounds()
    {
        if (!_cameraBoundsValid || _camera == null)
        {
            return;
        }

        _cameraTarget = _cameraBounds.Position + _cameraBounds.Size * 0.5f;
        _camera.Position = _cameraTarget;
    }

    private void ClampCameraTarget()
    {
        if (!_cameraBoundsValid || _camera == null)
        {
            return;
        }

        var viewSize = GetViewport().GetVisibleRect().Size;
        var half = viewSize * 0.5f;
        var padding = new Vector2(CameraBoundsPadding, CameraBoundsPadding);
        var min = _cameraBounds.Position + half - padding;
        var max = _cameraBounds.Position + _cameraBounds.Size - half + padding;

        if (min.X > max.X)
        {
            _cameraTarget.X = _cameraBounds.Position.X + _cameraBounds.Size.X * 0.5f;
        }
        else
        {
            _cameraTarget.X = Math.Clamp(_cameraTarget.X, min.X, max.X);
        }

        if (min.Y > max.Y)
        {
            _cameraTarget.Y = _cameraBounds.Position.Y + _cameraBounds.Size.Y * 0.5f;
        }
        else
        {
            _cameraTarget.Y = Math.Clamp(_cameraTarget.Y, min.Y, max.Y);
        }
    }

    private void UpdateHover()
    {
        if ((!EnableHoverHighlight && !EnableHoverTooltip) || HoverDetectRadiusPixels <= 0f || _layout.TotalPositions <= 0)
        {
            ApplyHoverIndex(-1, Vector2.Zero);
            return;
        }

        var mouse = GetGlobalMousePosition();
        var maxDistSq = HoverDetectRadiusPixels * HoverDetectRadiusPixels;
        var nearestIndex = -1;
        var nearestPos = Vector2.Zero;

        for (var i = 0; i < _layout.TotalPositions; i++)
        {
            var worldPos = GlobalPosition + _layout.GetBasePositionForIndex(i);
            var distSq = mouse.DistanceSquaredTo(worldPos);
            if (distSq <= maxDistSq)
            {
                maxDistSq = distSq;
                nearestIndex = i;
                nearestPos = worldPos;
            }
        }

        ApplyHoverIndex(nearestIndex, nearestPos);
    }

    private void ApplyHoverIndex(int index, Vector2 worldPos)
    {
        if (index != _hoverIndex)
        {
            _hoverIndex = index;
            if (EnableHoverHighlight)
            {
                _overlay.SetHoverIndex(_layout, index);
            }
        }

        if (!EnableHoverTooltip || _hoverTooltip == null)
        {
            return;
        }

        if (index < 0)
        {
            _hoverTooltip.Visible = false;
            return;
        }

        var tooltipText = BuildHoverText(index);
        if (string.IsNullOrWhiteSpace(tooltipText))
        {
            _hoverTooltip.Visible = false;
            return;
        }

        _hoverTooltip.Text = tooltipText;
        _hoverTooltip.Visible = true;
        var localPos = ToLocal(worldPos);
        _hoverTooltip.Position = localPos + new Vector2(12f, -20f);
    }

    private string BuildHoverText(int index)
    {
        var nameKey = _tileNameByIndex.TryGetValue(index, out var n) ? n : string.Empty;
        var name = TranslateOrFallback(nameKey);
        var kind = _tileTypeByIndex.TryGetValue(index, out var k) ? k : "tile";
        var kindLabel = TranslateKind(kind);
        var detailLabel = ResolveKindDetailLabel(kind, index, kindLabel);
        if (string.IsNullOrWhiteSpace(name))
        {
            return string.IsNullOrWhiteSpace(detailLabel) ? kindLabel : $"{kindLabel}: {detailLabel}";
        }

        if (string.IsNullOrWhiteSpace(detailLabel))
        {
            return $"{name} ({kindLabel})";
        }

        return $"{name} ({kindLabel}: {detailLabel})";
    }

    private static string TranslateOrFallback(string key)
    {
        if (string.IsNullOrWhiteSpace(key))
        {
            return string.Empty;
        }

        var translated = TranslationServer.Translate(key);
        return string.IsNullOrWhiteSpace(translated) ? key : translated;
    }

    private static string TranslateKind(string kind)
    {
        if (string.IsNullOrWhiteSpace(kind))
        {
            return string.Empty;
        }

        var key = $"tile.kind.{kind.Trim().ToLowerInvariant()}";
        var translated = TranslationServer.Translate(key);
        if (string.IsNullOrWhiteSpace(translated) || string.Equals(translated, key, StringComparison.Ordinal))
        {
            return kind;
        }

        return translated;
    }

    private string ResolveKindDetailLabel(string kind, int index, string kindLabel)
    {
        var normalized = (kind ?? string.Empty).Trim().ToLowerInvariant();
        if (!_tileStateByIndex.TryGetValue(index, out var stateId) || string.IsNullOrWhiteSpace(stateId))
        {
            return string.Empty;
        }

        var detail = normalized switch
        {
            "city" => ResolveRegionLabel(stateId),
            "event" => ResolveEventPoolLabel(stateId),
            "wild" => ResolveWildLabel(stateId),
            "pass" or "facility" => ResolveFacilityLabel(stateId),
            _ => string.Empty
        };

        if (string.IsNullOrWhiteSpace(detail))
        {
            return string.Empty;
        }

        if (!string.IsNullOrWhiteSpace(kindLabel)
            && string.Equals(detail, kindLabel, StringComparison.OrdinalIgnoreCase))
        {
            return string.Empty;
        }

        return detail;
    }

    private static string ResolveRegionLabel(string stateId)
    {
        var regionId = StripPrefix(stateId, "region:");
        if (string.IsNullOrWhiteSpace(regionId) || string.Equals(regionId, "unknown", StringComparison.OrdinalIgnoreCase))
        {
            return string.Empty;
        }

        var key = $"region.{regionId}.name";
        return TranslateKeyOrFallback(key, regionId);
    }

    private static string ResolveEventPoolLabel(string stateId)
    {
        var poolId = StripPrefix(stateId, "event_pool:");
        if (string.IsNullOrWhiteSpace(poolId) || string.Equals(poolId, "unknown", StringComparison.OrdinalIgnoreCase))
        {
            return string.Empty;
        }

        var key = $"event_pool.{poolId}.name";
        return TranslateKeyOrFallback(key, poolId);
    }

    private static string ResolveWildLabel(string stateId)
    {
        var wildId = StripPrefix(stateId, "wild:");
        if (string.IsNullOrWhiteSpace(wildId) || string.Equals(wildId, "unknown", StringComparison.OrdinalIgnoreCase))
        {
            return string.Empty;
        }

        var key = $"wild.{wildId}.name";
        return TranslateKeyOrFallback(key, wildId);
    }

    private static string ResolveFacilityLabel(string stateId)
    {
        var facilityId = StripPrefix(stateId, "facility:");
        if (string.IsNullOrWhiteSpace(facilityId) || string.Equals(facilityId, "unknown", StringComparison.OrdinalIgnoreCase))
        {
            return string.Empty;
        }

        var key = $"facility.{facilityId}.name";
        return TranslateKeyOrFallback(key, facilityId);
    }

    private static string StripPrefix(string value, string prefix)
    {
        if (value.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
        {
            return value.Substring(prefix.Length);
        }

        return value;
    }

    private static string TranslateKeyOrFallback(string key, string fallback)
    {
        if (string.IsNullOrWhiteSpace(key))
        {
            return fallback;
        }

        var translated = TranslationServer.Translate(key);
        return string.IsNullOrWhiteSpace(translated) || string.Equals(translated, key, StringComparison.Ordinal)
            ? fallback
            : translated;
    }
}
