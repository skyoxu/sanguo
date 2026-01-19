using System;
using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: SanguoCharactersCatalog
/// Description: Characters definitions loaded from JSON at runtime.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates), ADR-0019 (security baseline).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t55-characters.md.
/// Data source (SSoT): res://Data/characters.json.
/// </remarks>
public sealed record SanguoCharactersCatalog(
    int SchemaVersion,
    int Version,
    IReadOnlyList<SanguoCharacterDefinition> Characters
);

