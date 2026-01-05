using Godot;
using System;
using System.Collections.Generic;

namespace Game.Godot.Scripts.Sanguo;

internal sealed class SanguoBoardTokens
{
    private const string TokenVisualNodeName = "__TokenVisual__";

    private readonly Node2D _root;
    private readonly Dictionary<string, Node2D> _tokensByPlayerId;

    internal SanguoBoardTokens(Node2D root, Dictionary<string, Node2D> tokensByPlayerId)
    {
        _root = root ?? throw new ArgumentNullException(nameof(root));
        _tokensByPlayerId = tokensByPlayerId ?? throw new ArgumentNullException(nameof(tokensByPlayerId));
    }

    internal Node2D? ResolvePrimary(NodePath tokenPath)
    {
        if (tokenPath.IsEmpty)
        {
            return null;
        }

        return _root.GetNodeOrNull<Node2D>(tokenPath);
    }

    internal Node2D EnsureExtraToken(string playerId)
    {
        if (_tokensByPlayerId.TryGetValue(playerId, out var existing))
        {
            return existing;
        }

        var token = new Node2D
        {
            Name = $"Token_{SanitizeNodeName(playerId)}",
        };
        _root.AddChild(token);
        _tokensByPlayerId[playerId] = token;
        return token;
    }

    internal Node2D? ResolveTokenForPlayerId(string playerId, NodePath tokenPath, Color humanColor, Color aiColor, Color neutralColor)
    {
        if (_tokensByPlayerId.TryGetValue(playerId, out var token))
        {
            return token;
        }

        if (string.Equals(playerId, "p1", StringComparison.Ordinal))
        {
            var primary = ResolvePrimary(tokenPath);
            if (primary != null)
            {
                _tokensByPlayerId[playerId] = primary;
                EnsureTokenHasVisual(primary, humanColor);
            }
            return primary;
        }

        var extra = EnsureExtraToken(playerId);
        EnsureTokenHasVisual(extra, SanguoGlueJson.IsAiPlayerId(playerId) ? aiColor : neutralColor);
        return extra;
    }

    internal static void EnsureTokenHasVisual(Node2D token, Color color)
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
            Color = color,
            Polygon = new[]
            {
                new Vector2(-8, -8),
                new Vector2(8, -8),
                new Vector2(8, 8),
                new Vector2(-8, 8),
            },
        };

        token.AddChild(visual);
    }

    private static string SanitizeNodeName(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "unknown";
        }

        var chars = value.Trim().ToCharArray();
        for (int i = 0; i < chars.Length; i++)
        {
            var c = chars[i];
            if (!(char.IsLetterOrDigit(c) || c == '_' || c == '-'))
            {
                chars[i] = '_';
            }
        }

        return new string(chars);
    }
}

