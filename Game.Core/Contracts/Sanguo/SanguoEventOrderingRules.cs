using System;
using System.Collections.Generic;
using System.Linq;
using Game.Core.Contracts;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Deterministic ordering rules for Sanguo domain events.
/// </summary>
/// <remarks>
/// These rules are part of the contracts single source of truth (SSoT) and are enforced by unit tests.
///
/// Terminology:
/// - "Turn scope" means a group of events that belong to the same turn progression and share the same CorrelationId.
/// - "Active player" means the ActivePlayerId announced by <see cref="SanguoGameTurnStarted"/>.
///
/// Rules (must hold for events within the same turn scope):
/// A) Turn context first:
///    - <see cref="SanguoGameTurnStarted"/> MUST be published before any <see cref="SanguoPlayerStateChanged"/>
///      that is intended to update the active player's HUD for that turn scope.
/// B) State snapshots are results:
///    - <see cref="SanguoPlayerStateChanged"/> represents the post-mutation state of the player. Do not publish it
///      as an "intent" event. Publish it after the causative domain action has been applied.
/// C) Turn boundary last:
///    - <see cref="SanguoGameTurnEnded"/> MUST be the last event for the current turn number within the same turn scope.
///
/// Rationale:
/// - Prevent UI from missing an update due to out-of-order delivery (e.g., player.state.changed arriving before turn.started).
/// - Provide deterministic evidence for auditing, replay, and headless tests.
///
/// Related ADRs: ADR-0022, ADR-0005, ADR-0018.
/// </remarks>
/// <summary>
/// Provides deterministic order validation helpers for turn-scope Sanguo events.
/// </summary>
public static class SanguoEventOrderingRules
{
    public readonly record struct ReplayStableEvent(
        int RoundNumber,
        long Tick,
        string EventType,
        int SourceOrder);

    /// <summary>
    /// The primary ordering scope key used by this project for turn progression.
    /// </summary>
    public const string TurnScopeKey = "CorrelationId";

    public static IReadOnlyDictionary<string, int> EventTypeOrderIndex { get; } = BuildEventTypeOrderIndex();

    public static void Validate(IEnumerable<string> eventTypes)
    {
        if (eventTypes is null)
            throw new ArgumentNullException(nameof(eventTypes));

        var list = eventTypes.Where(x => !string.IsNullOrWhiteSpace(x)).ToArray();
        if (list.Length == 0)
            return;

        var iTurnStarted = IndexOfFirst(list, SanguoGameTurnStarted.EventType);
        var iPlayerStateChanged = IndexOfFirst(list, SanguoPlayerStateChanged.EventType);
        if (iPlayerStateChanged >= 0 && iTurnStarted >= 0 && iPlayerStateChanged < iTurnStarted)
            throw new InvalidOperationException($"{SanguoPlayerStateChanged.EventType} must not precede {SanguoGameTurnStarted.EventType} within the same turn scope.");

        var iTurnEnded = IndexOfFirst(list, SanguoGameTurnEnded.EventType);
        if (iTurnEnded >= 0 && iTurnEnded != list.Length - 1)
            throw new InvalidOperationException($"{SanguoGameTurnEnded.EventType} must be the last event within the same turn scope.");
    }

    public static IReadOnlyList<string> BuildReplayStableSnapshot(IEnumerable<ReplayStableEvent> events)
    {
        if (events is null)
            throw new ArgumentNullException(nameof(events));

        var normalized = events.Select(item =>
        {
            if (item.RoundNumber <= 0)
                throw new ArgumentOutOfRangeException(nameof(events), "RoundNumber must be >= 1.");
            if (item.Tick < 0)
                throw new ArgumentOutOfRangeException(nameof(events), "Tick must be >= 0.");
            if (item.SourceOrder < 0)
                throw new ArgumentOutOfRangeException(nameof(events), "SourceOrder must be >= 0.");
            if (string.IsNullOrWhiteSpace(item.EventType))
                throw new ArgumentException("EventType must be non-empty.", nameof(events));
            return item;
        }).ToArray();

        var ordered = normalized
            .OrderBy(item => item.RoundNumber)
            .ThenBy(item => item.Tick)
            .ThenBy(item => ResolveEventTypeOrder(item.EventType))
            .ThenBy(item => item.EventType, StringComparer.Ordinal)
            .ThenBy(item => item.SourceOrder)
            .ToArray();

        var result = new List<string>(ordered.Length);
        foreach (var item in ordered)
        {
            var order = ResolveEventTypeOrder(item.EventType);
            var slot = order == int.MaxValue ? "UNK" : order.ToString("D4");
            result.Add(
                $"round={item.RoundNumber:D4}|tick={item.Tick:D8}|slot={slot}|source={item.SourceOrder:D4}|type={item.EventType}");
        }

        return result;
    }

    public static void AssertReplayStableSnapshot(
        IEnumerable<string> expectedSnapshot,
        IEnumerable<string> actualSnapshot)
    {
        if (expectedSnapshot is null)
            throw new ArgumentNullException(nameof(expectedSnapshot));
        if (actualSnapshot is null)
            throw new ArgumentNullException(nameof(actualSnapshot));

        var expected = expectedSnapshot.ToArray();
        var actual = actualSnapshot.ToArray();

        if (expected.Length != actual.Length)
        {
            throw new InvalidOperationException(
                $"replay snapshot drift: length mismatch expected={expected.Length} actual={actual.Length}");
        }

        for (var i = 0; i < expected.Length; i++)
        {
            if (!StringComparer.Ordinal.Equals(expected[i], actual[i]))
            {
                throw new InvalidOperationException(
                    $"replay snapshot drift at index {i}: expected='{expected[i]}' actual='{actual[i]}'");
            }
        }
    }

    private static int IndexOfFirst(string[] list, string eventType)
    {
        for (var i = 0; i < list.Length; i++)
        {
            if (StringComparer.Ordinal.Equals(list[i], eventType))
                return i;
        }

        return -1;
    }

    private static int ResolveEventTypeOrder(string eventType)
    {
        if (EventTypeOrderIndex.TryGetValue(eventType, out var order))
            return order;
        return int.MaxValue;
    }

    private static IReadOnlyDictionary<string, int> BuildEventTypeOrderIndex()
    {
        var ordered = new[]
        {
            SanguoRandomEventApplied.EventType,
            SanguoGameTurnStarted.EventType,
            SanguoPlayerStateChanged.EventType,
            SanguoGameTurnEnded.EventType,
            EventTypes.RunStateTransitioned,
        };

        var dict = new Dictionary<string, int>(StringComparer.Ordinal);
        for (var i = 0; i < ordered.Length; i++)
            dict[ordered[i]] = i;

        return dict;
    }
}
