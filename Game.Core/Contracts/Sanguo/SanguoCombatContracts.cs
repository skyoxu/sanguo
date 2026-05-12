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
    int EffectiveCombatRating,
    string? EncounterId = null,
    string? EncounterKind = null,
    SanguoCombatRuntimeSnapshot? PlayerSnapshot = null,
    SanguoCombatRuntimeSnapshot? EnemySnapshot = null,
    IReadOnlyList<SanguoCombatRewardItem>? Rewards = null,
    IReadOnlyList<SanguoCombatLogEntry>? RecentLogEntries = null
);

/// <summary>
/// DTO: SanguoCombatRuntimeSnapshot
/// Description: Runtime battle snapshot for one side at combat start or end.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-V4/08/08-Contracts-Combat-Baseline.md.
/// </remarks>
public sealed record SanguoCombatRuntimeSnapshot(
    SanguoCombatUnitSnapshot MainUnit,
    IReadOnlyList<SanguoCombatUnitSnapshot>? Summons = null
);

/// <summary>
/// DTO: SanguoCombatUnitSnapshot
/// Description: Runtime unit snapshot used by battle UI and deterministic assertions.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-V4/08/08-Contracts-Combat-Baseline.md.
/// </remarks>
public sealed record SanguoCombatUnitSnapshot(
    string UnitId,
    string DisplayName,
    string UnitRole,
    SanguoCombatStatsDefinition Stats,
    IReadOnlyList<string>? SkillIds = null,
    IReadOnlyList<string>? PassiveSkillIds = null,
    IReadOnlyList<string>? RelicIds = null,
    IReadOnlyList<string>? BuffIds = null,
    IReadOnlyList<string>? DebuffIds = null
);

/// <summary>
/// DTO: SanguoCombatRewardItem
/// Description: Reward popup payload entry for combat win settlement.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-V4/08/08-Contracts-Combat-Baseline.md.
/// </remarks>
public sealed record SanguoCombatRewardItem(
    string RewardId,
    string RewardType,
    decimal Amount,
    string? IconPath = null,
    string? Description = null
);

/// <summary>
/// DTO: SanguoCombatLogEntry
/// Description: Structured battle log entry for latest-window UI rendering.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-V4/08/08-Contracts-Combat-Baseline.md.
/// </remarks>
public sealed record SanguoCombatLogEntry(
    int Sequence,
    decimal TimestampSeconds,
    string Message,
    string? EntryType = null
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
    string? CausationId,
    SanguoCombatRuntimeSnapshot? PlayerSnapshot = null,
    SanguoCombatRuntimeSnapshot? EnemySnapshot = null
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
    string? CausationId,
    SanguoCombatRuntimeSnapshot? PlayerSnapshot = null,
    SanguoCombatRuntimeSnapshot? EnemySnapshot = null
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.combat.ended";
}
