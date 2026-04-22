using System;
using System.Collections.Generic;
using System.Globalization;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Deterministic replay helper for Task 135 split scope.
/// </summary>
public static class BossRevealDelayPressureStackingEngine
{
    public static BossRevealDelayPressureReplayResult Replay(IReadOnlyList<string> signals)
    {
        ArgumentNullException.ThrowIfNull(signals);

        var storedPressure = 0;
        var pressureByRound = new List<int>();
        var stateTimeline = new List<string>();
        var auditTrail = new List<string>();
        var persistedState = string.Empty;
        var forcedChallengeTriggered = false;

        foreach (var signal in signals)
        {
            if (signal.StartsWith("seed_pressure:", StringComparison.Ordinal))
            {
                storedPressure = ParseIntSuffix(signal, "seed_pressure:");
                auditTrail.Add("seed_loaded");
                continue;
            }

            if (signal.StartsWith("ui_trace_pressure:", StringComparison.Ordinal))
            {
                // Lossy UI trace is intentionally ignored for deterministic restoration.
                auditTrail.Add("ui_trace_received");
                continue;
            }

            if (signal.Contains("boss_unrevealed", StringComparison.Ordinal))
            {
                storedPressure += 1;
                stateTimeline.Add("unrevealed");
                auditTrail.Add("delay_stack_applied");
                continue;
            }

            if (signal.Contains("boss_revealed_delayed", StringComparison.Ordinal))
            {
                storedPressure += 1;
                stateTimeline.Add("revealed_delayed");
                auditTrail.Add("delay_stack_applied");
                continue;
            }

            if (signal.Contains("challenge_failed", StringComparison.Ordinal))
            {
                storedPressure += 1;
                auditTrail.Add("challenge_failed_stack");
                continue;
            }

            if (signal.EndsWith(":end", StringComparison.Ordinal))
            {
                pressureByRound.Add(storedPressure);
                auditTrail.Add("round_closed");
                continue;
            }

            if (string.Equals(signal, "save", StringComparison.Ordinal))
            {
                persistedState = $"pressure={storedPressure}";
                auditTrail.Add("saved");
                continue;
            }

            if (string.Equals(signal, "load_from_save", StringComparison.Ordinal))
            {
                if (!string.IsNullOrWhiteSpace(persistedState))
                {
                    storedPressure = ParsePersistedPressure(persistedState, storedPressure);
                }

                auditTrail.Add("loaded_from_persisted_state");
                continue;
            }

            if (signal.Contains("forced_challenge_preempted", StringComparison.Ordinal))
            {
                forcedChallengeTriggered = true;
                stateTimeline.Add("forced_challenge");
                auditTrail.Add("forced_challenge_preempted");
                continue;
            }
        }

        if (pressureByRound.Count == 0 || pressureByRound[^1] != storedPressure)
        {
            pressureByRound.Add(storedPressure);
        }

        if (string.IsNullOrWhiteSpace(persistedState))
        {
            persistedState = $"pressure={storedPressure}";
        }

        return new BossRevealDelayPressureReplayResult(
            StoredPressure: storedPressure,
            PressureByRound: pressureByRound,
            StateTimeline: stateTimeline,
            ForcedChallengeTriggered: forcedChallengeTriggered,
            PersistedState: persistedState,
            AuditTrail: auditTrail);
    }

    private static int ParseIntSuffix(string value, string prefix)
    {
        var raw = value.Substring(prefix.Length);
        return int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed)
            ? parsed
            : 0;
    }

    private static int ParsePersistedPressure(string persistedState, int fallback)
    {
        const string prefix = "pressure=";
        if (!persistedState.StartsWith(prefix, StringComparison.Ordinal))
        {
            return fallback;
        }

        var raw = persistedState.Substring(prefix.Length);
        return int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed)
            ? parsed
            : fallback;
    }
}

public sealed record BossRevealDelayPressureReplayResult(
    int StoredPressure,
    IReadOnlyList<int> PressureByRound,
    IReadOnlyList<string> StateTimeline,
    bool ForcedChallengeTriggered,
    string PersistedState,
    IReadOnlyList<string> AuditTrail);
