namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Allowed effectKind values used by stop-loss content configs (Data/*.json) and related domain events.
/// </summary>
public static class SanguoEffectKinds
{
    public const string MoneyDelta = "moneyDelta";
    public const string EconomyStepDelta = "economyStepDelta";
}

