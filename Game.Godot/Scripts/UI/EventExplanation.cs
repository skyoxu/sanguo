using System;

namespace Game.Godot.Scripts.UI;

/// <summary>
/// UI-facing explanation for a domain event (facts-only, no inference).
/// </summary>
public sealed record EventExplanation(
    string EventType,
    string SummaryText,
    string DetailText,
    string Source,
    string EventId,
    string TimestampIso,
    string? CorrelationId,
    string? CausationId
)
{
    public static EventExplanation Minimal(string eventType, string source, string eventId, string timestampIso) =>
        new(
            EventType: eventType,
            SummaryText: eventType,
            DetailText: $"type: {eventType}\nsource: {source}\nid: {eventId}\nts: {timestampIso}",
            Source: source,
            EventId: eventId,
            TimestampIso: timestampIso,
            CorrelationId: null,
            CausationId: null
        );
}

