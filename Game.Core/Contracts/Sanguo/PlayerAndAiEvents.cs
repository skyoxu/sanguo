namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Domain event: core.sanguo.player.state.changed
/// Description: Emitted when a player's money, position, or assets change.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0018, ADR-0005, ADR-0006, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
/// </remarks>
public sealed record SanguoPlayerStateChanged(
    string GameId,
    string PlayerId,
    decimal Money,
    int PositionIndex,
    System.DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.player.state.changed";
}

/// <summary>
/// Domain event: core.sanguo.ai.decision.made
/// Description: Emitted when the AI makes a decision for the current situation (e.g., buy, skip, or other action).
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0018, ADR-0005, ADR-0015, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
/// </remarks>
public sealed record SanguoAiDecisionMade(
    string GameId,
    string AiPlayerId,
    string DecisionType,
    string? TargetCityId,
    System.DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.ai.decision.made";
}
