using System;

namespace Game.Core.Services.Sanguo;

public enum CoreStateFailureCampaignBootstrapAction
{
    Retry,
    EnterRun,
}

public enum CoreStateFailureCampaignBootstrapPhase
{
    Failed,
    Running,
}

public sealed record CoreStateFailureCampaignBootstrapInput(
    string CampaignId,
    CoreStateFailureCampaignBootstrapAction RequestedAction,
    string Seed,
    bool DiceFlowReady);

public sealed record CoreStateFailureCampaignBootstrapState(
    string CampaignId,
    CoreStateFailureCampaignBootstrapPhase Phase,
    string FailureCode,
    int Attempt,
    bool DiceFlowReady)
{
    public static CoreStateFailureCampaignBootstrapState Failed(
        string campaignId,
        string failureCode,
        int previousAttempt)
    {
        return new CoreStateFailureCampaignBootstrapState(
            CampaignId: campaignId,
            Phase: CoreStateFailureCampaignBootstrapPhase.Failed,
            FailureCode: failureCode,
            Attempt: previousAttempt,
            DiceFlowReady: false);
    }
}

public sealed record CoreStateFailureCampaignBootstrapResult(
    bool Accepted,
    string ReasonCode,
    string StartupOutcome,
    string EvidenceRefs,
    CoreStateFailureCampaignBootstrapState State);

public static class CoreStateFailureCampaignBootstrapper
{
    public const string InvalidInputReason = "invalid_core_state_failure_bootstrap_input";

    public static CoreStateFailureCampaignBootstrapResult Bootstrap(
        CoreStateFailureCampaignBootstrapState state,
        CoreStateFailureCampaignBootstrapInput input)
    {
        ArgumentNullException.ThrowIfNull(state);
        ArgumentNullException.ThrowIfNull(input);

        if (!IsValid(state, input))
        {
            return new CoreStateFailureCampaignBootstrapResult(
                Accepted: false,
                ReasonCode: InvalidInputReason,
                StartupOutcome: "startup_failure_refused",
                EvidenceRefs: "ACC:T215",
                State: state);
        }

        var nextState = state with
        {
            CampaignId = input.CampaignId.Trim(),
            Phase = CoreStateFailureCampaignBootstrapPhase.Running,
            FailureCode = string.Empty,
            Attempt = state.Attempt + 1,
            DiceFlowReady = input.DiceFlowReady,
        };

        return new CoreStateFailureCampaignBootstrapResult(
            Accepted: true,
            ReasonCode: string.Empty,
            StartupOutcome: "canonical_startup_path",
            EvidenceRefs: "ACC:T215",
            State: nextState);
    }

    private static bool IsValid(
        CoreStateFailureCampaignBootstrapState state,
        CoreStateFailureCampaignBootstrapInput input)
    {
        return !string.IsNullOrWhiteSpace(state.CampaignId)
            && !string.IsNullOrWhiteSpace(input.CampaignId)
            && string.Equals(state.CampaignId.Trim(), input.CampaignId.Trim(), StringComparison.Ordinal)
            && !string.IsNullOrWhiteSpace(input.Seed)
            && input.DiceFlowReady
            && (input.RequestedAction == CoreStateFailureCampaignBootstrapAction.Retry
                || input.RequestedAction == CoreStateFailureCampaignBootstrapAction.EnterRun);
    }
}
