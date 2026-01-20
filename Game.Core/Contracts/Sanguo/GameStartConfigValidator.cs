using System;
using System.Collections.Generic;
using System.Linq;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Deterministic validation for <see cref="GameStartConfig"/> to support
/// new-game gating and auditable, reproducible game starts.
/// </summary>
public static class GameStartConfigValidator
{
    private static readonly int[] AllowedPlayersCounts = { 4, 5, 6, 7, 8 };
    private static readonly int[] AllowedStartingMoneyPresets = { 5000, 10000, 20000 };
    private static readonly int[] AllowedGlobalEventIntervals = { 5, 10, 20 };

    public static bool TryValidate(GameStartConfig cfg, out IReadOnlyList<string> errors)
    {
        var list = new List<string>();

        if (cfg is null)
        {
            list.Add("cfg_null");
            errors = list;
            return false;
        }

        if (string.IsNullOrWhiteSpace(cfg.MapId))
        {
            list.Add("map_id_empty");
        }

        if (!AllowedPlayersCounts.Contains(cfg.PlayersCount))
        {
            list.Add($"players_count_invalid:{cfg.PlayersCount}");
        }

        if (!AllowedStartingMoneyPresets.Contains(cfg.StartingMoneyPreset))
        {
            list.Add($"starting_money_preset_invalid:{cfg.StartingMoneyPreset}");
        }

        if (!AllowedGlobalEventIntervals.Contains(cfg.GlobalEventIntervalTurns))
        {
            list.Add($"global_event_interval_turns_invalid:{cfg.GlobalEventIntervalTurns}");
        }

        if (cfg.CharacterAssignments is null)
        {
            list.Add("character_assignments_null");
        }
        else
        {
            if (cfg.CharacterAssignments.Count != cfg.PlayersCount)
            {
                list.Add($"character_assignments_count_mismatch:assignments={cfg.CharacterAssignments.Count} players={cfg.PlayersCount}");
            }

            if (cfg.CharacterAssignments.Any(kvp => string.IsNullOrWhiteSpace(kvp.Key)))
            {
                list.Add("character_assignments_has_empty_player_id");
            }

            if (cfg.CharacterAssignments.Any(kvp => string.IsNullOrWhiteSpace(kvp.Value)))
            {
                list.Add("character_assignments_has_empty_character_id");
            }

            var values = cfg.CharacterAssignments.Values
                .Where(v => !string.IsNullOrWhiteSpace(v))
                .ToArray();
            if (values.Distinct(StringComparer.Ordinal).Count() != values.Length)
            {
                list.Add("character_assignments_has_duplicates");
            }
        }

        errors = list;
        return list.Count == 0;
    }
}

