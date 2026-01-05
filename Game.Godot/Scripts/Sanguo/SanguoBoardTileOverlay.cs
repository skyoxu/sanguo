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
    private static readonly Color TileUnowned = new(0.32f, 0.32f, 0.32f, 1f);

    private readonly Node2D _root;
    private bool _built;
    private readonly Dictionary<int, string> _ownerByIndex = new();

    internal SanguoBoardTileOverlay(Node2D root)
    {
        _root = root ?? throw new ArgumentNullException(nameof(root));
    }

    internal void EnsureBuilt(SanguoBoardLayout layout)
    {
        if (_built)
        {
            return;
        }

        if (layout.TotalPositions <= 0 || layout.StepPixels <= 0)
        {
            return;
        }

        _built = true;

        EnsureBackground(layout);
        EnsureTiles(layout);

        foreach (var kv in _ownerByIndex)
        {
            ApplyOwner(kv.Key, kv.Value);
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

            var tileColor = (i % 2 == 0) ? TileBaseA : TileBaseB;
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

        var baseColor = (index % 2 == 0) ? TileBaseA : TileBaseB;
        var ownerColor = string.Equals(ownerId, "p1", StringComparison.Ordinal)
            ? HumanColor
            : (SanguoGlueJson.IsAiPlayerId(ownerId) ? AiColor : TileUnowned);
        tile.Color = baseColor.Lerp(ownerColor, 0.65f);
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
            Size = new Vector2(MathF.Max(32f, layout.StepPixels), 18f),
            Position = tileLocalPosition + new Vector2(-MathF.Max(16f, layout.StepPixels * 0.5f), -9f),
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

        label.Text = ownerId;
        label.Modulate = string.Equals(ownerId, "p1", StringComparison.Ordinal)
            ? HumanColor
            : (SanguoGlueJson.IsAiPlayerId(ownerId) ? AiColor : Colors.White);
    }
}

