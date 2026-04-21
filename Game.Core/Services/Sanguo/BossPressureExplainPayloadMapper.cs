using System;
using System.Collections.Generic;
using System.Linq;

namespace Game.Core.Services.Sanguo;

public static class BossPressureExplainPayloadMapper
{
    public static IReadOnlyList<BossPressureExplainPayloadItem> Map(
        IReadOnlyList<BossPressureExplainPayloadInput> rawEntries)
    {
        ArgumentNullException.ThrowIfNull(rawEntries);

        return rawEntries
            .Select(entry => new BossPressureExplainPayloadItem(
                Source: entry.Source,
                Value: entry.Value,
                Duration: entry.Duration))
            .ToArray();
    }
}

public sealed record BossPressureExplainPayloadInput(
    string Source,
    int Value,
    int Duration,
    bool FromDelayStacking);

public sealed record BossPressureExplainPayloadItem(
    string Source,
    int Value,
    int Duration);
