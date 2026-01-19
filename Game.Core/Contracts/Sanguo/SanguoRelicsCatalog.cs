using System;
using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: SanguoRelicsCatalog
/// Description: Relics (persistent modifiers) definitions loaded from JSON at runtime.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates), ADR-0019 (security baseline).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t62-relics.md.
/// Data source (SSoT): res://Data/relics.json.
/// </remarks>
public sealed record SanguoRelicsCatalog(
    int SchemaVersion,
    int Version,
    IReadOnlyList<SanguoRelicDefinition> Relics
);

/// <summary>
/// DTO: SanguoRelicDefinition
/// Description: Single relic definition. RelicId must be globally unique.
/// </summary>
/// <remarks>
/// EffectKind is restricted by an allow-list in quality gates. This contract stays pure C# (no Godot types).
/// </remarks>
public sealed record SanguoRelicDefinition(
    string RelicId,
    string NameKey,
    string DescriptionKey,
    string EffectKind,
    int? MoneyDelta,
    int? EconomyStepDelta
);

