using System;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Resolves the settlement route when camp durability reaches a fatal condition.
/// The fatal path must deterministically route to defeat settlement without retry loops.
/// </summary>
public sealed class CampFailSettlementRouter
{
    public const string InProgressScreen = "in_progress";
    public const string DefeatSettlementScreen = "defeat_settlement";
    public const string EndReasonCampDurabilityFatal = "camp_durability_fatal";
    public const string EvidenceScopeR3 = "R3";

    public SettlementRouteResult Route(SettlementRouteState state, int campDurability, int currentTick)
    {
        if (campDurability > 0)
        {
            return new SettlementRouteResult(
                NextScreen: state.CurrentScreen,
                EndReason: null,
                EvidenceScope: EvidenceScopeR3,
                DeadlockDetected: false,
                NextState: state);
        }

        var nextState = state with
        {
            CurrentScreen = DefeatSettlementScreen,
            LastProcessedTick = currentTick,
        };

        return new SettlementRouteResult(
            NextScreen: DefeatSettlementScreen,
            EndReason: EndReasonCampDurabilityFatal,
            EvidenceScope: EvidenceScopeR3,
            DeadlockDetected: false,
            NextState: nextState);
    }
}

public sealed record SettlementRouteState(string CurrentScreen, int LoopCount, int LastProcessedTick)
{
    public static SettlementRouteState InProgress()
    {
        return new SettlementRouteState(
            CurrentScreen: CampFailSettlementRouter.InProgressScreen,
            LoopCount: 0,
            LastProcessedTick: -1);
    }
}

public sealed record SettlementRouteResult(
    string NextScreen,
    string? EndReason,
    string EvidenceScope,
    bool DeadlockDetected,
    SettlementRouteState NextState);
