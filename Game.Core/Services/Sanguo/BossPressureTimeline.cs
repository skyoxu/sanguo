using System;
using System.Collections.Generic;

using Game.Core.Contracts.Sanguo;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Deterministic timeline replay for the Task 89 split scope.
/// </summary>
public static class BossPressureTimeline
{
    public static BossPressureTimelineReplayResult ReplayEventTypes(IEnumerable<string> eventTypes)
    {
        ArgumentNullException.ThrowIfNull(eventTypes);

        var pressureByStep = new List<int>();
        var currentPressure = 0;

        foreach (var eventType in eventTypes)
        {
            if (string.Equals(eventType, SanguoGameTurnAdvanced.EventType, StringComparison.Ordinal))
            {
                currentPressure += 1;
            }
            else if (string.Equals(eventType, SanguoCombatStarted.EventType, StringComparison.Ordinal))
            {
                currentPressure = 0;
            }
            else
            {
                throw new ArgumentException(
                    $"Unsupported event type for Task 89 split scope: '{eventType}'.",
                    nameof(eventTypes));
            }

            pressureByStep.Add(currentPressure);
        }

        return new BossPressureTimelineReplayResult(pressureByStep);
    }
}

public sealed record BossPressureTimelineReplayResult(IReadOnlyList<int> PressureByStep);
