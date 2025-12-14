namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Domain event: core.sanguo.board.token.moved
/// Description: Emitted when a player or AI token moves to a new board position.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0018 (Godot C# tech stack), ADR-0005 (quality gates), ADR-0015 (performance budgets), ADR-0024 (Sanguo template lineage).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
/// </remarks>
public sealed record SanguoTokenMoved(
    string GameId,
    string PlayerId,
    int FromIndex,
    int ToIndex,
    int Steps,
    bool PassedStart,
    System.DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.board.token.moved";
}

/// <summary>
/// Domain event: core.sanguo.dice.rolled
/// Description: Emitted when a player or AI rolls the dice and a result is produced.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0018, ADR-0005, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
/// </remarks>
public sealed record SanguoDiceRolled(
    string GameId,
    string PlayerId,
    int Value,
    System.DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.dice.rolled";
}
