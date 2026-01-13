using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: SanguoGameEndPlayerStats
/// Description: Minimal per-player stats snapshot for game-end UI.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoGameEndPlayerStats(
    string PlayerId,
    decimal Money
);

/// <summary>
/// DTO: SanguoGameEndStatsSnapshot
/// Description: Minimal snapshot for deterministic end-of-game display.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public sealed record SanguoGameEndStatsSnapshot(
    int TurnNumber,
    long TreasuryMinorUnits,
    IReadOnlyList<SanguoGameEndPlayerStats> Players
);

