using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

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
    [property: JsonPropertyName("map_id")] string MapId,
    [property: JsonPropertyName("players_count")] int PlayersCount,
    [property: JsonPropertyName("starting_money_preset")] int StartingMoneyPreset,
    [property: JsonPropertyName("global_event_interval_turns")] int GlobalEventIntervalTurns,
    [property: JsonPropertyName("random_seed")] int RandomSeed,
    [property: JsonPropertyName("character_assignments")] IReadOnlyDictionary<string, string> CharacterAssignments,
    [property: JsonPropertyName("active_strategem_id")] string ActiveStrategemId = "strat_active_default",
    [property: JsonPropertyName("passive_strategem_id")] string PassiveStrategemId = "strat_passive_default"
);
