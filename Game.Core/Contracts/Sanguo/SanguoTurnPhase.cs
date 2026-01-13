namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Enum: SanguoTurnPhase
/// Description: High-level turn phase contract used for deterministic action windows.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// </remarks>
public enum SanguoTurnPhase
{
    /// <summary>
    /// The player may optionally play at most one action card before rolling dice.
    /// </summary>
    BeforeRoll = 0,

    /// <summary>
    /// Dice roll and movement resolution.
    /// </summary>
    RollAndMove = 1,

    /// <summary>
    /// After-move tile actions (buy/build/skip) are resolved.
    /// </summary>
    AfterMove = 2,

    /// <summary>
    /// End-of-turn bookkeeping.
    /// </summary>
    End = 3,
}

