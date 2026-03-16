using System;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Domain event: core.sanguo.boss.challenge.prompted.
/// Published when the player is prompted before boss challenge confirmation.
/// </summary>
/// <remarks>
/// ADR refs: ADR-0004, ADR-0020.
/// Overlay ref: docs/architecture/overlays/PRD-SANGUO-T2/08/08-Contracts-Sanguo-GameLoop-Events.md.
/// </remarks>
public sealed record SanguoBossChallengePrompted(
    string GameId,
    string BossId,
    int RoundNumber,
    string WinRateTier,
    int NextRoundPressureForecast,
    string KeyLossSummary,
    string FailConsequence,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    public const string WinRateTierLow = "low";
    public const string WinRateTierMid = "mid";
    public const string WinRateTierHigh = "high";

    public const string FailConsequenceReturnToCampAndEndRound = "return_to_camp_end_round";

    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.boss.challenge.prompted";
}
