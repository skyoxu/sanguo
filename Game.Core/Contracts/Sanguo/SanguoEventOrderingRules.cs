using System;
using System.Collections.Generic;
using System.Linq;

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
public static class SanguoEventOrderingRules
{
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

    private static int IndexOfFirst(string[] list, string eventType)
    {
        for (var i = 0; i < list.Length; i++)
        {
            if (StringComparer.Ordinal.Equals(list[i], eventType))
                return i;
        }

        return -1;
    }

    private static IReadOnlyDictionary<string, int> BuildEventTypeOrderIndex()
    {
        var ordered = new[]
        {
            SanguoRandomEventApplied.EventType,
            SanguoGameTurnStarted.EventType,
            SanguoPlayerStateChanged.EventType,
            SanguoGameTurnEnded.EventType,
        };

        var dict = new Dictionary<string, int>(StringComparer.Ordinal);
        for (var i = 0; i < ordered.Length; i++)
            dict[ordered[i]] = i;

        return dict;
    }
}

