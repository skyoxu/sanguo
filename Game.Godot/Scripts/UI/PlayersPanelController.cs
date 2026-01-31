using Godot;
using System;
using System.Collections.Generic;

namespace Game.Godot.Scripts.UI;

public sealed class PlayersPanelController
{
    private readonly VBoxContainer _list;

    public PlayersPanelController(VBoxContainer list)
    {
        _list = list ?? throw new ArgumentNullException(nameof(list));
    }

    public void Render(
        IReadOnlyDictionary<string, PlayerStateSnapshot> states,
        Func<string, string> displayNameResolver,
        Func<string, bool> isAi)
    {
        if (states is null || displayNameResolver is null || isAi is null)
        {
            return;
        }

        foreach (var child in _list.GetChildren())
        {
            if (child is Node node)
            {
                node.QueueFree();
            }
        }

        if (states.Count == 0)
        {
            return;
        }

        var ids = new List<string>(states.Keys);
        ids.Sort(StringComparer.Ordinal);

        foreach (var playerId in ids)
        {
            if (!states.TryGetValue(playerId, out var state))
            {
                continue;
            }

            var displayName = displayNameResolver(playerId);
            var idLabel = string.Equals(displayName, playerId, StringComparison.Ordinal)
                ? playerId
                : $"{displayName} ({playerId})";
            var posText = state.PositionIndex >= 0 ? state.PositionIndex.ToString() : "-";
            var text = $"Player: {idLabel} | Money: {state.Money} | Pos: {posText}";
            if (isAi(playerId))
            {
                text += " | AI";
            }

            var label = new Label { Text = text };
            _list.AddChild(label);
        }
    }
}

public readonly record struct PlayerStateSnapshot(decimal Money, int PositionIndex);
