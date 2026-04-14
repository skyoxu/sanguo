using System;
using System.Collections.Generic;

using Game.Core.Contracts.Sanguo;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Deterministic replay helper for Task 90 forced challenge preemption split.
/// </summary>
public static class ForcedChallengePreemption
{
    public static ForcedChallengePreemptionReplayResult ReplayEventTypes(IEnumerable<string> eventTypes)
    {
        ArgumentNullException.ThrowIfNull(eventTypes);

        var auditTrail = new List<string>();
        var preemptionApplied = false;
        var preemptedFlowLocked = false;
        var forcedChallengeStarted = false;
        var activeFlow = "none";
        var preemptedFlowAdvancedInParallel = false;
        var preemptedFlowResolvedInParallel = false;

        foreach (var eventType in eventTypes)
        {
            if (string.Equals(eventType, SanguoBossChallengePrompted.EventType, StringComparison.Ordinal))
            {
                if (!preemptionApplied && string.Equals(activeFlow, "challenge", StringComparison.Ordinal))
                {
                    preemptionApplied = true;
                    preemptedFlowLocked = true;
                    activeFlow = "forced_challenge";
                    auditTrail.Add("forced_challenge_preempted");
                }

                continue;
            }

            if (string.Equals(eventType, SanguoCombatStarted.EventType, StringComparison.Ordinal))
            {
                if (string.Equals(activeFlow, "none", StringComparison.Ordinal))
                {
                    activeFlow = "challenge";
                    auditTrail.Add("challenge_started");
                    continue;
                }

                if (string.Equals(activeFlow, "forced_challenge", StringComparison.Ordinal))
                {
                    if (!forcedChallengeStarted)
                    {
                        forcedChallengeStarted = true;
                        auditTrail.Add("forced_challenge_started");
                    }

                    continue;
                }

                if (preemptedFlowLocked && string.Equals(activeFlow, "challenge", StringComparison.Ordinal))
                {
                    preemptedFlowAdvancedInParallel = true;
                    continue;
                }

                continue;
            }

            if (string.Equals(eventType, SanguoCombatEnded.EventType, StringComparison.Ordinal))
            {
                if (preemptedFlowLocked && string.Equals(activeFlow, "challenge", StringComparison.Ordinal))
                {
                    preemptedFlowResolvedInParallel = true;
                }

                continue;
            }
        }

        return new ForcedChallengePreemptionReplayResult(
            PreemptionApplied: preemptionApplied,
            ActiveFlow: activeFlow,
            AuditTrail: auditTrail,
            IsPreemptedFlowLocked: preemptedFlowLocked,
            PreemptedFlowAdvancedInParallel: preemptedFlowAdvancedInParallel,
            PreemptedFlowResolvedInParallel: preemptedFlowResolvedInParallel);
    }
}

public sealed record ForcedChallengePreemptionReplayResult(
    bool PreemptionApplied,
    string ActiveFlow,
    IReadOnlyList<string> AuditTrail,
    bool IsPreemptedFlowLocked,
    bool PreemptedFlowAdvancedInParallel,
    bool PreemptedFlowResolvedInParallel);
