using System;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Domain event: core.sanguo.action_card.played
/// Description: Emitted when an action card is played in TurnPhase.BeforeRoll.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoActionCardPlayed(
    string GameId,
    string PlayerId,
    string CardId,
    string EffectKind,
    int StepDelta,
    int DurationRounds,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.action_card.played";
}

/// <summary>
/// Domain event: core.sanguo.random_event.applied
/// Description: Emitted when a random event is applied (tile event or global event).
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoRandomEventApplied(
    string GameId,
    string PlayerId,
    string EventId,
    string EffectKind,
    int? MoneyDelta,
    int? StepDelta,
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
    public const string EventType = "core.sanguo.random_event.applied";
}

/// <summary>
/// Domain event: core.sanguo.building.built
/// Description: Emitted when a building is built or upgraded on an owned city.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoBuildingBuilt(
    string GameId,
    string PlayerId,
    string CityId,
    string BuildingId,
    int NewLevel,
    SanguoEconomyStepDeltas EconomyStepDeltas,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.building.built";
}
