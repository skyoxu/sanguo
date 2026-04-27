namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Domain event: core.sanguo.game.started
/// Description: Emitted after a new game is created from a GameStartConfig and enters the playable loop.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates), ADR-0019 (security baseline).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoGameStarted(
    string GameId,
    string MapId,
    int PlayersCount,
    int StartingMoneyPreset,
    int GlobalEventIntervalTurns,
    int RandomSeed,
    string RunMode,
    string CommanderId,
    string Difficulty,
    System.Collections.Generic.IReadOnlyList<string> PlayerOrder,
    System.Collections.Generic.IReadOnlyDictionary<string, string> CharacterAssignments,
    string ActiveStrategemId,
    string PassiveStrategemId,
    System.DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.game.started";

    public int TurnNumber => 1;

    public int RoundNumber => 1;

    public string ActivePlayerId => PlayerOrder.Count > 0 ? PlayerOrder[0] : string.Empty;
}

/// <summary>
/// Domain event: core.sanguo.game.turn.started
/// Description: Emitted when a turn starts; includes the active player and time context.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0018, ADR-0005, ADR-0015, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
/// Ordering: This event defines the active player context and MUST be emitted before any
/// <see cref="SanguoPlayerStateChanged"/> that is meant to update the active player's HUD within the same CorrelationId.
/// See <see cref="SanguoEventOrderingRules"/>.
/// </remarks>
public sealed record SanguoGameTurnStarted(
    string GameId,
    int TurnNumber,
    string ActivePlayerId,
    int Year,
    int Month,
    int Day,
    System.DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.game.turn.started";

    public int RoundNumber => TurnNumber;
}

/// <summary>
/// Domain event: core.sanguo.game.turn.ended
/// Description: Emitted when the current turn ends; used for settlement coordination and audit logging.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0018, ADR-0005, ADR-0015, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
/// Ordering: This event closes the current turn number within a turn scope.
/// See <see cref="SanguoEventOrderingRules"/>.
/// </remarks>
public sealed record SanguoGameTurnEnded(
    string GameId,
    int TurnNumber,
    string ActivePlayerId,
    System.DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.game.turn.ended";
}

/// <summary>
/// Domain event: core.sanguo.game.turn.advanced
/// Description: Emitted when the game advances to the next turn (including date changes).
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0018, ADR-0005, ADR-0015, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
/// </remarks>
public sealed record SanguoGameTurnAdvanced(
    string GameId,
    int TurnNumber,
    string ActivePlayerId,
    int Year,
    int Month,
    int Day,
    System.DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.game.turn.advanced";
}

/// <summary>
/// Domain event: core.sanguo.game.saved
/// Description: Emitted when a game save completes successfully.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0006, ADR-0018, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
/// </remarks>
public sealed record SanguoGameSaved(
    string GameId,
    string SaveSlotId,
    string ContentPackId,
    int ContentPackVersion,
    System.DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.game.saved";
}

/// <summary>
/// Domain event: core.sanguo.game.loaded
/// Description: Emitted when a game load completes successfully.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0006, ADR-0018, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
/// </remarks>
public sealed record SanguoGameLoaded(
    string GameId,
    string SaveSlotId,
    string ContentPackId,
    int ContentPackVersion,
    System.DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId,
    bool SaveUntrusted = false
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.game.loaded";
}

/// <summary>
/// Domain event: core.sanguo.game.ended
/// Description: Emitted when the game enters an ended state (e.g., bankrupt, max turns reached, or target assets achieved).
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0018, ADR-0005, ADR-0015, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
/// </remarks>
public sealed record SanguoGameEnded(
    string GameId,
    string EndReason,
    System.DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId,
    string? WinnerPlayerId = null,
    SanguoGameEndStatsSnapshot? StatsSnapshot = null
)
{
    public const string ReasonNoPlayers = "no_players";

    public const string ReasonPlayerBankrupt = "player_bankrupt";

    public const string ReasonLastActorStanding = "last_actor_standing";

    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.game.ended";
}

/// <summary>
/// Domain event: core.sanguo.player.eliminated
/// Description: Emitted when a player transitions into an eliminated state (audit-oriented).
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0024 (CorrelationId/CausationId).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
/// </remarks>
public sealed record SanguoPlayerEliminated(
    string GameId,
    int TurnNumber,
    string PlayerId,
    string ReasonCode,
    decimal MoneyBefore,
    decimal MoneyAfter,
    System.DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    public const string ReasonBankrupt = "bankrupt";

    public const string EventType = "core.sanguo.player.eliminated";
}
