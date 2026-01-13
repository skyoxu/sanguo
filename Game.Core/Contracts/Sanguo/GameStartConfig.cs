using System;
using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: GameStartConfig
/// Description: Immutable, auditable game start input for Sanguo new-game flow.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates), ADR-0011 (Windows-only), ADR-0019 (security baseline).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// This DTO is part of the "start-of-game contract surface" and MUST remain pure C# (no Godot types).
/// </remarks>
public sealed record GameStartConfig(
    string MapId,
    int PlayersCount,
    int StartingMoneyPreset,
    int GlobalEventIntervalTurns,
    int RandomSeed,
    IReadOnlyDictionary<string, string> CharacterAssignments
);

