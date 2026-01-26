using System;
using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: SanguoRegionsCatalog
/// Description: Regions (state/zone) definitions shared across maps. Loaded from JSON at runtime.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates), ADR-0019 (security baseline).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t64-regions.md.
/// Data source (SSoT): res://Data/regions.json.
/// </remarks>
public sealed record SanguoRegionsCatalog(
    int SchemaVersion,
    int Version,
    IReadOnlyList<SanguoRegionDefinition> Regions
);

/// <summary>
/// DTO: SanguoRegionDefinition
/// Description: Region metadata and region-wide bonus definition.
/// </summary>
/// <remarks>
/// EffectKind is restricted by an allow-list in quality gates.
/// </remarks>
public sealed record SanguoRegionDefinition(
    string RegionId,
    string NameKey,
    string DescriptionKey,
    string EffectKind,
    IReadOnlyDictionary<string, string> EffectParams,
    SanguoEconomyStepDeltas EconomyStepDeltas
);

