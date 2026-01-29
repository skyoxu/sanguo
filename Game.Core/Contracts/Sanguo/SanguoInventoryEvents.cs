using System;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Domain event: core.sanguo.card.lost
/// Description: Emitted when a player loses a held card instance (consume/discard/steal/expire/replace).
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t57-action-cards.md.
/// </remarks>
public sealed record SanguoCardLost(
    string GameId,
    string PlayerId,
    string CardId,
    string ReasonCode,
    string SourceKind,
    string SourceId,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    public const string ReasonConsumed = "consumed";
    public const string ReasonDiscarded = "discarded";
    public const string ReasonStolen = "stolen";
    public const string ReasonExpired = "expired";
    public const string ReasonReplaced = "replaced";

    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.card.lost";
}
