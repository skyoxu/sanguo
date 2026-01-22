using System;
using System.Collections.Generic;
using System.Linq;

namespace Game.Core.Services.Sanguo;

public static class SanguoCharacterAssignmentsGenerator
{
    public static bool TryBuildAssignments(
        IReadOnlyList<string> availableCharacterIds,
        int playersCount,
        string playerCharacterId,
        int seed,
        out IReadOnlyDictionary<string, string> assignments,
        out string error)
    {
        assignments = new Dictionary<string, string>(StringComparer.Ordinal);
        error = string.Empty;

        if (playersCount < 1)
        {
            error = "players_count_invalid";
            return false;
        }

        if (string.IsNullOrWhiteSpace(playerCharacterId))
        {
            error = "player_character_empty";
            return false;
        }

        if (availableCharacterIds is null || availableCharacterIds.Count == 0)
        {
            error = "insufficient_characters";
            return false;
        }

        var available = availableCharacterIds
            .Where(x => !string.IsNullOrWhiteSpace(x))
            .Distinct(StringComparer.Ordinal)
            .ToArray();

        if (!available.Contains(playerCharacterId, StringComparer.Ordinal))
        {
            error = "player_character_not_found";
            return false;
        }

        if (available.Length < playersCount)
        {
            error = "insufficient_characters";
            return false;
        }

        var remaining = available.Where(x => !string.Equals(x, playerCharacterId, StringComparison.Ordinal)).ToArray();
        var rnd = new Random(seed);
        for (var i = remaining.Length - 1; i > 0; i--)
        {
            var j = rnd.Next(i + 1);
            (remaining[i], remaining[j]) = (remaining[j], remaining[i]);
        }

        var dict = new Dictionary<string, string>(capacity: playersCount, comparer: StringComparer.Ordinal)
        {
            ["p1"] = playerCharacterId,
        };

        for (var i = 1; i < playersCount; i++)
        {
            dict[$"ai-{i}"] = remaining[i - 1];
        }

        assignments = dict;
        return true;
    }
}

