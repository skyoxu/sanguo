using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

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
    [property: JsonPropertyName("schemaVersion")] int SchemaVersion,
    [property: JsonPropertyName("version")] int Version,
    [property: JsonPropertyName("relics")] IReadOnlyList<SanguoRelicDefinition> Relics
);

/// <summary>
/// DTO: SanguoRelicDefinition
/// Description: Single relic definition. RelicId must be globally unique.
/// </summary>
/// <remarks>
/// EffectKind is restricted by an allow-list in quality gates. This contract stays pure C# (no Godot types).
/// </remarks>
public sealed record SanguoRelicDefinition(
    [property: JsonPropertyName("relicId")] string RelicId,
    [property: JsonPropertyName("nameKey")] string NameKey,
    [property: JsonPropertyName("descriptionKey")] string DescriptionKey,
    [property: JsonPropertyName("effectKind")] string EffectKind,
    [property: JsonPropertyName("moneyDelta")] int? MoneyDelta,
    [property: JsonPropertyName("stepDelta")] int? EconomyStepDelta
);

