using System;
using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: SanguoRandomEventsCatalog
/// Description: Random events catalog used by event tiles and global event triggers.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates), ADR-0019 (security baseline).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t56-random-events.md.
/// Data source (SSoT): res://Data/random_events.json.
/// </remarks>
public sealed record SanguoRandomEventsCatalog(
    int SchemaVersion,
    int Version,
    IReadOnlyList<SanguoRandomEventCatalogEntry> Events,
    IReadOnlyList<SanguoRandomEventPoolCatalogEntry> EventPools
);

/// <summary>
/// DTO: SanguoRandomEventCatalogEntry
/// Description: Single random event definition.
/// </summary>
/// <remarks>
/// EffectKind is restricted by an allow-list in quality gates.
/// </remarks>
public sealed record SanguoRandomEventCatalogEntry(
    string EventId,
    string NameKey,
    string DescriptionKey,
    string EffectKind,
    int? MoneyDelta,
    int? StepDelta,
    int CooldownRounds,
    bool UniqueOnce,
    string? EncounterId = null,
    int? EncounterTarget = null
);

/// <summary>
/// DTO: SanguoRandomEventPoolCatalogEntry
/// Description: Named pool of EventIds.
/// </summary>
public sealed record SanguoRandomEventPoolCatalogEntry(
    string PoolId,
    IReadOnlyList<string> EventIds
);

