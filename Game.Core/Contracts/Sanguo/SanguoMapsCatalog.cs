using System;
using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: SanguoMapsCatalog
/// Description: Maps index/catalog for new-game map selection. This is loaded from JSON at runtime.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates), ADR-0019 (security baseline).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t53-map-config.md.
/// Data source (SSoT): res://Data/maps/_index.json (do not scan directories).
/// </remarks>
public sealed record SanguoMapsCatalog(
    int SchemaVersion,
    int Version,
    IReadOnlyList<SanguoMapCatalogEntry> Maps
);

/// <summary>
/// DTO: SanguoMapCatalogEntry
/// Description: Single map entry shown in the new-game menu.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0019 (security baseline).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t54-new-game-menu.md.
/// </remarks>
public sealed record SanguoMapCatalogEntry(
    string MapId,
    string NameKey,
    string DescriptionKey,
    string Path,
    int RecommendedPlayersMin,
    int RecommendedPlayersMax,
    int ContentVersion,
    string PreviewResPath
);

