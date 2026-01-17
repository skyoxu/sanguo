using System;
using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: SanguoCombatResult
/// Description: Minimal deterministic PVE combat result contract.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoCombatResult(
    string Outcome, // win | lose | draw
    decimal MoneyDelta,
    int EncounterTarget,
    int EffectiveCombatRating
);

/// <summary>
/// Domain event: core.sanguo.combat.started
/// Description: Emitted when a PVE combat encounter starts.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoCombatStarted(
    string GameId,
    string PlayerId,
    string EncounterId,
    int RandomSeed,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.combat.started";
}

/// <summary>
/// Domain event: core.sanguo.combat.ended
/// Description: Emitted when a PVE combat encounter ends and the result is applied back to the main loop.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoCombatEnded(
    string GameId,
    string PlayerId,
    string EncounterId,
    SanguoCombatResult Result,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.combat.ended";
}
