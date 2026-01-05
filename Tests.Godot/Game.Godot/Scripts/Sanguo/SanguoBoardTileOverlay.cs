using Godot;
using System;
using System.Collections.Generic;

namespace Game.Godot.Scripts.Sanguo;

internal sealed class SanguoBoardTileOverlay
{
    private const string BoardBackgroundNodeName = "__BoardBackground__";
    private const string BoardTilePrefix = "__BoardTile__";
    private const string BoardTileLabelPrefix = "__BoardTileLabel__";

    private static readonly Color HumanColor = new(0.9f, 0.2f, 0.2f, 1f);
    private static readonly Color AiColor = new(0.2f, 0.4f, 0.9f, 1f);
    private static readonly Color TileBaseA = new(0.18f, 0.18f, 0.18f, 1f);
    private static readonly Color TileBaseB = new(0.22f, 0.22f, 0.22f, 1f);
    private static readonly Color TileBasePass = new(0.62f, 0.54f, 0.18f, 1f);
    private static readonly Color TileBaseWild = new(0.18f, 0.52f, 0.22f, 1f);
    private static readonly Color TileUnowned = new(0.32f, 0.32f, 0.32f, 1f);

    private readonly Node2D _root;
    private bool _built;
    private int _builtTotalPositions;
    private readonly Dictionary<int, string> _ownerByIndex = new();
    private readonly Dictionary<int, string> _tileTypeByIndex = new();
    private readonly Dictionary<int, string> _baseLabelByIndex = new();

    internal SanguoBoardTileOverlay(Node2D root)
    {
        _root = root ?? throw new ArgumentNullException(nameof(root));
    }

    internal void EnsureBuilt(SanguoBoardLayout layout)
    {
        if (_built && layout.TotalPositions != _builtTotalPositions)
        {
            TeardownExisting();
            _built = false;
            _builtTotalPositions = 0;
        }

        if (_built)
        {
            return;
        }

        if (layout.TotalPositions <= 0 || layout.StepPixels <= 0)
        {
            return;
        }

        _built = true;
        _builtTotalPositions = layout.TotalPositions;

        EnsureBackground(layout);
        EnsureTiles(layout);

        foreach (var (index, tileType) in _tileTypeByIndex)
        {
            ApplyBase(index, tileType);
        }

        foreach (var (index, baseLabel) in _baseLabelByIndex)
        {
            ApplyBaseLabel(index, baseLabel);
        }

        foreach (var kv in _ownerByIndex)
        {
            ApplyOwner(kv.Key, kv.Value);
        }
    }

    internal void ClearOwners(SanguoBoardLayout layout)
    {
        _ownerByIndex.Clear();
        if (!_built)
        {
            return;
        }

        for (var i = 0; i < layout.TotalPositions; i++)
        {
            ApplyOwner(i, string.Empty);
        }
    }

    internal void SetOwnerForIndex(SanguoBoardLayout layout, int index, string ownerId)
    {
        if (index < 0)
        {
            return;
        }

        _ownerByIndex[index] = ownerId;
        if (_built)
        {
            ApplyOwner(index, ownerId);
        }
    }

    internal void SetTileTypeForIndex(int index, string tileType)
    {
        if (index < 0)
        {
            return;
        }

        _tileTypeByIndex[index] = tileType ?? string.Empty;
        if (_built)
        {
            ApplyBase(index, tileType);
            ApplyOwnerColor(index, _ownerByIndex.TryGetValue(index, out var owner) ? owner : string.Empty);
        }
    }

    internal void SetBaseLabelForIndex(int index, string label)
    {
        if (index < 0)
        {
            return;
        }

        _baseLabelByIndex[index] = label ?? string.Empty;
        if (_built)
        {
            ApplyBaseLabel(index, label);
            ApplyOwnerLabel(index, _ownerByIndex.TryGetValue(index, out var owner) ? owner : string.Empty);
        }
    }

    private void EnsureBackground(SanguoBoardLayout layout)
    {
        if (_root.GetNodeOrNull<Node>(BoardBackgroundNodeName) != null)
        {
            return;
        }

        var w = layout.UseSquareLayout
            ? (layout.LayoutEdgeSteps * layout.StepPixels + layout.StepPixels)
            : (layout.TotalPositions * layout.StepPixels + 16f);
        var h = layout.UseSquareLayout
            ? (layout.LayoutEdgeSteps * layout.StepPixels + layout.StepPixels)
            : 56f;

        var background = new Polygon2D
        {
            Name = BoardBackgroundNodeName,
            Color = new Color(0.08f, 0.08f, 0.08f, 1f),
            Polygon = new[]
            {
                new Vector2(0, 0),
                new Vector2(w, 0),
                new Vector2(w, h),
                new Vector2(0, h),
            },
            ZIndex = -20,
            Position = layout.Origin + new Vector2(-layout.StepPixels * 0.5f, -layout.StepPixels * 0.5f),
        };

        _root.AddChild(background);
    }

