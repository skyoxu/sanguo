using System;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Domain event: core.sanguo.objective.skipped.
/// Published when current-round objective is not published due to run ending in boss battle.
/// </summary>
/// <remarks>
/// ADR refs: ADR-0004, ADR-0020.
/// Overlay ref: docs/architecture/overlays/PRD-SANGUO-T2/08/08-Contracts-Sanguo-GameLoop-Events.md.
/// </remarks>
public sealed record SanguoObjectiveSkipped(
    string GameId,
    string ObjectiveId,
    int RoundNumber,
    string Reason,
    string? BossId,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    public const string ReasonRunEndedInBoss = "run_ended_in_boss";

    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.objective.skipped";

    public int TurnNumber => RoundNumber;

    public string ActivePlayerId => string.Empty;
}
