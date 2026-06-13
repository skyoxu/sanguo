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
    string? CausationId,
    AppliedMultipliers? AppliedMultipliersAfter = null
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.action_card.played";
}

/// <summary>
/// Domain event: core.sanguo.action_card.play.rejected
/// Description: Emitted when an action card play is rejected by core rules (auditable, no state change).
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t52-turn-window-and-event-ordering.md.
/// </remarks>
public sealed record SanguoActionCardPlayRejected(
    string GameId,
    int TurnNumber,
    int RoundNumber,
    string PlayerId,
    string Phase,
    string CardId,
    string ReasonCode,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    public const string ReasonAlreadyPlayedThisTurn = "already_played_this_turn";
    public const string ReasonNotBeforeRoll = "not_before_roll";
    public const string ReasonCatalogMissing = "catalog_missing";
    public const string ReasonUnknownCardId = "unknown_card_id";
    public const string ReasonInvalidCardEffectKind = "invalid_card_effect_kind";
    public const string ReasonInvalidTarget = "invalid_target";
    public const string ReasonNotOwned = "not_owned";

    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.action_card.play.rejected";
}

/// <summary>
/// Domain event payload contract for core.sanguo.action.explain.
/// Description: Structured explainability payload used by deterministic action-flow decisions.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005, ADR-0020.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-V3/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoActionExplainEventData(
    string ExplainCode,
    string SourceTag,
    string? ReasonCode = null,
    string? GameId = null,
    int? TurnNumber = null,
    int? RoundNumber = null,
    string? PlayerId = null,
    string? Phase = null,
    string? CardId = null,
    DateTimeOffset? OccurredAt = null,
    string? CorrelationId = null,
    string? CausationId = null
) : IEventData;

/// <summary>
/// Domain event: core.sanguo.random_event.applied
/// Description: Emitted when a random event is applied (tile event or global event).
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t56-random-events.md.
/// </remarks>
public sealed record SanguoRandomEventApplied(
    string GameId,
    string PlayerId,
    string EventId,
    string EffectKind,
    int MapCycleNumber,
    int? MoneyDelta,
    int? StepDelta,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId,
    string? RngContextId = null,
    string? CandidatesSortedIdsHash = null,
    int? PickedIndex = null,
    string? PickedId = null,
    AppliedMultipliers? AppliedMultipliersAfter = null,
    string? EncounterId = null,
    int? EncounterTarget = null,
    string? TriggerSource = null
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.random_event.applied";
}

/// <summary>
/// Domain event: core.sanguo.random_event.rejected
/// Description: Emitted when a random event is selected but rejected by allow-list or validation rules.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t56-random-events.md.
/// </remarks>
public sealed record SanguoRandomEventRejected(
    string GameId,
    string PlayerId,
    string EventId,
    string EffectKind,
    string RejectReason,
    int? MoneyDelta,
    int? StepDelta,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId,
    string? RngContextId = null,
    string? CandidatesSortedIdsHash = null,
    int? PickedIndex = null,
    string? PickedId = null,
    string? EncounterId = null,
    int? EncounterTarget = null,
    string? TriggerSource = null
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.random_event.rejected";
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

/// <summary>
/// Domain event: core.sanguo.building.build.rejected
/// Description: Emitted when a building build or upgrade action is rejected by core rules.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoBuildingBuildRejected(
    string GameId,
    string PlayerId,
    string CityId,
    string BuildingId,
    int AttemptedLevel,
    string ReasonCode,
    decimal RequiredMoney,
    decimal AvailableMoney,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    public const string ReasonInsufficientResources = "insufficient_resources";

    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.building.build.rejected";
}
