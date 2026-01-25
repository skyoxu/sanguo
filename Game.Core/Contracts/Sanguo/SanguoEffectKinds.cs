namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Allowed effectKind values used by stop-loss content configs (Data/*.json) and related domain events.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t51-economy-multipliers-and-applied-multipliers.md.
/// </remarks>
public static class SanguoEffectKinds
{
    public const string MoneyDelta = "moneyDelta";
    public const string EconomyStepDelta = "economyStepDelta";
    public const string FixedDice = "fixedDice";
    public const string SkipNextTurn = "skipNextTurn";
    public const string Teleport = "teleport";
    public const string PendingSteal = "pendingSteal";
    public const string StartCombat = "startCombat";
}
