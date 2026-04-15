using System.Collections.Generic;

namespace Game.Core.Services.Sanguo;

public enum EventTileType
{
    Normal = 0,
    Event = 1,
}

public sealed class EventTileAutoTriggerEnforcementModule
{
    public const string SkipBlockedReasonMandatoryEventResolutionActive = "mandatory-event-resolution-active";
    public const string SkipBlockedReasonRuleBlocked = "rule-blocked";

    private readonly List<string> auditTrail = new();
    private string? ruleBlockedSkipReason = SkipBlockedReasonRuleBlocked;

    public bool IsAwaitingMandatoryEventResolution { get; private set; }

    public bool IsTurnClosed { get; private set; }

    public bool IsSkipEnabled { get; private set; } = true;

    public bool IsEndTurnEnabled { get; private set; } = true;

    public bool IsShopEnabled { get; private set; } = true;

    public IReadOnlyList<string> AuditTrail => auditTrail;
    public string? LastSkipBlockedReason { get; private set; }

    public void OnPlayerLanded(EventTileType tileType)
    {
        auditTrail.Add("PlayerLanded");

        if (tileType == EventTileType.Event)
        {
            IsAwaitingMandatoryEventResolution = true;
            IsTurnClosed = false;
            IsSkipEnabled = false;
            ruleBlockedSkipReason = SkipBlockedReasonMandatoryEventResolutionActive;
            IsEndTurnEnabled = false;
            IsShopEnabled = false;
            auditTrail.Add("MandatoryEventResolutionEntered");
            return;
        }

        IsAwaitingMandatoryEventResolution = false;
        IsTurnClosed = true;
        IsSkipEnabled = true;
        ruleBlockedSkipReason = null;
        IsEndTurnEnabled = true;
        IsShopEnabled = true;
        auditTrail.Add("TurnEnded");
    }

    public void SetSkipEligibility(bool isEligible, string? blockedReason = null)
    {
        IsSkipEnabled = isEligible;
        ruleBlockedSkipReason = isEligible
            ? null
            : string.IsNullOrWhiteSpace(blockedReason) ? SkipBlockedReasonRuleBlocked : blockedReason.Trim();
    }

    public SkipAttemptDecision EvaluateSkip()
    {
        if (IsAwaitingMandatoryEventResolution)
        {
            LastSkipBlockedReason = SkipBlockedReasonMandatoryEventResolutionActive;
            return new SkipAttemptDecision(false, LastSkipBlockedReason);
        }

        if (!IsSkipEnabled)
        {
            LastSkipBlockedReason = ruleBlockedSkipReason ?? SkipBlockedReasonRuleBlocked;
            return new SkipAttemptDecision(false, LastSkipBlockedReason);
        }

        LastSkipBlockedReason = null;
        return new SkipAttemptDecision(true, null);
    }

    public bool TrySkip() => EvaluateSkip().IsAllowed;

    public bool TryEndTurn() => !IsAwaitingMandatoryEventResolution && IsEndTurnEnabled;

    public bool TryOpenShop() => !IsAwaitingMandatoryEventResolution && IsShopEnabled;
}

public readonly record struct SkipAttemptDecision(bool IsAllowed, string? BlockedReason);
