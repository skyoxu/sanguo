namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Domain event: core.sanguo.game.turn.started
/// Description: Emitted when a turn starts; includes the active player and time context.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0018, ADR-0005, ADR-0015, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
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
}

/// <summary>
/// Domain event: core.sanguo.game.turn.ended
/// Description: Emitted when the current turn ends; used for settlement coordination and audit logging.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0018, ADR-0005, ADR-0015, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
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
    System.DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
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
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.game.ended";
}
