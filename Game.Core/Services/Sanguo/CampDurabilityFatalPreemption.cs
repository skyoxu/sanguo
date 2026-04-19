using System;
using System.Collections.Generic;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Applies the camp-durability fatal preemption rule for same-frame collisions.
/// Fatal entries are promoted to the front while preserving relative order.
/// </summary>
public static class CampDurabilityFatalPreemption
{
    public static IReadOnlyList<T> Resolve<T>(
        IEnumerable<T> events,
        Func<T, bool> isCampDurabilityFatal)
    {
        if (events is null)
        {
            throw new ArgumentNullException(nameof(events));
        }

        if (isCampDurabilityFatal is null)
        {
            throw new ArgumentNullException(nameof(isCampDurabilityFatal));
        }

        var fatals = new List<T>();
        var others = new List<T>();

        foreach (var item in events)
        {
            if (isCampDurabilityFatal(item))
            {
                fatals.Add(item);
                continue;
            }

            others.Add(item);
        }

        var resolved = new List<T>(fatals.Count + others.Count);
        resolved.AddRange(fatals);
        resolved.AddRange(others);
        return resolved;
    }
}
