using System;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Domain event: core.sanguo.loot.granted
/// Description: Emitted when loot is granted to a player (money/card/relic), regardless of the source (combat/event/facility).
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t62-relics.md.
/// </remarks>
public sealed record SanguoLootGranted(
    string GameId,
    string PlayerId,
    string LootKind,
    int? MoneyDelta,
    string? CardId,
    string? RelicId,
    string SourceKind,
    string SourceId,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId,
    string? RngContextId = null,
    string? CandidatesSortedIdsHash = null,
    int? PickedIndex = null,
    string? PickedId = null
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.loot.granted";
}

/// <summary>
/// Domain event: core.sanguo.relic.applied
/// Description: Emitted when a relic becomes active and its effect is applied to the player's state.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t62-relics.md.
/// </remarks>
public sealed record SanguoRelicApplied(
    string GameId,
    string PlayerId,
    string RelicId,
    string EffectKind,
    int? MoneyDelta,
    int? StepDelta,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.relic.applied";
}

