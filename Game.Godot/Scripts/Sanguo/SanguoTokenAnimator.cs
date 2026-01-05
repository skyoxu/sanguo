using Godot;
using System;
using System.Collections.Generic;

namespace Game.Godot.Scripts.Sanguo;

internal sealed class SanguoTokenAnimator
{
    private readonly Node _owner;
    private readonly Dictionary<string, Tween> _tweensByPlayerId = new(StringComparer.Ordinal);

    internal SanguoTokenAnimator(Node owner)
    {
        _owner = owner ?? throw new ArgumentNullException(nameof(owner));
    }

    internal void KillAll()
    {
        foreach (var tween in _tweensByPlayerId.Values)
        {
            tween?.Kill();
        }
        _tweensByPlayerId.Clear();
    }

    internal bool MoveTo(string playerId, Node2D token, Vector2 targetLocalPosition, double durationSeconds)
    {
        KillForPlayer(playerId);

        if (durationSeconds <= 0)
        {
            token.Position = targetLocalPosition;
            return false;
        }

        var tween = _owner.CreateTween();
        _tweensByPlayerId[playerId] = tween;
        tween.TweenProperty(token, "position", targetLocalPosition, durationSeconds);
        return true;
    }

    internal bool MoveAlongPath(
        string playerId,
        Node2D token,
        int totalPositions,
        int fromIndex,
        int steps,
        double durationSeconds,
        Func<int, Vector2> targetForIndex)
    {
        KillForPlayer(playerId);

        if (durationSeconds <= 0 || steps <= 1 || totalPositions <= 0)
        {
            var target = targetForIndex(fromIndex);
            token.Position = target;
            return false;
        }

        var tween = _owner.CreateTween();
        _tweensByPlayerId[playerId] = tween;

        var perStep = durationSeconds / Math.Max(1, steps);
        for (int i = 1; i <= steps; i++)
        {
            var index = (fromIndex + i) % totalPositions;
            tween.TweenProperty(token, "position", targetForIndex(index), perStep);
        }

        return true;
    }

    private void KillForPlayer(string playerId)
    {
        if (_tweensByPlayerId.TryGetValue(playerId, out var tween))
        {
            tween.Kill();
            _tweensByPlayerId.Remove(playerId);
        }
    }
}