    private void EnsureTiles(SanguoBoardLayout layout)
    {
        for (int i = 0; i < layout.TotalPositions; i++)
        {
            var name = $"{BoardTilePrefix}{i}";
            if (_root.GetNodeOrNull<Node>(name) != null)
            {
                continue;
            }

            var tileColor = ResolveBaseColor(i, _tileTypeByIndex.TryGetValue(i, out var tileType) ? tileType : string.Empty);
            var half = MathF.Max(6f, MathF.Min(24f, layout.StepPixels * 0.35f));
            var pos = layout.GetBasePositionForIndex(i);
            var tile = new Polygon2D
            {
                Name = name,
                Color = tileColor,
                Polygon = new[]
                {
                    new Vector2(-half, -half),
                    new Vector2(half, -half),
                    new Vector2(half, half),
                    new Vector2(-half, half),
                },
                ZIndex = -10,
                Position = pos,
            };

            _root.AddChild(tile);
            EnsureOwnerLabelForIndex(layout, i, pos);
            ApplyOwner(i, _ownerByIndex.TryGetValue(i, out var owner) ? owner : string.Empty);
        }
    }

    private void ApplyOwner(int index, string ownerId)
    {
        ApplyOwnerColor(index, ownerId);
        ApplyOwnerLabel(index, ownerId);
    }

    private void ApplyOwnerColor(int index, string ownerId)
    {
        var tile = _root.GetNodeOrNull<Polygon2D>($"{BoardTilePrefix}{index}");
        if (tile == null)
        {
            return;
        }

        var tileType = _tileTypeByIndex.TryGetValue(index, out var tt) ? tt : string.Empty;
        var baseColor = ResolveBaseColor(index, tileType);
        var ownerColor = string.Equals(ownerId, "p1", StringComparison.Ordinal)
            ? HumanColor
            : (SanguoGlueJson.IsAiPlayerId(ownerId) ? AiColor : TileUnowned);
        tile.Color = string.IsNullOrWhiteSpace(ownerId) ? baseColor : baseColor.Lerp(ownerColor, 0.65f);
    }

    private void EnsureOwnerLabelForIndex(SanguoBoardLayout layout, int index, Vector2 tileLocalPosition)
    {
        var name = $"{BoardTileLabelPrefix}{index}";
        if (_root.GetNodeOrNull<Node>(name) != null)
        {
            return;
        }

        var label = new Label
        {
            Name = name,
            Text = string.Empty,
            ZIndex = -5,
            MouseFilter = Control.MouseFilterEnum.Ignore,
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center,
            Size = new Vector2(MathF.Max(32f, layout.StepPixels), 32f),
            Position = tileLocalPosition + new Vector2(-MathF.Max(16f, layout.StepPixels * 0.5f), -16f),
        };

        _root.AddChild(label);
    }

    private void ApplyOwnerLabel(int index, string ownerId)
    {
        var label = _root.GetNodeOrNull<Label>($"{BoardTileLabelPrefix}{index}");
        if (label == null)
        {
            return;
        }

        if (string.IsNullOrWhiteSpace(ownerId))
        {
            label.Text = _baseLabelByIndex.TryGetValue(index, out var baseLabel) ? baseLabel : string.Empty;
            label.Modulate = Colors.White;
            return;
        }

        var baseText = _baseLabelByIndex.TryGetValue(index, out var name) ? name : string.Empty;
        label.Text = string.IsNullOrWhiteSpace(baseText) ? ownerId : $"{baseText}\n{ownerId}";
        label.Modulate = string.Equals(ownerId, "p1", StringComparison.Ordinal)
            ? HumanColor
            : (SanguoGlueJson.IsAiPlayerId(ownerId) ? AiColor : Colors.White);
    }

    private void ApplyBase(int index, string tileType)
    {
        var tile = _root.GetNodeOrNull<Polygon2D>($"{BoardTilePrefix}{index}");
        if (tile == null)
        {
            return;
        }

        var baseColor = ResolveBaseColor(index, tileType);
        tile.Color = baseColor;
    }

    private void ApplyBaseLabel(int index, string baseLabel)
    {
        var label = _root.GetNodeOrNull<Label>($"{BoardTileLabelPrefix}{index}");
        if (label == null)
        {
            return;
        }

        if (_ownerByIndex.TryGetValue(index, out var ownerId) && !string.IsNullOrWhiteSpace(ownerId))
        {
            return;
        }

        label.Text = baseLabel ?? string.Empty;
    }

    private static Color ResolveBaseColor(int index, string tileType)
    {
        var normalized = (tileType ?? string.Empty).Trim().ToLowerInvariant();
        if (normalized == "pass")
        {
            return TileBasePass;
        }

        if (normalized == "wild")
        {
            return TileBaseWild;
        }

        return (index % 2 == 0) ? TileBaseA : TileBaseB;
    }

    private void TeardownExisting()
    {
        var children = _root.GetChildren();
        foreach (var child in children)
        {
            if (child is not Node node)
            {
                continue;
            }

            var name = node.Name.ToString();
            if (name == BoardBackgroundNodeName
                || name.StartsWith(BoardTilePrefix, StringComparison.Ordinal)
                || name.StartsWith(BoardTileLabelPrefix, StringComparison.Ordinal))
            {
                node.QueueFree();
            }
        }
    }
}
