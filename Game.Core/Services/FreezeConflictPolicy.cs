namespace Game.Core.Services;

public static class FreezeConflictPolicy
{
    public static FreezeConflictEvaluation Evaluate(
        string freezeRevision,
        string frozenRuleId,
        string candidateChangeId,
        bool conflictsWithFrozenRule,
        string? laterFreezeRevision,
        string evidencePath)
    {
        if (!conflictsWithFrozenRule)
        {
            return FreezeConflictEvaluation.Accepted("no_freeze_conflict");
        }

        if (!string.IsNullOrWhiteSpace(laterFreezeRevision))
        {
            return FreezeConflictEvaluation.Accepted("superseded_by_later_freeze_revision");
        }

        return FreezeConflictEvaluation.BlockedAsBug("freeze_conflict_blocked");
    }
}

public sealed record FreezeConflictEvaluation(
    bool IsAccepted,
    bool IsBlocked,
    bool IsDefect,
    bool RequiresTripletBaselineValidation,
    string ReasonCode,
    string Status,
    string EvidenceLane)
{
    public static FreezeConflictEvaluation Accepted(string reasonCode) => new(
        IsAccepted: true,
        IsBlocked: false,
        IsDefect: false,
        RequiresTripletBaselineValidation: true,
        ReasonCode: reasonCode,
        Status: "Accepted",
        EvidenceLane: "xunit-core");

    public static FreezeConflictEvaluation BlockedAsBug(string reasonCode) => new(
        IsAccepted: false,
        IsBlocked: true,
        IsDefect: true,
        RequiresTripletBaselineValidation: true,
        ReasonCode: reasonCode,
        Status: "BlockedAsBug",
        EvidenceLane: "xunit-core");
}
