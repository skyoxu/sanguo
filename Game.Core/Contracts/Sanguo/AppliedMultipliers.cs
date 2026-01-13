namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: AppliedMultipliers
/// Description: Snapshot of all multiplier factors used by an economic computation.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md.
/// UI must only display this snapshot and MUST NOT compute money on its own.
/// </remarks>
public sealed record AppliedMultipliers(
    decimal Character,
    decimal Building,
    decimal Event,
    decimal ActionCard,
    decimal Effective
);

