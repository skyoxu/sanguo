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
}

