#nullable enable

using System;

namespace Game.Core.Services;

public static class SanguoGlobalEventId
{
    public const string PrefixToken = "global:";

    public static string Prefix(string eventId) => WithGlobalPrefix(eventId);

    public static string PrefixGlobal(string eventId) => WithGlobalPrefix(eventId);

    public static string WithGlobalPrefix(string eventId)
    {
        if (string.IsNullOrWhiteSpace(eventId))
            throw new ArgumentException("EventId must be non-empty.", nameof(eventId));

        return eventId.StartsWith(PrefixToken, StringComparison.Ordinal)
            ? eventId
            : $"{PrefixToken}{eventId}";
    }
}

