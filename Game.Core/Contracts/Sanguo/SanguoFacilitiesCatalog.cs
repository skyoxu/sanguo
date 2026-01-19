using System;
using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: SanguoFacilitiesCatalog
/// Description: Facilities catalog for "pass/facility" tiles. Loaded from JSON at runtime.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0019 (security baseline), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t53-map-config.md.
/// Data source (SSoT): res://Data/facilities.json.
/// </remarks>
public sealed record SanguoFacilitiesCatalog(
    int SchemaVersion,
    int Version,
    IReadOnlyList<SanguoFacilityDefinition> Facilities
);

/// <summary>
/// DTO: SanguoFacilityDefinition
/// Description: Defines a facility tile behavior and its available actions.
/// </summary>
/// <remarks>
/// FacilityKind is a stable identifier used by Core logic. UI should only use keys/paths for rendering.
/// </remarks>
public sealed record SanguoFacilityDefinition(
    string FacilityId,
    string FacilityKind,
    string NameKey,
    string DescriptionKey,
    IReadOnlyList<SanguoFacilityActionDefinition> Actions
);

/// <summary>
/// DTO: SanguoFacilityActionDefinition
/// Description: Action exposed by a facility tile (e.g., "buy", "trigger_event").
/// </summary>
/// <remarks>
/// Params are string-based to keep the contract pure and JSON-friendly; Core should validate keys and values.
/// IconResPath MUST be under res://Assets/ (security baseline); enforcement lives in validators/adapters.
/// </remarks>
public sealed record SanguoFacilityActionDefinition(
    string ActionId,
    string NameKey,
    string IconResPath,
    IReadOnlyDictionary<string, string>? Params
);

