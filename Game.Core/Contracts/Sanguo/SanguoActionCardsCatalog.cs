using System;
using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: SanguoActionCardsCatalog
/// Description: Action cards catalog loaded from JSON at runtime.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates), ADR-0019 (security baseline).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t57-action-cards.md.
/// Data source (SSoT): res://Data/action_cards.json.
/// </remarks>
public sealed record SanguoActionCardsCatalog(
    int SchemaVersion,
    int Version,
    IReadOnlyList<SanguoActionCardCatalogEntry> Cards
);

/// <summary>
/// DTO: SanguoActionCardCatalogEntry
/// Description: Single action card definition. Cards use the steps-based multiplier system (0.5 step).
/// </summary>
/// <remarks>
/// EffectKind is restricted by an allow-list in quality gates. DurationRounds is the default duration for the effect.
/// </remarks>
public sealed record SanguoActionCardCatalogEntry(
    string CardId,
    string NameKey,
    string DescriptionKey,
    string EffectKind,
    int StepDelta,
    int DurationRounds
);

